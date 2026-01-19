import os
from db.session import get_db
from db import crud

def show_trailheads():
    try:
        db = get_db()
        # Hardcoded user_id from the test
        user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
        trailheads = crud.get_trailheads_for_user(db, user_id)
        
        print(f"\n--- Generated Trailheads ({len(trailheads)}) ---")
        for t in trailheads[:5]: # Show top 5
            print(f"\nTitle: {t.title}")
            print(f"Insight: {t.insight}")
            print(f"Related Atoms: {t.related_atom_ids}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    show_trailheads()

