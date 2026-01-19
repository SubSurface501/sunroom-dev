import os
import sys
import argparse
import shutil
import subprocess

# --- Add FFmpeg to PATH at runtime ---
# Winget usually installs it here, but doesn't update the current process's ENV
possible_ffmpeg_paths = [
    r"C:\Program Files\ffmpeg\bin",
    os.path.join(os.getenv('LOCALAPPDATA'), r"Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin"),
    os.path.join(os.getenv('LOCALAPPDATA'), r"Microsoft\WinGet\Links")
]

for path in possible_ffmpeg_paths:
    if os.path.exists(path):
        os.environ["PATH"] += os.pathsep + path
        # print(f"Added to PATH: {path}")

def check_dependencies():
    # Check for openai-whisper
    try:
        import whisper
    except ImportError:
        print("Error: 'openai-whisper' python library is not installed.")
        print("Please run: pip install openai-whisper")
        return False

    # Check for ffmpeg
    if not shutil.which("ffmpeg"):
        print("Error: 'ffmpeg' is not found in your system PATH.")
        print("OpenAI Whisper requires ffmpeg to process audio.")
        if sys.platform == "win32":
            print("To install on Windows:")
            print("1. Open PowerShell as Administrator")
            print("2. Run: winget install Gyan.FFmpeg")
            print("3. Restart your terminal.")
        else:
            print("Please install ffmpeg via your package manager (e.g., apt, brew).")
        return False
        
    return True

def transcribe_file(file_path, model_name="base"):
    import whisper
    
    print(f"--- Loading Whisper model '{model_name}'... ---")
    try:
        model = whisper.load_model(model_name)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return None

    print(f"--- Transcribing '{file_path}'... (This may take a while) ---")
    try:
        result = model.transcribe(file_path)
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None
    
    text = result["text"]
    output_path = os.path.splitext(file_path)[0] + ".txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text.strip())
    
    print(f"--- Success! ---")
    print(f"Transcript saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe a local video/audio file or directory using OpenAI Whisper.")
    parser.add_argument("path", help="Path to the file or directory to transcribe")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny, base, small, medium, large). Default: base")
    
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path '{args.path}' not found.")
        sys.exit(1)

    if check_dependencies():
        if os.path.isdir(args.path):
            print(f"--- Processing Directory: {args.path} ---")
            supported_exts = ('.mp3', '.mp4', '.m4a', '.wav', '.mov', '.mkv')
            for root, dirs, files in os.walk(args.path):
                for file in files:
                    if file.lower().endswith(supported_exts):
                        full_path = os.path.join(root, file)
                        transcribe_file(full_path, args.model)
        else:
             transcribe_file(args.path, args.model)