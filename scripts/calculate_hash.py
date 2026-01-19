import hashlib
import os
import sys

SECRET = os.environ.get("SUPABASE_JWT_SECRET")

if not SECRET:
    print("Error: SUPABASE_JWT_SECRET environment variable not set.")
    sys.exit(1)

hasher = hashlib.sha256()
hasher.update(SECRET.encode('utf-8'))
full_hash = hasher.hexdigest()
print(full_hash[:8])
