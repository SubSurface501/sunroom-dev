import os
import json
import sys
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from llm.client import LLMClient

# 1. Load Environment
load_dotenv()

# 2. Initialize Clients
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Use the project's LLM client for consistency
llm_client = LLMClient()

def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2:
        return 0.0
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def simulate_agent_recall():
    print("\n🧠 SIMULATION: Storybook Agent 'Memory Check' 🧠")
    print("------------------------------------------------")
    
    # 3. The Scenario: Agent is writing a scene about the mind
    scene_concept = "A deep philosophical debate about the nature of the soul and human awareness."
    print(f"📝 SCENE CONCEPT: '{scene_concept}'")

    # 4. The "Encoding": Convert concept to Math using project's LLMClient
    print("... encoding query to vector ...")
    query_vector = llm_client.get_embedding(scene_concept)
    
    if not query_vector:
        print("Error: Failed to generate embedding for the scene concept.")
        return

    # 5. The "Monitor": Fetch all relevant atoms and perform client-side similarity search
    print("... fetching all 'concept' atoms and performing client-side vector search ...")
    
    user_id_for_debug = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" # Use the valid user ID found earlier
    atom_type_filter = "concept"
    match_threshold = 0.5
    match_count = 10

    try:
        # Fetch all atoms of the specified type for the user
        response = supabase.table("Atoms").select("id, name, type, metadata, embedding").eq("user_id", user_id_for_debug).eq("type", atom_type_filter).execute()
        all_atoms = response.data
        
        if not all_atoms:
            print(f"No atoms of type '{atom_type_filter}' found for user '{user_id_for_debug}'.")
            return

        scored_atoms = []
        for atom in all_atoms:
            atom_embedding = atom.get('embedding')
            
            if atom_embedding:
                # Ensure embedding is a list of floats (it might be a string from DB)
                if isinstance(atom_embedding, str):
                    try:
                        atom_embedding = json.loads(atom_embedding)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse embedding for atom {atom['id']}. Skipping.")
                        continue

                similarity = cosine_similarity(query_vector, atom_embedding)
                if similarity > match_threshold:
                    atom['similarity'] = similarity
                    scored_atoms.append(atom)
            else:
                print(f"Warning: Atom {atom['id']} ('{atom['name']}') has no embedding. Skipping.")

        # Sort by similarity (descending)
        scored_atoms.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
        matches = scored_atoms[:match_count]
        
        print(f"DEBUG: Total atoms fetched for type '{atom_type_filter}': {len(all_atoms)}")
        print(f"DEBUG: Matches after client-side scoring and filtering: {matches}")

        if matches:
            print(f"\n✅ SUCCESS: The Monitor found {len(matches)} relevant historical records (client-side).")
            for i, atom in enumerate(matches):
                print(f"\n   Match #{i+1}: {atom['name']} (Type: {atom['type']})")
                print(f"   Similarity: {atom['similarity']:.4f}")
                description = atom['metadata'].get('description', '')
                print(f"   Content Preview: {description[:150]}...")
                
                # Verification Logic: check if the re-indexed atom is found
                if "consciousness" in atom['name'].lower() or ("consciousness" in description.lower()):
                    print("   🌟 VERIFIED: It found the atom we just re-indexed!")
        else:
            print(f"\n❌ FAILURE: No matches found above threshold of {match_threshold}. (Check if relevant atoms exist and have embeddings)")

    except Exception as e:
        print(f"\n❌ ERROR during client-side search: {e}")

if __name__ == "__main__":
    simulate_agent_recall()