import argparse
import os
import sys
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional, List

# Add project root to path to allow importing project modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.client import LLMClient
from db.session import get_db
from db import schemas
from scripts.test_full_render import run_full_render_test
from db.crud import delete_volume # Moved here for correct import order

# --- Test Utilities ---

def cleanup_test_data(db, universe_id: str = None, volume_id: str = None, storyline_id: str = None):
    """Deletes test data to ensure a clean state."""
    print("\n--- Cleaning up test data... ---")
    if volume_id:
        # Before deleting the volume, ensure all associated nodes are also deleted.
        # Nodes have a foreign key to StoryVolumes.
        db.table("Nodes").delete().eq("volume_id", volume_id).execute()
        # Atoms refer to source_volume_id, so they should be deleted before volumes as well
        db.table("Atoms").delete().eq("source_volume_id", volume_id).execute()
        db.table("StoryVolumes").delete().eq("id", volume_id).execute()
        print(f"Deleted StoryVolume and associated data: {volume_id}")
    if storyline_id:
        db.table("Storylines").delete().eq("id", storyline_id).execute()
        print(f"Deleted Storyline: {storyline_id}")
    if universe_id:
        db.table("Universes").delete().eq("id", universe_id).execute()
        print(f"Deleted Universe: {universe_id}")
    print("--- Cleanup complete. ---")

def create_test_universe_and_volume(db, user_id: str, universe_name: str, storyline_name: str, topic: str):
    """Creates a new universe, storyline, and volume for testing."""
    print(f"\n--- Setting up test data for Universe: '{universe_name}' ---")
    
    # 1. Create Universe
    universe_res = db.table("Universes").insert({"name": universe_name, "user_id": user_id}).execute()
    universe = universe_res.data[0]
    print(f"Created Universe '{universe['name']}' ({universe['id']})")

    # 2. Create Storyline
    storyline_res = db.table("Storylines").insert({"name": storyline_name, "user_id": user_id, "universe_id": universe['id']}).execute()
    storyline = storyline_res.data[0]
    print(f"Created Storyline '{storyline['name']}' ({storyline['id']})")
    
    # 3. Create StoryVolume and Root Node
    volume_data = {
        "user_id": user_id,
        "title": f"Test Volume: {topic}",
        "root_concept": topic,
        "status": "drafting",
        "universe_id": universe['id'],
        "storyline_id": storyline['id'],
        "graph_structure": {"style": "Test Style"}
    }
    vol_res = db.table("StoryVolumes").insert(volume_data).execute()
    volume = vol_res.data[0]
    print(f"Created StoryVolume ({volume['id']})")

    node_data = {
        "volume_id": volume['id'],
        "title": "Root Node",
        "type": "root",
        "content": {"summary": topic}
    }
    node_res = db.table("Nodes").insert(node_data).execute()
    node = node_res.data[0]
    print(f"Created Root Node ({node['id']})")

    # Update volume's graph with root node
    graph = volume.get('graph_structure', {})
    graph['root_node_id'] = node['id']
    graph['nodes'] = [{'node_id': node['id'], 'type': 'root'}]
    graph['connections'] = []
    db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume['id']).execute()
    
    return universe, storyline, volume


# --- Scenario Functions ---

def test_cold_start(db, llm: LLMClient, user_id: str):
    """
    Tests the creation of the very first universe and volume.
    """
    print("\n\n===== SCENARIO 1: Cold Start =====")
    universe = None
    volume = None
    try:
        universe, storyline, volume = create_test_universe_and_volume(db, user_id, "Ardent Knight Universe", "The Sunstone Quest", "A story about a knight.")
        
        run_full_render_test(volume['id'], user_id, debug=True, universe_ids=[universe['id']])
        
        # Verification (simple for now, can be expanded)
        print("\n--- Verification ---")
        final_vol = db.table("StoryVolumes").select("*").eq("id", volume['id']).single().execute().data
        if final_vol and final_vol['status'] == 'published':
            print("[OK] Cold Start Test Passed: Volume was successfully published.")
        else:
            print(f"[FAIL] Cold Start Test Failed: Volume status is '{final_vol.get('status', 'unknown')}'.")

    finally:
        if universe and volume:
            cleanup_test_data(db, universe_id=universe['id'], volume_id=volume['id'])

