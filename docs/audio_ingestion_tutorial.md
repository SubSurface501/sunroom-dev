## Tutorial: Ingesting Local Audio Files for Atomization

This tutorial guides you through using the `ingest_local_audio.py` script to add your local MP3 (or other audio) files to your knowledge graph. This process involves transcribing the audio, uploading the text to your Supabase database as "Sources," and then breaking it down into "Atoms" (concepts, persons, books).

---

### Objective

To populate your Sun Room knowledge graph with content from your local audio files, automatically transcribing and atomizing them.

---

### Prerequisites

Before you begin, ensure the following are in place:

1.  **Python 3.8+**: Installed and accessible in your PATH.
2.  **`pip`**: Python's package installer.
3.  **`openai-whisper`**: The transcription library.
    ```powershell
pip install openai-whisper
    ```
4.  **`ffmpeg`**: Required by Whisper for audio processing.
    *   **Windows**: Open PowerShell as Administrator and run `winget install Gyan.FFmpeg`. Restart your terminal after installation.
    *   **macOS/Linux**: Install via your package manager (e.g., `brew install ffmpeg` or `sudo apt install ffmpeg`).
5.  **Environment Variables (`.env` file)**: Ensure your project's `.env` file (in the `sunroom_dev` root directory) contains:
    *   `SUPABASE_URL`
    *   `SUPABASE_SERVICE_KEY`
    *   `CELERY_BROKER_URL` (e.g., `redis://127.0.0.1:6379/0`)
6.  **Celery Worker Running**: Your Celery worker must be active to process the `agents.indexing.run` tasks dispatched by the ingestion script.
    *   If not running, start it from your `sunroom_dev` directory:
        ```powershell
python -m celery -A worker.src.agents.tasks.worker worker --loglevel=info --pool=threads --concurrency=10
        ```
        *(Adjust `--concurrency` based on your system's capabilities).*

---

### Step 1: Organize Your Audio Files

The script is designed to treat subfolders within your chosen root directory as "playlists" or categories.

1.  **Create a Root Audio Folder**: Choose a main folder for all your audio content, e.g., `C:\Users\grunt\MyAudioLibrary`.
2.  **Create Subfolders for Playlists/Topics**: Inside your root folder, create subfolders to categorize your MP3s.
    *   Example:
        ```
        C:\Users\grunt\MyAudioLibrary\
        ├── Gnosticism\
        │   ├── Ancient Texts Explained.mp3
        │   └── Sophia_The_Divine_Fallen.mp3
        └── Quantum_Physics\
            ├── Entanglement_101.mp3
            └── Particle_Wave_Duality.mp3
        ```
3.  **Place Your Audio Files**: Put your `.mp3`, `.m4a`, `.wav`, `.mp4`, `.mov`, or `.mkv` files into these subfolders.

---

### Step 2: Obtain Your User ID

The ingested sources need to be linked to a specific user in your Supabase database.

1.  **Find your User ID**: Look in your API or Celery worker logs for a line similar to:
    `User 75dadbbc-34da-4cb3-a75d-edaa5dcf7341 successfully authenticated...`
    Your User ID is the UUID string (e.g., `75dadbbc-34da-4cb3-a75d-edaa5dcf7341`).
    *   *Alternatively*, if you have Supabase access, query your `auth.users` table.

---

### Step 3: Run the Ingestion Script

Navigate to your `sunroom_dev` directory in your terminal and execute the `ingest_local_audio.py` script.

1.  **Example Command**:
    ```powershell
python ingest_local_audio.py "C:\Users\grunt\MyAudioLibrary" "75dadbbc-34da-4cb3-a75d-edaa5dcf7341" --model base
    ```
2.  **Arguments Explained**:
    *   `"C:\Users\grunt\MyAudioLibrary"`: Replace with the absolute path to *your* root audio folder (from Step 1).
    *   `"75dadbbc-34da-4cb3-a75d-edaa5dcf7341"`: Replace with *your* actual User ID (from Step 2).
    *   `--model base`: (Optional) Specifies the Whisper model size. Options: `tiny`, `base`, `small`, `medium`, `large`. Larger models are more accurate but require more resources and take longer. `base` is a good starting point.

---

### Expected Outcome

As the script runs, observe the output in both the script's terminal and your Celery worker terminal:

1.  **`ingest_local_audio.py` Output**:
    *   You'll see messages like `--- Scanning Folder: Gnosticism ---`.
    *   `Found: Ancient Texts Explained.mp3`.
    *   `-> Transcribing...` (This step can be very slow for long audio files).
    *   `-> Success! Transcript saved to: ... .txt`.
    *   `-> Inserting into Database...`.
    *   `-> Created Source ID: <UUID>`.
    *   `-> Dispatching Indexing Agent...`.
    *   If a file was already ingested, it will show `-> Skipping (Already Ingested...)`.

2.  **Celery Worker Output**:
    *   For each new `Source ID` created, your Celery worker will log: `Task agents.indexing.run[<UUID>] received`.
    *   The `IndexAtomAgent` will then process the transcript, extracting atoms and logging its progress.

3.  **Supabase Database**:
    *   The `Sources` table will be populated with new entries, containing the `raw_text` (transcript), `title` (filename), `user_id`, and `metadata` (including `playlist` and `source_type`).
    *   The `Atoms` table will be filled with concepts, persons, books, claims, and questions extracted from each transcript, all linked back to their respective `Source` records.

---

### Troubleshooting

*   **"Error: Path '<path>' not found."** : Double-check the path you provided to `ingest_local_audio.py`.
*   **"Error: Missing environment variables..."** : Verify your `.env` file and ensure all required variables are set.
*   **"Error: 'openai-whisper' ... not installed."** : Run `pip install openai-whisper`.
*   **"Error: 'ffmpeg' is not found..."** : Install `ffmpeg` as per prerequisites.
*   **Celery Worker Not Processing Tasks**:
    *   Ensure the worker is running (see Prerequisites).
    *   Check the worker's logs for any errors.
    *   If the worker was restarted recently, it might have lost track of some tasks. Re-run `ingest_local_audio.py` (it will skip already-ingested files).

---

Once your audio files are processed, your knowledge graph will be significantly richer, providing much more context for generating personalized story content!