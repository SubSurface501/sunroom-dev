import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

# The two test users
users = [
    "75dadbbc-34da-4cb3-a75d-edaa5dcf7341", # jacob.ecommerce@gmail.com
    "67d2eb38-2bd4-467f-bf1c-fae879d8047d"  # jacob@thesunroom.ca
]

print("--- 🧹 Starting Mind Wipe ---")

for user_id in users:
    print(f"\nCleaning User {user_id}...")
    
    # 1. Delete Atoms (and links to sources via cascade usually, but explicit here)
    # Note: Atoms_to_Sources might need explicit delete if no cascade, but let's try.
    try:
        supabase.table("Atoms_to_Sources").delete().in_("atom_id", [
            a['id'] for a in supabase.table("Atoms").select("id").eq("user_id", user_id).execute().data
        ]).execute()
    except: 
        pass # Might be empty

    atoms = supabase.table("Atoms").delete().eq("user_id", user_id).execute()
    print(f" - Deleted {len(atoms.data)} Atoms")
    
    # 2. Delete Sources
    sources = supabase.table("Sources").delete().eq("user_id", user_id).execute()
    print(f" - Deleted {len(sources.data)} Sources")
    
    # 3. Delete Trailheads (Children first!)
    trails = supabase.table("Trailheads").delete().eq("user_id", user_id).execute()
    print(f" - Deleted {len(trails.data)} Trailheads")

    # 4. Delete Volumes (Parents)
    vols = supabase.table("StoryVolumes").delete().eq("user_id", user_id).execute()
    print(f" - Deleted {len(vols.data)} Volumes")
    
    # 5. Delete Projects (if owner)
    # Delete members first? Cascade usually handles, but let's be safe
    try:
        supabase.table("project_members").delete().eq("user_id", user_id).execute()
    except: pass
    
    projs = supabase.table("projects").delete().eq("owner_id", user_id).execute()
    print(f" - Deleted {len(projs.data)} Projects")

print("\n✅ Wipe Complete. Database is clean for test users.")