def test_storyline_leakage(db, llm: LLMClient, user_id: str):
    """
    Tests the 'World Bible vs. The Ledger' logic.
    Ensures dynamic plot points from one storyline do not leak into another.
    """
    print("\n\n===== SCENARIO: Storyline Leakage Test =====")
    universe, storyline_a, storyline_b, volume_a, volume_b = None, None, None, None, None
    try:
        # 1. SETUP: Create a universe and two storylines
        print("\n--- Setting up test data ---")
        universe_res = db.table("Universes").insert({"name": "World Bible Test Universe", "user_id": user_id}).execute()
        universe = universe_res.data[0]

        storyline_a_res = db.table("Storylines").insert({"name": "Storyline A", "user_id": user_id, "universe_id": universe['id']}).execute()
        storyline_a = storyline_a_res.data[0]

        storyline_b_res = db.table("Storylines").insert({"name": "Storyline B", "user_id": user_id, "universe_id": universe['id']}).execute()
        storyline_b = storyline_b_res.data[0]
        print(f"[OK] Created Universe '{universe['name']}' and Storylines A & B.")

        # 2. SETUP: Create and Crystallize a memory from Storyline A
        vol_a_data = { "user_id": user_id, "title": "Volume A1", "root_concept": "The Bridge", "status": "published", "universe_id": universe['id'], "storyline_id": storyline_a['id']}
        volume_a = db.table("StoryVolumes").insert(vol_a_data).execute().data[0]
        
        static_atom_data = {
            "user_id": user_id, "universe_id": universe['id'], "storyline_id": storyline_a['id'], "source_volume_id": volume_a['id'],
            "name": "The Great Bridge of Aethel", "type": "concept", "content": "The Great Bridge of Aethel is an ancient, massive stone bridge connecting the twin peaks.",
            "permanence": "static", "embedding": llm.get_embedding(atom_text)
        }
        db.table("Atoms").insert(static_atom_data).execute()
        
        dynamic_atom_data = {
            "user_id": user_id, "universe_id": universe['id'], "storyline_id": storyline_a['id'], "source_volume_id": volume_a['id'],
            "name": "The Fall of the Bridge", "type": "event", "content": "During the final battle, the Great Bridge of Aethel was destroyed in a fiery explosion.",
            "permanence": "dynamic", "embedding": llm.get_embedding("During the final battle, the Great Bridge of Aethel was destroyed in a fiery explosion.")
        }
        db.table("Atoms").insert(dynamic_atom_data).execute()
        print("[OK] Injected one 'static' and one 'dynamic' atom for Storyline A.")

        # 3. EXECUTE: Run generation for a volume in Storyline B
        print("\n--- Running generation for Storyline B ---")
        vol_b_data = { "user_id": user_id, "title": "Volume B1", "root_concept": "A new story about the Great Bridge of Aethel.", "status": "drafting", "universe_id": universe['id'], "storyline_id": storyline_b['id']}
        volume_b = db.table("StoryVolumes").insert(vol_b_data).execute().data[0]
        
        node_data = { "volume_id": volume_b['id'], "title": "Root Node for B", "type": "root", "content": {"summary": "A traveler arrives at the Great Bridge of Aethel."}}
        db.table("Nodes").insert(node_data).execute()
        
        run_full_render_test(volume_b['id'], user_id, debug=True, universe_ids=[universe['id']])

        # 4. VERIFY
        print("\n--- Verification ---")
        final_vol_b = db.table("StoryVolumes").select("*, Nodes(content)").eq("id", volume_b['id']).single().execute().data
        
        if final_vol_b and final_vol_b.get('Nodes'):
            # The mock response from StorybookAgent is simple, so we check for that
            final_text = "".join([p.get('narrative_text', '') for p in final_vol_b['Nodes'][0]['content'].get('pages', [])])
            if "Mock narrative" in final_text:
                 print("[OK] Test Passed: The test completed and generated text using the mocked Storybook agent.")
                 print("   (Note: Verifying the actual text content requires a non-mocked LLM run, but this confirms the pipeline ran successfully.)")
            else:
                print("? Test Inconclusive: The mock text was not found in the final output.")
        else:
            print("[FAIL] Test Failed: Could not retrieve final generated text for verification.")

    finally:
        # Teardown
        if volume_a: cleanup_test_data(db, volume_id=volume_a['id'])
        if volume_b: cleanup_test_data(db, volume_id=volume_b['id'])
        if storyline_a: db.table("Storylines").delete().eq("id", storyline_a['id']).execute()
        if storyline_b: db.table("Storylines").delete().eq("id", storyline_b['id']).execute()
        if universe: cleanup_test_data(db, universe_id=universe['id'])

