import hashlib

provided_secret = "CFGgfawskiOahDriXJEv/FF+M+ZuPNw0+YlTaMhmM2x8uVfdmMl6X2fHqJJcDRtNZIFfZ7m9f2D4hqGetkleBw=="

# Calculate SHA256 hash
hasher = hashlib.sha256()
hasher.update(provided_secret.encode('utf-8'))
full_hash = hasher.hexdigest()
secret_hash_partial = full_hash[:8]

print(f"Provided Secret Hash Start: {secret_hash_partial}")
print(f"Provided Secret Length: {len(provided_secret)}")
