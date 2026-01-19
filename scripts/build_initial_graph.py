import logging
import sys
import uuid
from typing import List, Dict
from db.session import get_db
from db import crud, schemas

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_graph(user_id: str):
    db = get_db()
    
    logger.info(f"Building Initial Graph for User: {user_id}")
    
    # 1. Fetch all Atoms for this user
    logger.info("Fetching all atoms...")
    # Note: If database is huge, we should paginate. For now, fetching all.
    all_atoms_res = db.table("Atoms").select("*").eq("user_id", user_id).execute()
    all_atoms = all_atoms_res.data
    logger.info(f"Found {len(all_atoms)} atoms.")
    
    # 2. Phase 1: The "Train Tracks" (Intra-Source Linking)
    logger.info("Phase 1: Constructing 'Train Tracks' (Narrative Flow)...")
    
    atoms_by_source = {}
    for atom in all_atoms:
        meta = atom.get('metadata') or {}
        source_id = meta.get('source_id')
        
        if not source_id:
            continue
            
        if source_id not in atoms_by_source:
            atoms_by_source[source_id] = []
        atoms_by_source[source_id].append(atom)
        
    edges_created = 0
    for source_id, src_atoms in atoms_by_source.items():
        # Sort: Try chunk_index first, then created_at
        def sort_key(a):
            meta = a.get('metadata') or {}
            idx = meta.get('chunk_index', -1)
            # created_at might be string, supabase-py returns ISO strings
            return (int(idx), a.get('created_at'))
            
        src_atoms.sort(key=sort_key)
        
        for i in range(len(src_atoms) - 1):
            source_atom = src_atoms[i]
            target_atom = src_atoms[i+1]
            
            # Create Narrative Edge
            _create_edge(db, user_id, source_atom['id'], target_atom['id'], "narrative_flow", 1.0)
            edges_created += 1
            
    logger.info(f"Phase 1 Complete. Created {edges_created} narrative edges.")
    
    # 3. Phase 2: The "Wormholes" (Semantic Similarity)
    logger.info("Phase 2: Constructing 'Wormholes' (Semantic Similarity)...")
    logger.info("Threshold: 0.85 (High Precision)")
    
    wormholes_created = 0
    
    # We only process atoms that have embeddings
    atoms_with_vectors = [a for a in all_atoms if a.get('embedding')]
    total = len(atoms_with_vectors)
    
    for i, atom in enumerate(atoms_with_vectors):
        if i % 50 == 0:
            logger.info(f"Processing atom {i}/{total}...")
            
        embedding = atom['embedding']
        if not embedding: continue
        
        # Use RPC to find neighbors
        # We search for slightly more than 3 because we need to filter by source_id
        matches = crud.match_atoms_by_embedding(
            db, 
            embedding, 
            match_threshold=0.85, 
            match_count=10, 
            query_user_id=user_id
        )
        
        current_source_id = (atom.get('metadata') or {}).get('source_id')
        
        links_made = 0
        for match in matches:
            if links_made >= 3: break
            
            # Self check
            if match['id'] == atom['id']: continue
            
            # Cross-Source Check (Wormhole Logic)
            match_source_id = (match.get('metadata') or {}).get('source_id')
            
            # If both have sources and they are the same, skip (already covered by Train Tracks or redundancy)
            # If one doesn't have a source, we treat it as valid for linking (e.g. a concept atom)
            if current_source_id and match_source_id and current_source_id == match_source_id:
                continue
                
            # Create Semantic Edge (Bidirectional notion, but we store as directed edges A->B and B->A? 
            # Or just A->B since similarity is symmetric-ish?
            # To avoid double counting A->B and B->A later, we can enforce ID ordering or just let it be.
            # Let's just create one way for now: Current -> Match. 
            # The DomainExpert finds paths in any direction usually? No, it's BFS directed.
            # So we should probably create bidirectional edges for similarity.
            
            _create_edge(db, user_id, atom['id'], match['id'], "semantic_similarity", match['similarity'])
            _create_edge(db, user_id, match['id'], atom['id'], "semantic_similarity", match['similarity'])
            
            links_made += 1
            wormholes_created += 2
            
    logger.info(f"Phase 2 Complete. Created {wormholes_created} semantic edges.")
    logger.info("Graph Induction Finalized.")

def _create_edge(db, user_id, source_id, target_id, rel_type, weight):
    # Idempotent insert
    try:
        edge_data = {
            "user_id": user_id,
            "source_atom_id": source_id,
            "target_atom_id": target_id,
            "relationship_type": rel_type,
            "weight": weight
        }
        # Upsert
        db.table("AtomEdges").upsert(
            edge_data, 
            on_conflict="source_atom_id, target_atom_id, relationship_type"
        ).execute()
    except Exception as e:
        # Ignore dupes or errors
        pass

if __name__ == "__main__":
    # Get user_id from args or DB
    db = get_db()
    
    # Try to find a user with atoms
    res = db.table("Atoms").select("user_id").limit(1).execute()
    if res.data:
        uid = res.data[0]['user_id']
        build_graph(uid)
    else:
        logger.error("No atoms found in DB to build graph.")
