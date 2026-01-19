import logging
import numpy as np
from typing import List, Dict, Any
from .base import BaseAgent
from db import crud, schemas
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances

logger = logging.getLogger(__name__)

class AutoGenesisAgent(BaseAgent):
    """
    The Centrifuge.
    Ingests raw user logs, clusters them into topics, and extracts 'Golden Sample' seeds.
    """
    
    def run_task(self, user_id: str):
        logger.info(f"Starting Auto-Genesis for User {user_id}")
        
        # 1. Fetch Raw Data
        logs = crud.get_all_raw_logs_for_user(self.db, user_id)
        if not logs:
            logger.warning("No raw logs found for Auto-Genesis.")
            return
        
        logger.info(f"Fetched {len(logs)} raw logs. Chunking and Vectorizing...")
        
        # 2. Chunk & Vectorize
        # For MVP, we treat each Source as a chunk. In production, we'd split long texts.
        vectors = []
        valid_logs = []
        
        for log in logs:
            text = log['raw_text'][:8000] # Truncate for embedding model limit
            try:
                embedding = self.llm.get_embedding(text)
                if embedding:
                    vectors.append(embedding)
                    valid_logs.append(log)
            except Exception as e:
                logger.error(f"Failed to embed log {log['id']}: {e}")
        
        if not vectors:
            logger.error("No valid vectors generated.")
            return

        X = np.array(vectors)
        
        # 3. Cluster (The Separation)
        # eps=0.3 is a heuristic for cosine distance (1 - similarity). 
        # range is 0-2. 0.3 means high similarity required.
        logger.info("Running DBSCAN Clustering...")
        clustering = DBSCAN(eps=0.5, min_samples=2, metric='cosine').fit(X)
        
        unique_labels = set(clustering.labels_)
        logger.info(f"Found {len(unique_labels) - (1 if -1 in unique_labels else 0)} clusters.")
        
        # 4. Distill (The Gold)
        seeds_created = 0
        
        for label in unique_labels:
            if label == -1: 
                continue # Skip Noise
            
            # Get indices for this cluster
            indices = [i for i, x in enumerate(clustering.labels_) if x == label]
            cluster_vectors = X[indices]
            cluster_logs = [valid_logs[i] for i in indices]
            
            # Calculate Centroid
            centroid = np.mean(cluster_vectors, axis=0)
            
            # Find closest log to centroid (The Archetype)
            min_dist = float('inf')
            closest_log = None
            
            for i, vec in enumerate(cluster_vectors):
                # cosine_distances returns a 2D array, we want [0][0]
                dist = cosine_distances([vec], [centroid])[0][0]
                if dist < min_dist:
                    min_dist = dist
                    closest_log = cluster_logs[i]
            
            if closest_log:
                # 5. Label (Auto-Tag)
                sample_text = closest_log['raw_text'][:1000]
                tag_prompt = f"Analyze this text and provide a short, 2-3 word topic tag (e.g., 'Quantum Physics', 'Crypto Regulation'). Text: {sample_text}"
                try:
                    cluster_name = self.llm.chat_completion(tag_prompt).strip().replace('"', '').replace('[', '').replace(']', '').replace('\n', ' ').strip()
                except:
                    cluster_name = f"Cluster_{label}"

                # --- TEMPORAL SLICING (V5) ---
                # We have the cluster. Now we find the Epochs within it.
                # Sort cluster logs by date
                from datetime import datetime
                
                def get_date(log):
                    # Try published_at first, then created_at
                    metadata = log.get('metadata') or {}
                    d_str = metadata.get('published_at') or log.get('created_at')
                    if d_str:
                        try:
                            return datetime.fromisoformat(d_str.replace('Z', '+00:00'))
                        except:
                            pass
                    return datetime.min
                
                cluster_logs_with_date = []
                for i in indices:
                    log = valid_logs[i]
                    date = get_date(log)
                    cluster_logs_with_date.append({'log': log, 'date': date, 'vector': X[i]})
                
                cluster_logs_with_date.sort(key=lambda x: x['date'])
                
                # Simple Binning: Yearly
                # Group by Year
                epochs = {}
                for item in cluster_logs_with_date:
                    year = item['date'].year
                    if year == 1: year = "Unknown" # datetime.min
                    if year not in epochs: epochs[year] = []
                    epochs[year].append(item)
                
                # For each Epoch, find the Centroid
                for year, items in epochs.items():
                    epoch_vectors = np.array([item['vector'] for item in items])
                    epoch_centroid = np.mean(epoch_vectors, axis=0)
                    
                    # Find closest log in THIS epoch
                    min_epoch_dist = float('inf')
                    closest_epoch_log = None
                    
                    for item in items:
                        dist = cosine_distances([item['vector']], [epoch_centroid])[0][0]
                        if dist < min_epoch_dist:
                            min_epoch_dist = dist
                            closest_epoch_log = item['log']
                            
                    if closest_epoch_log:
                        epoch_label = f"{cluster_name}_{year}"
                        logger.info(f"  -> Epoch '{epoch_label}' (Size {len(items)}) -> Source {closest_epoch_log['id']}")
                        
                        # 6. Insert Seed Atom (One per Epoch)
                        atom_name = f"Archetype: {epoch_label}"
                        seed_atom = schemas.Atom(
                            user_id=user_id,
                            name=atom_name,
                            type="seed_prose",
                            content=closest_epoch_log['raw_text'],
                            embedding=epoch_vectors[0].tolist(), 
                            created_at_source=get_date(closest_epoch_log), 
                            epoch_label=str(year), 
                            metadata={
                                "is_seed": True,
                                "cluster_id": int(label),
                                "cluster_name": cluster_name,
                                "source_id": closest_epoch_log['id'],
                                "epoch_year": int(year) if isinstance(year, int) else 0
                            }
                        )
                        
                        crud.create_atom(self.db, seed_atom)
                        seeds_created += 1

                # 7. Bulk Tagging (The Fix)
                # Update ALL atoms derived from these sources to belong to this cluster.
                # This ensures the Timeline shows the full count, not just the seed.
                logger.info(f"  -> Bulk tagging atoms for cluster '{cluster_name}'...")
                for log in cluster_logs:
                    source_id = log['id']
                    try:
                        # We fetch atoms linked to this source
                        # Using the metadata->>source_id convention established in IndexAtomAgent
                        # Fetch current metadata to preserve other fields? 
                        # Ideally we update via JSONb path, but Supabase/Postgres update replaces the column or merges?
                        # Standard update replaces. We must be careful.
                        # But we can use the jsonb_set syntax if we use rpc, or just fetch-modify-save.
                        # For MVP speed/safety, let's just assume we can fetch-modify-save or use a specialized query.
                        # Actually, updating metadata by fetching first is safest.
                        
                        atoms_to_update = self.db.table("Atoms").select("id, metadata").eq("metadata->>source_id", source_id).execute()
                        if atoms_to_update.data:
                            for a in atoms_to_update.data:
                                meta = a['metadata'] or {}
                                meta['cluster_id'] = int(label)
                                meta['cluster_name'] = cluster_name
                                self.db.table("Atoms").update({"metadata": meta}).eq("id", a['id']).execute()
                    except Exception as e:
                        logger.error(f"Failed to bulk tag atoms for source {source_id}: {e}")
                
        logger.info(f"Auto-Genesis Complete. Created {seeds_created} seed atoms across multiple epochs.")
        return seeds_created
