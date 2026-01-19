import os
import sys
from dotenv import load_dotenv

# Load Env BEFORE importing the processor so it finds the HF_TOKEN
load_dotenv() 

# Ensure current directory is in python path
sys.path.append(os.getcwd())

from services.ingestion.audio_atomizer import AudioAtomizer

# Mock Data - REPLACE THESE WITH REAL UUIDS FROM YOUR DB
USER_ID = "00000000-0000-0000-0000-000000000000" 
PROJECT_ID = "00000000-0000-0000-0000-000000000000"
SOURCE_ID = "00000000-0000-0000-0000-000000000000"
TEST_FILE = "test_interview.mp3" 

if __name__ == "__main__":
    print("--- Audio Atomizer Test ---")
    if not os.path.exists(TEST_FILE):
        print(f"❌ Please place a '{TEST_FILE}' in this folder to test.")
        print("You can download a sample audio file to run this test.")
    else:
        print(f"Processing {TEST_FILE}...")
        try:
            atomizer = AudioAtomizer(USER_ID, PROJECT_ID)
            atomizer.ingest(TEST_FILE, SOURCE_ID)
        except Exception as e:
            print(f"❌ Error during ingestion: {e}")