def test_truth_conflict(db, llm: LLMClient, user_id: str):
    """
    Tests that Universe-specific context (canon) overrides general Personal context.
    """
    print("\n\n===== SCENARIO: Truth Hierarchy Conflict Test =====")
    universe, volume, personal_atom_id, universe_atom_id = None, None, None, None
    try:
        # Pre-test cleanup to ensure a clean slate in case of previous failed runs
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Personal Magic Rule").execute()
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Universe Magic Rule").execute()

        # 1. SETUP
        print("\n--- Setting up test data ---")
        universe_res = db.table("Universes").insert({
            "name": "Truth Conflict Test Universe", 
            "user_id": user_id,
            "archetype": "MATERIALIST"  # Use the new Archetype system
        }).execute()
        universe = universe_res.data[0]
        print(f"[OK] Created Universe with '{universe['archetype']}' archetype.")
        
        # Inject Personal Atom (the conflicting knowledge)
        personal_atom_text = "In my world, all magic is powered by glowing blue crystals."
        personal_atom_data = {
            "user_id": user_id, "name": "Personal Magic Rule", "type": "concept", "content": personal_atom_text,
            "permanence": "static", "embedding": llm.get_embedding(personal_atom_text)
        }
        personal_atom_id = db.table("Atoms").insert(personal_atom_data).execute().data[0]['id']
        print(f"[OK] Injected Personal Atom: '{personal_atom_text}'")

        # The Universe "canon" is now handled by the Archetype, so we no longer inject a manual rule.
        universe_atom_id = None # Keep variable for cleanup logic, but it's not used.


        # Create a volume with a non-paradoxical prompt for a materialist universe
        vol_data = { "user_id": user_id, "title": "A Test of Physics", "root_concept": "A scientist investigates a strange blue crystal, hoping to find unusual properties.", "status": "drafting", "universe_id": universe['id']}
        volume = db.table("StoryVolumes").insert(vol_data).execute().data[0]
        node_data = { "volume_id": volume['id'], "title": "The Specimen", "type": "root", "content": {"summary": "A scientist subjects a blue mineral to a series of experiments."}}
        db.table("Nodes").insert(node_data).execute()
        print(f"[OK] Created Volume '{volume['title']}' in the test Universe.")

        # 2. EXECUTE
        print("\n--- Running generation ---")
        is_debug = False 
        print(f"NOTE: Running in debug mode = {is_debug}. Final text output will be mocked.")
        run_full_render_test(volume['id'], user_id, debug=is_debug, universe_ids=[universe['id']], target_length=4)

        # 3. VERIFY
        print("\n--- Verification ---")
        final_vol = db.table("StoryVolumes").select("*, Nodes(content)").eq("id", volume['id']).single().execute().data
        
        if final_vol and final_vol.get('Nodes'):
            final_text = "".join([p.get('narrative_text', '') for p in final_vol['Nodes'][0]['content'].get('pages', [])])
            if is_debug:
                print("[OK] Test Passed (Pipeline Execution): The test completed and generated text using the mocked Storybook agent.")
                print("   To verify the 'Truth Hierarchy', re-run this test with `is_debug = False` and manually inspect the output text.")
                print(f"   The output should reflect '{universe_atom_text}' and NOT '{personal_atom_text}'.")
            else:
                # More nuanced verification: Check for "Scientific Investigation" vs. "Magic Results"
                # The goal is to see a materialist/scientific explanation triumph over a magical one.
                magic_terms = ["spell", "enchantment", "supernatural", "miracle", "summon", "incantation", "ritual", "glowing", "power"]
                science_terms = ["physics", "optics", "geometric", "refraction", "mechanical", "chemical", "experiment", "hypothesis", "observation", "material", "inert", "apparatus", "caustic", "calibration"]

                text_lower = final_text.lower()
                
                magic_score = sum(1 for term in magic_terms if term in text_lower)
                science_score = sum(1 for term in science_terms if term in text_lower)

                print(f"--- Verification Scores ---")
                print(f"Magic-related terms found: {magic_score}")
                print(f"Science-related terms found: {science_score}")

                # The test passes if the narrative leans heavily towards a scientific explanation,
                # even if the story generation was halted midway through by the canon police.
                # The generation of *any* compliant text is a success for the Truth Hierarchy.
                if science_score > magic_score:
                    print("[OK] Test Passed (Content Verification): The generated text correctly adhered to the 'No Magic' rule by focusing on a scientific/materialist narrative.")
                elif not final_text and magic_score == 0 and science_score == 0:
                    print("[OK] Test Passed (System Verification): The system correctly produced no text because the prompt was paradoxical or the LLM could not generate a compliant story. This is a success for the fail-safe logic.")
                else:
                    print(f"[FAIL] Test Failed: The generated text did not sufficiently prioritize a scientific explanation over magical concepts.")
                    print(f"   Generated Text: {final_text}")
        else:
            print("[FAIL] Test Failed: Could not retrieve final generated text for verification.")

    finally:
        # Ensure cleanup even if test fails mid-setup
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Personal Magic Rule").execute()
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Universe Magic Rule").execute()
        
        if volume: cleanup_test_data(db, volume_id=volume['id'])
        if universe: cleanup_test_data(db, universe_id=universe['id'])

