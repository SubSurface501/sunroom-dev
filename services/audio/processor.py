import whisperx
import gc
import os
import torch

class AudioProcessor:
    def __init__(self, device="cuda" if torch.cuda.is_available() else "cpu", batch_size=16, compute_type="float16"):
        self.device = device
        self.batch_size = batch_size
        # float16 is not supported on CPU
        self.compute_type = "int8" if device == "cpu" else compute_type
        self.hf_token = os.getenv("HF_TOKEN")
        
        if not self.hf_token:
            print("Warning: HF_TOKEN not found in env. Diarization might fail if using gated models.")

    def process_audio(self, audio_file):
        """
        Transcribes and diarizes audio file.
        Returns segments with speaker labels.
        """
        print(f"Loading WhisperX model on {self.device} (compute_type={self.compute_type})...")
        
        # 1. Transcribe with WhisperX (Faster Whisper)
        # Using 'base' model for dev/testing speed, change to 'large-v2' for prod
        model_size = "base" 
        model = whisperx.load_model(model_size, self.device, compute_type=self.compute_type)
        audio = whisperx.load_audio(audio_file)
        
        result = model.transcribe(audio, batch_size=self.batch_size)
        print("Transcription complete. Aligning...")
        
        # 2. Align (Required for accurate timestamps before diarization)
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=self.device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, self.device, return_char_alignments=False)
        
        # Cleanup alignment model to free VRAM
        del model_a
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()

        # 3. Diarize
        print("Diarizing...")
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=self.hf_token, device=self.device)
        diarize_segments = diarize_model(audio)
        
        # 4. Assign Speaker Labels
        # result['segments'] is modified in-place to include 'speaker'
        result = whisperx.assign_word_speakers(diarize_segments, result)
        
        # 5. Format Output
        final_segments = []
        for seg in result["segments"]:
            speaker = seg.get("speaker", "Unknown")
            text = seg["text"].strip()
            start = seg["start"]
            end = seg["end"]
            
            final_segments.append({
                "timestamp_start": start,
                "timestamp_end": end,
                "formatted_string": f"[{speaker}]: {text}"
            })
            
        return final_segments
