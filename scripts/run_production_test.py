
import os
import requests
import time
import argparse
import json

"""
End-to-End Production Workflow Test Script

This script simulates a user's full workflow to test the most intensive parts
of the content generation pipeline.

It will:
1. Ingest a small source text to ensure the knowledge base is not empty.
2. Trigger the Volume Architect to create a story blueprint.
3. Poll until the blueprint is ready.
4. Trigger the Manuscript Production pipeline, which runs many parallel agents.
5. Poll until the manuscript is complete.

This process is designed to generate a high volume of concurrent API calls
to the Gemini API, which will help us verify if and when rate limiting occurs.

HOW TO RUN:

1. Get Your Authentication JWT:
   - Log in to the Sun Room web application in your browser.
   - Open the browser's Developer Tools (usually F12 or Ctrl+Shift+I).
   - Go to the 'Application' tab (in Chrome/Edge) or 'Storage' tab (in Firefox).
   - Find 'Local Storage' for your application's domain (e.g., localhost:3000).
   - Find the key that looks like 'sb-xxxxxxxx-auth-token'.
   - Copy the long string value from the 'access_token' field within the JSON value.

2. Run the script from your terminal:
   python scripts/run_production_test.py "YOUR_COPIED_JWT_HERE"

"""

API_BASE_URL = "http://localhost:8000"

def run_test(jwt: str):
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    }
    
    # --- Step 1: Ingest a Source ---
    print("--- STEP 1: Ingesting a small source text... ---")
    source_data = {
        "title": "Test Source for Production Run",
        "raw_text": "A lone wanderer discovers a hidden library containing books that write themselves. Each book details a possible future, but reading a future sets it in stone. The wanderer must choose whether to know their destiny or remain free."
    }
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/sources", headers=headers, json=source_data)
        response.raise_for_status()
        source_id = response.json().get('source_id')
        print(f"✅ Source ingested successfully. Source ID: {source_id}")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Could not ingest source. Error: {e}")
        print(f"Response body: {e.response.text}")
        return

    # --- Step 2: Generate Volume Blueprint ---
    print("\n--- STEP 2: Triggering Volume Architect... ---")
    volume_data = {
        "topic": "The Library of Fate",
        "depth": 3 # A small depth is sufficient to generate a few nodes for parallel processing
    }
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/volumes/generate", headers=headers, json=volume_data)
        response.raise_for_status()
        volume_id = response.json().get('volume_id')
        print(f"✅ Volume generation started. Volume ID: {volume_id}")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Could not start volume generation. Error: {e}")
        print(f"Response body: {e.response.text}")
        return

    # --- Step 3: Poll for Architect Completion ---
    print("\n--- STEP 3: Waiting for Architect to finish blueprint... ---")
    max_polls = 60
    for i in range(max_polls):
        try:
            print(f"Polling attempt {i+1}/{max_polls}...")
            response = requests.get(f"{API_BASE_URL}/api/v1/volumes/{volume_id}", headers=headers)
            response.raise_for_status()
            volume_status = response.json().get('status')
            print(f"Current volume status: '{volume_status}'")
            if volume_status not in ["architecting", "starting"]:
                print("✅ Architect has completed the blueprint.")
                break
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Polling failed. Error: {e}")
            return
    else:
        print("❌ FAILED: Architect timed out.")
        return

    # --- Step 4: Trigger Manuscript Production ---
    print("\n--- STEP 4: Triggering Manuscript Production (High Concurrency Test)... ---")
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/volumes/{volume_id}/produce", headers=headers)
        response.raise_for_status()
        print(f"✅ Manuscript production started for Volume ID: {volume_id}")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Could not start manuscript production. Error: {e}")
        print(f"Response body: {e.response.text}")
        return
        
    # --- Step 5: Poll for Manuscript Completion ---
    print("\n--- STEP 5: Waiting for Manuscript to complete... ---")
    print("(This is the part where rate limiting is most likely to occur. Check your worker logs.)")
    for i in range(max_polls * 2): # Allow more time for writing
        try:
            print(f"Polling attempt {i+1}/{max_polls * 2}...")
            response = requests.get(f"{API_BASE_URL}/api/v1/volumes/{volume_id}", headers=headers)
            response.raise_for_status()
            volume_status = response.json().get('status')
            print(f"Current volume status: '{volume_status}'")
            if volume_status in ["text_ready", "completed", "published"]:
                print("✅ Manuscript production complete!")
                break
            time.sleep(10)
        except requests.exceptions.RequestException as e:
            print(f"Polling failed. Error: {e}")
            return
    else:
        print("❌ FAILED: Manuscript production timed out.")
        return
        
    print("\n--- TEST COMPLETE ---")
    print("Review your API and Celery worker logs now for any errors, especially '429 Too Many Requests'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a full production workflow test.")
    parser.add_argument("jwt", help="The JWT auth token for the user.")
    args = parser.parse_args()
    
    run_test(args.jwt)
