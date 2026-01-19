import jwt
import json
import os
import sys

# The JWT to decode
JWT_TOKEN = os.environ.get("USER_JWT")

if not JWT_TOKEN:
    print("Error: USER_JWT environment variable not set.")
    sys.exit(1)

# Supabase URL from environment (needed for issuer comparison)
SUPABASE_URL = os.environ.get("SUPABASE_URL")

if not SUPABASE_URL:
    print("Error: SUPABASE_URL environment variable not set.")
    sys.exit(1)

try:
    # Decode without verification to inspect payload
    decoded_payload = jwt.decode(JWT_TOKEN, options={"verify_signature": False})
    print("--- Decoded JWT Payload ---")
    print(json.dumps(decoded_payload, indent=2))

    # Extract relevant claims
    issuer = decoded_payload.get("iss")
    audience = decoded_payload.get("aud")
    expiration = decoded_payload.get("exp")
    subject = decoded_payload.get("sub")

    print("\n--- Extracted Claims ---")
    print(f"Issuer (iss): {issuer}")
    print(f"Audience (aud): {audience}")
    print(f"Expiration (exp): {expiration} (Unix timestamp)")
    print(f"Subject (sub/user_id): {subject}")

    # Compare with expected values from api_server.py
    expected_audience = "authenticated"
    expected_issuer = f"{SUPABASE_URL}/auth/v1"

    print("\n--- Comparison with Expected Values (from api_server.py) ---")
    print(f"Expected Audience: {expected_audience}")
    print(f"Actual Audience:   {audience}")
    print(f"Audience Match: {audience == expected_audience}")

    print(f"Expected Issuer: {expected_issuer}")
    print(f"Actual Issuer:   {issuer}")
    print(f"Issuer Match: {issuer == expected_issuer}")

except jwt.PyJWTError as e:
    print(f"Error decoding JWT: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
