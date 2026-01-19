import requests
import os
import sys
import json
import argparse

# Hardcoded values for debugging - DO NOT USE IN PRODUCTION
API_URL = "https://sunroom-api-136102377810.us-central1.run.app"
USER_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6InppR25HK29WMk9wZENRQk8iLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2ZienJvYmdzdHdreHdjc29tdHVyLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI1N2E1MDczZi02ZGM1LTRiOTItYWQ5Yi05MjVkMDFmOGU4OGQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzYzMjQyOTA3LCJpYXQiOjE3NjMyMzkzMDcsImVtYWlsIjoidGVzdHVzZXJAZXhhbXBsZS5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2MzIzOTMwN31dLCJzZXNzaW9uX2lkIjoiOGNlOTQ0NzktYTAwMC00ZmQ4LWE5YTQtZDQ1MjM0Y2FjMmJhIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.vv1S34HCNEUpbaTYY05nUcxJp1uojinU5efMv6yfovY"
USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"

headers = {
    "Authorization": f"Bearer {USER_JWT}",
    "Content-Type": "application/json"
}

def call_debug_generator_prompt(api_url, headers, user_id):
    params = {
        "prompt_name": "PLAN_GENERATOR_PROMPT",
        "user_input": "Test user input",
        "context": "Test context",
        "trailhead_insight": "AI's emergent properties, when viewed through the lens of Gnostic cosmology, reveal a surprising parallel to the concept of the Demiurge.",
        "atom_names": "Gnosticism, AI, Demiurge",
        "current_outline": "Introduction"
    }
    body = {
        "script_id": "24a73b7f-006c-4f2d-8f99-a5c4015ef546",
        "user_id": user_id,
        "atom_ids": [
            "46b3370e-7ac0-450f-9a48-b7c01b7196f7",
            "a4d0f20d-ab7e-467a-b1ac-b379f16ace4d",
            "fa220fe4-66f3-4c7c-9369-f12e4b620ac7"
        ],
        "topic_name": "Test: The Interplay of AI and Ancient Philosophy",
        "trailhead_insight": "AI_s emergent properties, when viewed through the lens of Gnostic cosmology, reveal a surprising parallel to the concept of the Demiurge."
    }
    print("--- Calling /api/v1/admin/debug-generator-prompt ---")
    print("This may take several minutes to complete...")
    response = requests.post(f"{api_url}/api/v1/admin/debug-generator-prompt", headers=headers, json=body, params=params, timeout=600)
    return response

def call_list_models(api_url, headers):
    print("--- Calling /api/v1/admin/list-models ---")
    response = requests.get(f"{api_url}/api/v1/admin/list-models", headers=headers, timeout=60)
    return response

def call_index_atom(api_url, headers, payload):
    """Calls the index-atom endpoint."""
    print(f"--- Calling /api/v1/admin/index-atom ---")
    response = requests.post(f"{api_url}/api/v1/admin/index-atom", headers=headers, json=payload, timeout=60)
    return response


def call_run_proactive_discovery(api_url, headers, payload):
    """Calls the run-proactive-discovery endpoint."""
    print(f"--- Calling /api/v1/admin/run-proactive-discovery ---")
    response = requests.post(f"{api_url}/api/v1/admin/run-proactive-discovery", headers=headers, json=payload, timeout=60)
    return response


def call_hello_world(api_url, headers):
    """Calls the hello-world endpoint."""
    print(f"--- Calling /api/v1/admin/hello-world ---")
    response = requests.post(f"{api_url}/api/v1/admin/hello-world", headers=headers, timeout=60)
    return response


def call_health_check(api_url, output_file):
    """Calls the health check endpoint and writes the response to a file."""
    print("--- Calling /api/v1/health ---", file=sys.stderr, flush=True)
    try:
        response = requests.get(f"{api_url}/api/v1/health", timeout=60)
        print(f"Health Check HTTP Status Code: {response.status_code}", file=sys.stderr, flush=True)
        response.raise_for_status() # Raise an exception for HTTP errors
        with open(output_file, 'w') as f:
            f.write(response.text)
        print(f"Health check response written to {output_file}", file=sys.stderr, flush=True)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Network or request error during health check: {e}", file=sys.stderr, flush=True)
        return False

def main():
    parser = argparse.ArgumentParser(description="Make API calls to the SunRoom API.")
    parser.add_argument("--list-models", action="store_true", help="Call the /api/v1/admin/list-models endpoint.")
    parser.add_argument("--index-atom", action="store_true", help="Run the index_atom task.")
    parser.add_argument("--run-proactive-discovery", action="store_true", help="Run the proactive discovery task.")
    parser.add_argument("--hello", action="store_true", help="Run the hello_world task.")
    parser.add_argument("--payload-file", type=str, help="Path to a JSON file containing the payload for the task.")
    parser.add_argument("--jwt", type=str, help="JWT token for authentication.")
    parser.add_argument("--health-check", action="store_true", help="Call the /api/v1/health endpoint.")
    parser.add_argument("--health-check-output-file", type=str, default="health_check_output.json", help="File to write health check output to.")
    args = parser.parse_args()

    # Use the provided JWT from the command line if available, otherwise use the hardcoded one
    jwt = args.jwt if args.jwt else USER_JWT
    headers["Authorization"] = f"Bearer {jwt}"

    try:
        if args.list_models:
            response = call_list_models(API_URL, headers)
            response.raise_for_status()
            print(f"API Call Successful: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
        elif args.index_atom:
            if not args.payload_file:
                print("Error: --payload-file is required when using --index-atom.", file=sys.stderr, flush=True)
                sys.exit(1)
            with open(args.payload_file, 'r') as f:
                payload_dict = json.load(f)
            response = call_index_atom(API_URL, headers, payload_dict)
            response.raise_for_status()
            print(f"API Call Successful: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
        elif args.run_proactive_discovery:
            if not args.payload_file:
                print("Error: --payload-file is required when using --run-proactive-discovery.", file=sys.stderr, flush=True)
                sys.exit(1)
            with open(args.payload_file, 'r') as f:
                payload_dict = json.load(f)
            response = call_run_proactive_discovery(API_URL, headers, payload_dict)
            response.raise_for_status()
            print(f"API Call Successful: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
        elif args.hello:
            response = call_hello_world(API_URL, headers)
            response.raise_for_status()
            print(f"API Call Successful: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
        elif args.health_check:
            success = call_health_check(API_URL, args.health_check_output_file)
            if not success:
                sys.exit(1)
        else:
            # Default action if no other flags are provided
            print("No specific action requested. Use --list-models, --index-atom, or --health-check.", file=sys.stderr, flush=True)
            parser.print_help()
            sys.exit(0)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}", file=sys.stderr, flush=True)
        print(f"Response content: {http_err.response.text}", file=sys.stderr, flush=True)
        sys.exit(1)
    except Exception as err:
        print(f"An unexpected error occurred: {err}", file=sys.stderr, flush=True)
        sys.exit(1)
