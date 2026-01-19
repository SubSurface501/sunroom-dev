import logging
import time
import requests
import sys
import os

# Fix path to allow importing from worker
sys.path.append(os.getcwd())

from worker.src.agents.energy_middleware import EnergyModelMiddleware
from worker.src.agents.domain_expert import DomainExpertAgent
from db.session import get_db
from db import crud, schemas
import uuid
from llm.client import get_llm_client

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerificationTest")

def run_tests():
    db = get_db()
    llm = get_llm_client()
    middleware = EnergyModelMiddleware()
    # Mock worker for initialization
    worker = type('obj', (object,), {})
    domain_agent = DomainExpertAgent(db, worker, llm)
    
    # Use valid existing User ID (testuser@example.com)
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
    print(f"🆔 Test User ID: {user_id}")
    
    print("\n--- TEST 1: Hybrid Search Fidelity (RRF) ---")
    
    # 1. Ingest Atom with specific acronym
    rare_acronym = "XZ-14 protocol"
    atom_name = "Test Atom XZ-14"
    atom_content = f"The {rare_acronym} improves efficiency by 300% in quantum tunneling."
    embedding = llm.get_embedding(f"{atom_name}: {atom_content}")
    
    atom = schemas.Atom(
        user_id=user_id,
        name=atom_name,
        type="thought",
        content=atom_content,
        embedding=embedding,
        status="active"
    )
    crud.create_atom(db, atom)
    print(f"✅ Ingested Atom: {atom_name}")
    
    # 2. Query with broad semantic term (Dense would match, Sparse might fail if strict)
    # But we want to test Hybrid. We need a query that matches conceptually but we want 
    # to see if the Sparse component 'boosts' the exact match if we use the acronym.
    
    # Let's query specifically for the acronym to prove Sparse works where Dense might be fuzzy.
    query_text = "XZ-14 protocol efficiency"
    query_embedding = llm.get_embedding(query_text)
    
    results = crud.match_atoms_hybrid(
        db, 
        query_text=query_text, 
        embedding=query_embedding, 
        match_threshold=0.5, 
        match_count=5, 
        query_user_id=user_id
    )
    
    found = any(r['name'] == atom_name for r in results)
    if found:
        print(f"✅ Hybrid Search Found '{atom_name}' via RRF!")
        # Ideally check rank/score if visible, but existence proves retrieval path works.
    else:
        print(f"❌ Hybrid Search FAILED to find '{atom_name}'. Check index/RPC.")

    print("\n--- TEST 2: Geometric Constraint (Alpha * Beta) ---")
    
    # 1. Propose Hallucination (High Novelty, Zero Validity)
    # "The Chrono-Displacement Engine using flux capacitors" -> High Novelty (User hasn't written it)
    # But Zero Validity (OpenAlex has no papers on it).
    
    fake_idea = "The Chrono-Displacement Engine uses flux capacitors to reverse entropy."
    
    # Calculate Energy
    # We expect Validity to be low (0.3) and Novelty high (~1.0).
    # Geometric Mean = sqrt(1.0 * 0.3) = sqrt(0.3) = ~0.54
    # If we had high resonance (Alpha=1.0) and Zero Validity, it should collapse.
    
    # Let's test "Resonance" mode (Simulating user generating it).
    # If user generates it, Alpha (Resonance) might be low if they haven't written about it.
    # Let's assume we want to score it as a 'Novel Idea' (Novelty Mode).
    
    score, feedback = middleware.calculate_energy(
        text=fake_idea,
        context_type="novelty", 
        user_id=user_id
    )
    
    print(f"⚡ Calculated Score for Hallucination: {score}")
    print(f"📝 Critique: {feedback}")
    
    if score < 0.6:
        print("✅ System REJECTED Hallucination (Low Score). Constraint Active.")
    else:
        print(f"⚠️ Warning: Score {score} might be too high. Check Validity penalty logic.")

    print("\n--- TEST 3: External Grounding (OpenAlex) ---")
    
    # 1. Query Real Science
    # "Transformer Architecture" is real.
    query_science = "Attention is All You Need"
    
    external_concepts = domain_agent.search_external_concepts(query_science)
    
    if external_concepts and len(external_concepts) > 0:
        print(f"✅ OpenAlex returned {len(external_concepts)} results.")
        print(f"   Sample: {external_concepts[0]['concept_name']} - {external_concepts[0]['url']}")
        
        if "OpenAlex" in external_concepts[0]['source']:
            print("✅ Source verified as OpenAlex.")
    else:
        print("❌ OpenAlex Search Failed. Check API/Network.")

if __name__ == "__main__":
    run_tests()
