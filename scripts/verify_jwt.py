import os
import jwt

def verify_jwt():
    """
    Verifies a JWT using the Supabase JWT Secret.
    """
    try:
        # Get the JWT and secret from environment variables
        token = os.environ.get("JWT")
        secret = os.environ.get("SUPABASE_JWT_SECRET")

        if not token or not secret:
            print("Error: JWT and SUPABASE_JWT_SECRET must be set as environment variables.")
            return

        # Decode the JWT without verifying audience and issuer first, to inspect claims
        decoded_token = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_aud": False, "verify_iss": False}
        )

        print("JWT signature and expiration verified!")
        print("Decoded token claims:")
        print(decoded_token)

        # Manually verify issuer and audience
        if decoded_token.get("iss") != "https://fbzrobgstwkxwcsomtur.supabase.co/auth/v1":
            print(f"Issuer verification failed. Expected: https://fbzrobgstwkxwcsomtur.supabase.co/auth/v1, Got: {decoded_token.get('iss')}")
        else:
            print("Issuer verification successful.")

        if decoded_token.get("aud") != "authenticated":
            print(f"Audience verification failed. Expected: authenticated, Got: {decoded_token.get('aud')}")
        else:
            print("Audience verification successful.")


    except jwt.ExpiredSignatureError:
        print("Error: Token has expired.")
    except jwt.InvalidTokenError as e:
        print(f"Error: Invalid token - {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    verify_jwt()