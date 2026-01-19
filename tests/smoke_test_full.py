import os
import sys
import time
import requests
import json
from dotenv import load_dotenv

# Load env vars
load_dotenv()

API_URL = "http://localhost:8000"

def run_smoke_test():
    print("--- 🚀 STARTING SYSTEM INTEGRITY CHECK (SMOKE TEST) ---")
    
    # 1. AUTH
    print("\n[Step 0] Authenticating...")
    try:
        # We'll use the script's logic directly since we can't easily capture its stdout if run as subprocess
        from supabase import create_client
        supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        res = supabase.auth.sign_in_with_password({"email": "testuser@example.com", "password": "testpassword"})
        
        if not res.session:
            print("❌ Auth Failed: No session returned. Ensure 'test@example.com' exists.")
            return
        
        token = res.session.access_token
        user_id = res.user.id
        print(f"✅ Authenticated as {user_id}")
        headers = {"Authorization": f"Bearer {token}"}
        
    except Exception as e:
        print(f"❌ Auth Exception: {e}")
        # Fallback for dev: Try to proceed if auth is disabled in API (unlikely)
        return

    # 2. TEST 1: INGESTION (Body)
    print("\n[Step 1] Testing Ingestion (The Body)...")
    try:
        payload = {
            "title": "Smoke Test Manual Source",
            "source_type": "uploaded_text",
            "file_upload_id": "manual_text_entry",
            "author": "System Check"
        }
        r = requests.post(f"{API_URL}/api/v1/sources", json=payload, headers=headers)
        if r.status_code == 202:
            data = r.json()
            source_id = data.get("source_id")
            print(f"✅ API Accepted Source: ID {source_id}")
            
            # Check for processing (Poll)
            print("   ⏳ Waiting for Worker to process source...")
            for _ in range(10):
                time.sleep(2)
                r_check = requests.get(f"{API_URL}/api/v1/sources", headers=headers)
                sources = r_check.json()
                target = next((s for s in sources if s["id"] == source_id), None)
                if target:
                    # In a real run, 'is_processed' might take longer due to LLM calls. 
                    # For smoke test, just seeing it in the list is 'Pass' for the API, 
                    # but seeing 'is_processed=True' is 'Pass' for the Worker.
                    print(f"   ℹ️ Current Status: is_processed={target.get('is_processed')}")
                    if target.get('is_processed'):
                        print("✅ Worker Successfully Processed Source!")
                        break
            else:
                print("⚠️ Worker didn't finish in 20s (expected if LLM is slow), but API is working.")
                
        else:
            print(f"❌ Ingestion Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Ingestion Exception: {e}")


    # 3. TEST 2: ARCHITECTING (Brain)
    print("\n[Step 2] Testing Architect (The Brain)...")
    volume_id = None
    try:
        payload = {
            "topic": "The Secret Life of Smoke Tests",
            "depth": 3,
            "lenses": []
        }
        r = requests.post(f"{API_URL}/api/v1/volumes/generate", json=payload, headers=headers)
        if r.status_code == 200:
            data = r.json()
            volume_id = data.get("volume_id")
            print(f"✅ API Started Volume Generation: ID {volume_id}")
            
            # Poll for Nodes
            print("   ⏳ Waiting for Architect to build graph...")
            for _ in range(30): # Wait up to 60s
                time.sleep(2)
                r_nodes = requests.get(f"{API_URL}/api/v1/volumes/{volume_id}/nodes", headers=headers)
                nodes = r_nodes.json()
                if len(nodes) > 0:
                    print(f"✅ Graph Population Detected! Found {len(nodes)} nodes.")
                    break
            else:
                 print("❌ Architect timed out. Check Worker logs.")
                 return # Cannot proceed to Step 3 without nodes
        else:
             print(f"❌ Volume Generation Failed: {r.status_code} - {r.text}")
             return
    except Exception as e:
        print(f"❌ Architect Exception: {e}")
        return

    # 4. TEST 3: SPRAWL (Interactive Graph)
    print("\n[Step 3] Testing Sprawl (Interactive Graph)...")
    if volume_id:
        try:
            # Get a node
            r_nodes = requests.get(f"{API_URL}/api/v1/volumes/{volume_id}/nodes", headers=headers)
            nodes = r_nodes.json()
            if not nodes:
                print("❌ No nodes available for expansion test.")
            else:
                target_node = nodes[0]
                print(f"   🎯 Targeting Node: {target_node['content'].get('title')} ({target_node['id']})")
                
                payload = {
                    "volume_id": volume_id,
                    "node_id": target_node['id'],
                    "branch_id": target_node.get('branch_id', 'main') 
                }
                
                start_time = time.time()
                r_expand = requests.post(f"{API_URL}/api/v1/nodes/expand", json=payload, headers=headers)
                duration = time.time() - start_time
                
                if r_expand.status_code == 200:
                    options = r_expand.json().get("options", [])
                    print(f"✅ Expansion Successful! Returned {len(options)} options in {duration:.2f}s.")
                    for opt in options:
                        print(f"      - {opt.get('title')}")
                else:
                    print(f"❌ Expansion Failed: {r_expand.status_code} - {r_expand.text}")

        except Exception as e:
            print(f"❌ Sprawl Exception: {e}")

    print("\n--- 🏁 SMOKE TEST COMPLETE ---")

if __name__ == "__main__":
    run_smoke_test()