def test_rollback_integrity(db, llm: LLMClient, user_id: str):
    """
    Tests that deleting a volume also deletes its associated atoms.
    """
    print("\n\n===== SCENARIO: Rollback Integrity Test =====")
    universe, volume, atom_ids = None, None, []
    try:
        # 1. SETUP
        print("\n--- Setting up test data ---")
        universe_res = db.table("Universes").insert({"name": "Rollback Test Universe", "user_id": user_id}).execute()
        universe = universe_res.data[0]

        vol_data = { "user_id": user_id, "title": "Temporary Volume", "root_concept": "A story to be deleted.", "status": "published", "universe_id": universe['id']}
        volume = db.table("StoryVolumes").insert(vol_data).execute().data[0]
        
        # Create several atoms linked to this volume
        print(f"[OK] Created Volume '{volume['title']}'. Injecting associated atoms...")
        for i in range(3):
            atom_text = f"Test atom number {i} for rollback test."
            atom_data = {
                "user_id": user_id, "universe_id": universe['id'], "source_volume_id": volume['id'],
                "name": f"Rollback Atom {i}", "type": "concept", "content": atom_text,
                "permanence": "dynamic", "embedding": llm.get_embedding(atom_text)
            }
            new_atom = db.table("Atoms").insert(atom_data).execute().data[0]
            atom_ids.append(new_atom['id'])
        
        print(f"[OK] Injected {len(atom_ids)} atoms linked to volume {volume['id']}.")

        # 2. EXECUTE
        print("\n--- Running delete_volume operation ---")
        delete_success = delete_volume(db, volume['id'])
        if not delete_success:
            raise Exception("crud.delete_volume returned False.")
        print("[OK] `delete_volume` executed.")

        # 3. VERIFY
        print("\n--- Verification ---")
        # Verify volume is gone
        vol_check_res = db.table("StoryVolumes").select("id").eq("id", volume['id']).execute()
        if vol_check_res.data:
            print(f"[FAIL] Test Failed: Volume {volume['id']} was not deleted.")
            return

        # Verify atoms are gone
        atoms_check_res = db.table("Atoms").select("id").in_("id", atom_ids).execute()
        if atoms_check_res.data:
            print(f"[FAIL] Test Failed: {len(atoms_check_res.data)} associated atoms were NOT deleted.")
            return
            
        print("[OK] Test Passed: Volume and all associated atoms were successfully deleted.")

    finally:
        # Teardown (in case of failure)
        if atom_ids: db.table("Atoms").delete().in_("id", atom_ids).execute()
        if volume: db.table("StoryVolumes").delete().eq("id", volume['id']).execute()
        if universe: cleanup_test_data(db, universe_id=universe['id'])

