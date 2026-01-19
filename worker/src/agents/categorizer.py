import logging
from collections import Counter
import numpy as np
from .base import BaseAgent
from db import crud

logger = logging.getLogger(__name__)

class CategorizerAgent(BaseAgent):
    """
    The Librarian's Assistant.
    Analyzes the atoms of a new source and suggests a category for it.
    """

    def run_task(self, source_id: str, user_id: str):
        logger.info(f"🤖 Categorizer Agent starting for source {source_id}...")

        try:
            # 1. Fetch all atoms associated with the new source
            source_atoms_res = self.db.table("Atoms").select("embedding").eq("resolution_source_id", source_id).execute()
            if not source_atoms_res.data:
                logger.warning(f"Categorizer: No atoms found for source {source_id}. Cannot categorize.")
                return "No atoms to analyze."

            source_atoms = source_atoms_res.data
            
            # 2. Calculate the average embedding for the new source's atoms
            # This creates a single vector representing the "center of mass" of the document's concepts
            embeddings = [np.array(atom['embedding']) for atom in source_atoms if atom.get('embedding')]
            if not embeddings:
                logger.warning(f"Categorizer: No embeddings found in the atoms for source {source_id}.")
                return "No embeddings to analyze."
            
            avg_embedding = np.mean(embeddings, axis=0).tolist()

            # 3. Perform a vector search to find similar atoms from OTHER sources
            # We exclude the current source_id to avoid matching the same atoms.
            # We use the 'match_atoms_with_category' RPC function which we need to create.
            # For now, let's assume a function that returns atoms with their category info.
            
            # Hypothetical RPC call - we will need to create this.
            # For now, we will use the existing match_atoms and then fetch category info.
            # This is less efficient but works with the current schema.
            
            logger.info("Searching for similar atoms to determine category...")
            similar_atoms = crud.match_atoms_by_embedding(
                db=self.db,
                query_embedding=avg_embedding,
                match_threshold=0.7,  # Use a reasonably high threshold for good matches
                match_count=10,       # Get a decent sample size
                query_user_id=user_id
            )
            
            # Filter out atoms from the same source
            similar_atoms = [atom for atom in similar_atoms if atom.get('resolution_source_id') != source_id]

            if not similar_atoms:
                logger.info("No similar atoms found in other sources. Cannot determine category.")
                return "No similar atoms found."

            # 4. Analyze the categories of the similar atoms
            # Fetch the category for each similar atom's source
            source_ids = {atom['resolution_source_id'] for atom in similar_atoms if atom.get('resolution_source_id')}
            if not source_ids:
                logger.info("Similar atoms have no source links. Cannot determine category.")
                return "No linked sources found."

            source_categories_res = self.db.table("Sources").select("id, category_id").in_("id", list(source_ids)).execute()
            
            category_map = {src['id']: src['category_id'] for src in source_categories_res.data}
            
            category_votes = []
            for atom in similar_atoms:
                source_of_atom = atom.get('resolution_source_id')
                if source_of_atom and source_of_atom in category_map:
                    category_id = category_map[source_of_atom]
                    if category_id:
                        category_votes.append(category_id)

            if not category_votes:
                logger.info("No categories found among similar atoms.")
                return "No categories to vote on."

            # 5. Determine the winning category and confidence
            # Use Counter to find the most common category
            vote_counts = Counter(category_votes)
            winner, num_votes = vote_counts.most_common(1)[0]
            
            confidence = num_votes / len(similar_atoms)
            
            logger.info(f"Category vote results: {vote_counts}. Winner: {winner} with {confidence:.2f} confidence.")

            # 6. Assign the category if confidence is high enough
            CONFIDENCE_THRESHOLD = 0.4 # At least 40% of the top 10 similar atoms must share a category
            
            if confidence >= CONFIDENCE_THRESHOLD:
                logger.info(f"Confidence threshold met. Assigning source {source_id} to category {winner}.")
                self.db.table("Sources").update({"category_id": winner}).eq("id", source_id).execute()
                return f"Assigned to category {winner}."
            else:
                logger.info("Confidence threshold not met. Leaving category unassigned.")
                # Future enhancement: save `winner` as `suggested_category_id`
                return "Confidence too low."

        except Exception as e:
            logger.error(f"Categorizer Agent failed for source {source_id}: {e}", exc_info=True)
            # Optionally, update the source status to 'categorization_failed'
            return "Failed."

