import logging
import os
from collections import defaultdict # This can stay as it's a lightweight built-in

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, device="cuda", compute_type="float16"):
        # Lazy imports for heavy AI libraries
        import torch
        import torch.serialization # Import for add_safe_globals
        from omegaconf.listconfig import ListConfig # Import ListConfig
        from omegaconf.dictconfig import DictConfig # Import DictConfig
        from omegaconf.base import ContainerMetadata # Import ContainerMetadata
        from omegaconf.nodes import AnyNode # Import AnyNode
        from typing import Any # Import Any

        # Monkey-patch torch.load to default weights_only=False for PyTorch 2.6+ compatibility with legacy checkpoints
        original_load = torch.load
        def safe_load(*args, **kwargs):
            # Force weights_only=False to handle legacy checkpoints
            kwargs['weights_only'] = False 
            return original_load(*args, **kwargs)
        torch.load = safe_load

        # Fallback to CPU if CUDA is not available (for dev environments)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # float16 is not supported on CPU
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self.batch_size = 16 
        
        self.model = None
        self.diarize_model = None
        self.whisperx = None
        
        # Lazy Import
        try:
            import whisperx as wx
            import whisperx.diarize # Explicit import required
            self.whisperx = wx
        except ImportError:
            logger.warning("WhisperX not installed. Audio processing will fail if attempted.")

    def _load_transcription_model(self):
        if not self.whisperx: raise ImportError("WhisperX not installed")
        if not self.model:
            logger.info(f"Loading WhisperX on {self.device}...")
            self.model = self.whisperx.load_model(
                "large-v2", 
                self.device, 
                compute_type=self.compute_type
            )

    def _load_diarization_model(self, hf_token):
        if not self.whisperx: raise ImportError("WhisperX not installed")
        if not self.diarize_model:
            logger.info("Loading Pyannote Diarization...")
            self.diarize_model = self.whisperx.diarize.DiarizationPipeline(
                use_auth_token=hf_token,
                device=self.device
            )

    def process_audio(self, audio_path, hf_token, status_callback: callable = None):
        if not self.whisperx: 
            logger.warning("WhisperX not found. Using Mock Audio Processor (Dev Mode).")
            return self._mock_processing(audio_path)

        def _callback(status):
            if status_callback:
                status_callback(status)

        try:
            self._load_transcription_model()
            
            # 1. Transcribe
            _callback("transcribing")
            audio = self.whisperx.load_audio(audio_path)
            result = self.model.transcribe(audio, batch_size=self.batch_size)
            
            # 2. Align (Timestamps)
            # This is fast, so no dedicated status is needed
            model_a, metadata = self.whisperx.load_align_model(
                language_code=result["language"], 
                device=self.device
            )
            result = self.whisperx.align(
                result["segments"], 
                model_a, 
                metadata, 
                audio, 
                self.device, 
                return_char_alignments=False
            )
            import gc
            del model_a; gc.collect();
            import torch # Local import for torch
            torch.cuda.empty_cache()

            # 3. Diarize (Speakers)
            if hf_token:
                _callback("diarizing")
                self._load_diarization_model(hf_token)
                diarize_segments = self.diarize_model(audio)
                final_result = self.whisperx.assign_word_speakers(diarize_segments, result)
            else:
                logger.warning("HF_TOKEN missing, skipping diarization.")
                final_result = result
            
            return self._format_output(final_result["segments"])

        except Exception as e:
            logger.error(f"Audio Processing Failed: {e}")
            raise e
        finally:
            self._cleanup()

    def _mock_processing(self, audio_path):
        """Returns dummy data to allow pipeline testing without GPU/WhisperX."""
        logger.info(f"Mocking transcription for {audio_path}")
        return [
            {
                "speaker": "SPEAKER_01",
                "start": 0.0,
                "end": 5.0,
                "text": "This is a simulated transcription for development purposes.",
                "fmt_string": "[SPEAKER_01 (0.0-5.0)]: This is a simulated transcription for development purposes."
            },
            {
                "speaker": "SPEAKER_02",
                "start": 5.0,
                "end": 10.0,
                "text": "It allows us to test the ingestion pipeline without heavy GPU dependencies.",
                "fmt_string": "[SPEAKER_02 (5.0-10.0)]: It allows us to test the ingestion pipeline without heavy GPU dependencies."
            }
        ]

    def _format_output(self, segments):
        formatted = []
        for seg in segments:
            speaker = seg.get("speaker", "Unknown")
            text = seg["text"].strip()
            formatted.append({
                "speaker": speaker,
                "start": seg["start"],
                "end": seg["end"],
                "text": text,
                "fmt_string": f"[{speaker} ({seg['start']:.1f}-{seg['end']:.1f})]: {text}"
            })
        return formatted

    def _cleanup(self):
        import gc # Lazy import for gc
        import torch # Lazy import for torch
        # Explicitly delete models to free VRAM
        if self.model:
            del self.model
            self.model = None
        if self.diarize_model:
            del self.diarize_model
            self.diarize_model = None
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