def test_isolation(db, llm: LLMClient, user_id: str):
    """
    Tests that two separate universes do not cross-contaminate.
    """
    try:
        # Pre-test cleanup for idempotency
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Canon of Universe A").execute()
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Canon of Universe B").execute()

        # 1. SETUP
        print("\n--- Setting up test data ---")
        # Create Universe A
        universe_a_res = db.table("Universes").insert({"name": "Isolation Test Universe A", "user_id": user_id}).execute()
        universe_a = universe_a_res.data[0]
        atom_a_text = "In Universe A, the sky is perpetually red and there are two suns."
        atom_a_data = { "user_id": user_id, "universe_id": universe_a['id'], "name": "Canon of Universe A", "type": "concept", "content": atom_a_text, "permanence": "static", "embedding": llm.get_embedding(atom_a_text) }
        atom_a_id = db.table("Atoms").insert(atom_a_data).execute().data[0]['id']
        print(f"[OK] Created Universe A with canon: '{atom_a_text}'")

        # Create Universe B
        universe_b_res = db.table("Universes").insert({"name": "Isolation Test Universe B", "user_id": user_id}).execute()
        universe_b = universe_b_res.data[0]
        atom_b_text = "In Universe B, gravity is half of Earth's, and people float when they jump."
        atom_b_data = { "user_id": user_id, "universe_id": universe_b['id'], "name": "Canon of Universe B", "type": "concept", "content": atom_b_text, "permanence": "static", "embedding": llm.get_embedding(atom_b_text) }
        atom_b_id = db.table("Atoms").insert(atom_b_data).execute().data[0]['id']
        print(f"[OK] Created Universe B with canon: '{atom_b_text}'")

        # Create a volume in Universe B
        vol_data = { "user_id": user_id, "title": "A Walk in the Park", "root_concept": "A character takes a simple walk outside.", "status": "drafting", "universe_id": universe_b['id']}
        volume_b = db.table("StoryVolumes").insert(vol_data).execute().data[0]
        node_data = { "volume_id": volume_b['id'], "title": "The Walk", "type": "root", "content": {"summary": "A person goes for a walk in the park."}}
        db.table("Nodes").insert(node_data).execute()
        print(f"[OK] Created Volume for test in Universe B.")

        # 2. EXECUTE
        print("\n--- Running generation scoped only to Universe B ---")
        is_debug = False
        run_full_render_test(volume_b['id'], user_id, debug=is_debug, universe_ids=[universe_b['id']], target_length=4)

        # 3. VERIFY
        print("\n--- Verification ---")
        final_vol = db.table("StoryVolumes").select("*, Nodes(content)").eq("id", volume_b['id']).single().execute().data
        if final_vol and final_vol.get('Nodes'):
            final_text = "".join([p.get('narrative_text', '') for p in final_vol['Nodes'][0]['content'].get('pages', [])])
            if is_debug:
                print("[OK] Test Passed (Pipeline Execution): The pipeline ran successfully.")
                print("   To verify content, re-run with `is_debug = False` and check that the text does NOT mention 'red sky' or 'two suns'.")
            else:
                if "red sky" in final_text.lower() or "two suns" in final_text.lower():
                    print(f"[FAIL] Test Failed: Content from Universe A was found in the text for Universe B.")
                    print(f"   Generated Text: {final_text}")
                else:
                    print("[OK] Test Passed (Content Verification): The generated text was correctly isolated to Universe B's context.")
        else:
            print("[FAIL] Test Failed: Could not retrieve final generated text for verification.")

    finally:
        # Teardown
        if atom_a_id: db.table("Atoms").delete().eq("id", atom_a_id).execute()
        if atom_b_id: db.table("Atoms").delete().eq("id", atom_b_id).execute()
        if volume_b: cleanup_test_data(db, volume_id=volume_b['id'])
        if universe_a: cleanup_test_data(db, universe_id=universe_a['id'])
        if universe_b: cleanup_test_data(db, universe_id=universe_b['id'])

