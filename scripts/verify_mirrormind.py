import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: Missing Supabase credentials")
    sys.exit(1)

supabase = create_client(url, key)

tables_to_check = ["semantic_memories", "persona_profiles", "domain_concepts"]
missing_tables = []

for table in tables_to_check:
    print(f"Checking table: {table}...", end=" ")
    try:
        # Try to select 1 row. 
        # If table doesn't exist, Supabase API usually returns a 404 or specific error.
        response = supabase.table(table).select("*").limit(1).execute()
        print("EXISTS")
    except Exception as e:
        # Check error message
        print(f"MISSING or ERROR ({e})")
        missing_tables.append(table)

if missing_tables:
    print(f"\nMissing tables: {missing_tables}")
    sys.exit(1)
else:
    print("\nAll MirrorMind tables exist.")
    
    # Check for fidelity_weight column in persona_profiles
    print("Checking for fidelity_weight column in persona_profiles...", end=" ")
    try:
        response = supabase.table("persona_profiles").select("fidelity_weight").limit(1).execute()
        print("EXISTS")
    except Exception as e:
        print(f"MISSING ({e})")
        sys.exit(2) # Exit code 2 for missing column

    sys.exit(0)