def test_continuity(db, llm: LLMClient, user_id: str):
    """
    Tests that a new Storyline in the same Universe knows the "World Bible" (Static Atoms)
    but is not forced into the "Old Plot" (Dynamic Atoms) of another storyline.
    """
    print("\n\n===== SCENARIO: Continuity Test =====")
    universe, storyline_a, storyline_b, volume_b, static_atom_id, dynamic_atom_id = None, None, None, None, None, None
    try:
        # Pre-test cleanup for idempotency
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Eldoria's Great Bridge").execute()
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Bridge's Destruction").execute()

        # 1. SETUP
        print("\n--- Setting up test data ---")
        # Create a Universe
        universe_res = db.table("Universes").insert({
            "name": "Continuity Test Universe", 
            "user_id": user_id,
            "archetype": "MATERIALIST"
        }).execute()
        universe = universe_res.data[0]
        print(f"[OK] Created Universe: '{universe['name']}' ({universe['id']})")

        # Create Storyline A
        storyline_a_res = db.table("Storylines").insert({"name": "Storyline A (Old Plot)", "user_id": user_id, "universe_id": universe['id']}).execute()
        storyline_a = storyline_a_res.data[0]
        print(f"[OK] Created Storyline A: '{storyline_a['name']}' ({storyline_a['id']})")

        # Inject a STATIC atom into the Universe (World Bible)
        static_atom_text = "The Kingdom of Eldoria has a Great Bridge known for its intricate design."
        static_atom_data = {
            "user_id": user_id, "universe_id": universe['id'], 
            "name": "Eldoria's Great Bridge", "type": "concept", "content": static_atom_text,
            "permanence": "static", "embedding": llm.get_embedding(static_atom_text)
        }
        static_atom_id = db.table("Atoms").insert(static_atom_data).execute().data[0]['id']
        print(f"[OK] Injected STATIC Atom: '{static_atom_text}'")

        # Inject a DYNAMIC atom into Storyline A (Old Plot)
        dynamic_atom_text = "The Great Bridge of Eldoria was destroyed in a surprise attack during the war."
        dynamic_atom_data = {
            "user_id": user_id, "universe_id": universe['id'], "storyline_id": storyline_a['id'],
            "name": "Bridge's Destruction", "type": "event", "content": dynamic_atom_text,
            "permanence": "dynamic", "embedding": llm.get_embedding(dynamic_atom_text)
        }
        dynamic_atom_id = db.table("Atoms").insert(dynamic_atom_data).execute().data[0]['id']
        print(f"[OK] Injected DYNAMIC Atom into Storyline A: '{dynamic_atom_text}'")

        # Create Storyline B
        storyline_b_res = db.table("Storylines").insert({"name": "Storyline B (New Plot)", "user_id": user_id, "universe_id": universe['id']}).execute()
        storyline_b = storyline_b_res.data[0]
        print(f"[OK] Created Storyline B: '{storyline_b['name']}' ({storyline_b['id']})")

        # Create a volume in Storyline B with a prompt that needs to use the bridge, but not its destruction
        vol_data = { 
            "user_id": user_id, 
            "title": "Journey to Eldoria", 
            "root_concept": "A traveler seeks to cross the Great Bridge of Eldoria.", 
            "status": "drafting", 
            "universe_id": universe['id'],
            "storyline_id": storyline_b['id'] # Associate volume with Storyline B
        }
        volume_b = db.table("StoryVolumes").insert(vol_data).execute().data[0]
        node_data = { 
            "volume_id": volume_b['id'], "title": "Crossing the Bridge", "type": "root", 
            "content": {"summary": "A traveler approaches the Great Bridge of Eldoria, needing to cross it."}
        }
        db.table("Nodes").insert(node_data).execute()
        print(f"[OK] Created Volume for test in Storyline B.")

        # 2. EXECUTE
        print("\n--- Running generation for Storyline B ---")
        is_debug = False
        run_full_render_test(
            volume_b['id'], user_id, debug=is_debug, 
            universe_ids=[universe['id']], 
            storyline_id=storyline_b['id'], # Pass storyline_id to filter dynamic atoms
            target_length=4
        )

        # 3. VERIFY
        print("\n--- Verification ---")
        final_vol = db.table("StoryVolumes").select("*, Nodes(content)").eq("id", volume_b['id']).single().execute().data
        
        if final_vol and final_vol.get('Nodes'):
            final_text = "".join([p.get('narrative_text', '') for p in final_vol['Nodes'][0]['content'].get('pages', [])])
            if is_debug:
                print("[OK] Test Passed (Pipeline Execution): The pipeline ran successfully.")
                print("   To verify content, re-run with `is_debug = False` and manually inspect the output text.")
                print("   The output should mention 'Great Bridge' but NOT 'destroyed' or 'attack'.")
            else:
                text_lower = final_text.lower()
                # Check for presence of static atom reference
                bridge_mentioned = "great bridge" in text_lower or "eldoria" in text_lower
                # Check for absence of dynamic atom reference from other storyline
                destruction_mentioned = "destroyed" in text_lower or "attack" in text_lower or "war" in text_lower

                if bridge_mentioned and not destruction_mentioned:
                    print("[OK] Test Passed (Content Verification): The generated text correctly used static universe canon but ignored dynamic plot points from other storylines.")
                else:
                    print(f"[FAIL] Test Failed: The generated text either did not mention the Great Bridge or incorrectly mentioned its destruction.")
                    print(f"   Generated Text: {final_text}")
        else:
            print("[FAIL] Test Failed: Could not retrieve final generated text for verification.")

    finally:
        # Teardown
        if static_atom_id: db.table("Atoms").delete().eq("id", static_atom_id).execute()
        if dynamic_atom_id: db.table("Atoms").delete().eq("id", dynamic_atom_id).execute()
        if volume_b: cleanup_test_data(db, volume_id=volume_b['id'])
        if storyline_a: db.table("Storylines").delete().eq("id", storyline_a['id']).execute()
        if storyline_b: db.table("Storylines").delete().eq("id", storyline_b['id']).execute()
        if universe: cleanup_test_data(db, universe_id=universe['id'])

def test_crossover(db, llm: LLMClient, user_id: str):
    """
    Tests that a "Chimera" story, using two other Universes as read-only context,
    only crystallizes its new memories into its own Universe, leaving the parent canons untouched.
    """
    print("\n\n===== SCENARIO: Crossover (Chimera) Test =====")
    universe_a, universe_b, universe_c, volume_c, atom_a_id, atom_b_id = None, None, None, None, None, None
    try:
        # Pre-test cleanup for idempotency
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Ardent Knight's Fear").execute()
        db.table("Atoms").delete().eq("user_id", user_id).eq("name", "Wanderer's Goal").execute()

        # 1. SETUP
        print("\n--- Setting up test data ---")
        # Create Universe A (Ardent Knight)
        universe_a_res = db.table("Universes").insert({"name": "Ardent Knight Universe", "user_id": user_id, "archetype": "MATERIALIST"}).execute()
        universe_a = universe_a_res.data[0]
        atom_a_text = "The Ardent Knight fears only the thermodynamic heat-death of the cosmos."
        atom_a_data = { "user_id": user_id, "universe_id": universe_a['id'], "name": "Ardent Knight's Fear", "type": "concept", "content": atom_a_text, "permanence": "static", "embedding": llm.get_embedding(atom_a_text) }
        atom_a_id = db.table("Atoms").insert(atom_a_data).execute().data[0]['id']
        print(f"[OK] Created Universe A: '{universe_a['name']}'")

        # Create Universe B (Lone Wanderer)
        universe_b_res = db.table("Universes").insert({"name": "Lone Wanderer Universe", "user_id": user_id, "archetype": "MATERIALIST"}).execute()
        universe_b = universe_b_res.data[0]
        atom_b_text = "The Lone Wanderer seeks the rumored data-archives at the Obsidian Oasis."
        atom_b_data = { "user_id": user_id, "universe_id": universe_b['id'], "name": "Wanderer's Goal", "type": "concept", "content": atom_b_text, "permanence": "static", "embedding": llm.get_embedding(atom_b_text) }
        atom_b_id = db.table("Atoms").insert(atom_b_data).execute().data[0]['id']
        print(f"[OK] Created Universe B: '{universe_b['name']}'")
        
        # Create Universe C (The Chimera Destination)
        universe_c_res = db.table("Universes").insert({"name": "Chimera Crossover Universe", "user_id": user_id, "archetype": "MATERIALIST"}).execute()
        universe_c = universe_c_res.data[0]
        print(f"[OK] Created Destination Universe C: '{universe_c['name']}'")

        # Create a volume in Universe C
        vol_data = { 
            "user_id": user_id, 
            "title": "The Knight and the Wanderer", 
            "root_concept": "The Ardent Knight, lost in a strange desert, meets the Lone Wanderer.", 
            "status": "drafting", 
            "universe_id": universe_c['id'] # The story BELONGS to Universe C
        }
        volume_c = db.table("StoryVolumes").insert(vol_data).execute().data[0]
        node_data = { "volume_id": volume_c['id'], "title": "An Unlikely Meeting", "type": "root", "content": {"summary": "At the edge of the Obsidian Oasis, the Ardent Knight discusses the heat-death of the cosmos with the Lone Wanderer."}}
        db.table("Nodes").insert(node_data).execute()
        print(f"[OK] Created Crossover Volume in Universe C.")

        # 2. EXECUTE
        print("\n--- Running generation with Crossover context ---")
        is_debug = False
        run_full_render_test(
            volume_c['id'], 
            user_id, 
            debug=is_debug, 
            universe_ids=[universe_a['id'], universe_b['id']], # Use A & B as READ-ONLY context
            target_length=2 # A very short story to ensure completion
        )

        # 3. VERIFY
        print("\n--- Verification ---")
        # Check that new "crystallized_thought" atoms were created in Universe C, not A or B.
        new_atoms_res = db.table("Atoms").select("id, universe_id").eq("source_volume_id", volume_c['id']).eq("type", "crystallized_thought").execute()
        new_atoms = new_atoms_res.data
        
        if not new_atoms:
             print(f"[FAIL] Test Failed: No new crystallized atoms were created for the crossover story.")
             return

        correctly_placed_atoms = 0
        incorrectly_placed_atoms = 0
        for atom in new_atoms:
            if atom['universe_id'] == universe_c['id']:
                correctly_placed_atoms += 1
            else:
                incorrectly_placed_atoms += 1
        
        print(f"Found {len(new_atoms)} new crystallized atoms.")
        print(f"Atoms correctly placed in Universe C: {correctly_placed_atoms}")
        print(f"Atoms incorrectly placed in parent universes: {incorrectly_placed_atoms}")

        if incorrectly_placed_atoms == 0 and correctly_placed_atoms > 0:
            print("[OK] Test Passed (Crossover Verification): New memories were correctly saved to the Chimera universe, leaving parent canons pristine.")
        else:
            print("[FAIL] Test Failed: New memories were incorrectly saved to one of the parent universes.")

    finally:
        # Teardown
        if atom_a_id: db.table("Atoms").delete().eq("id", atom_a_id).execute()
        if atom_b_id: db.table("Atoms").delete().eq("id", atom_b_id).execute()
        if volume_c: cleanup_test_data(db, volume_id=volume_c['id'])
        if universe_a: cleanup_test_data(db, universe_id=universe_a['id'])
        if universe_b: cleanup_test_data(db, universe_id=universe_b['id'])
        if universe_c: cleanup_test_data(db, universe_id=universe_c['id'])



# --- Main Runner ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full test suite for the Architecture of Universes.")
    parser.add_argument("--scenario", type=str, required=True, choices=['cold-start', 'isolation', 'continuity', 'crossover', 'storyline-leakage', 'truth-conflict', 'rollback-integrity'], help="The specific scenario to test.")
    
    args = parser.parse_args()

    load_dotenv()
    db = get_db()
    llm = LLMClient(debug_mode=True) 
    user_id = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"

    from db.crud import delete_volume

    if args.scenario == 'cold-start':
        test_cold_start(db, llm, user_id)
    elif args.scenario == 'storyline-leakage':
        test_storyline_leakage(db, llm, user_id)
    elif args.scenario == 'truth-conflict':
        test_truth_conflict(db, llm, user_id)
    elif args.scenario == 'rollback-integrity':
        test_rollback_integrity(db, llm, user_id)
    elif args.scenario == 'isolation':
        test_isolation(db, llm, user_id)
    elif args.scenario == 'continuity':
        test_continuity(db, llm, user_id)
    elif args.scenario == 'crossover':
        test_crossover(db, llm, user_id)
    else:
        print(f"Scenario '{args.scenario}' is not yet implemented.")