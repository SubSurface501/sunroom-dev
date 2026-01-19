import os
import subprocess
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        pass

    def get_video_duration(self, video_path: str) -> float:
        """Returns video duration in seconds."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            return float(result.stdout)
        except Exception as e:
            logger.error(f"Failed to get duration: {e}")
            return 0.0

    def extract_frames(self, video_path: str, output_dir: str, interval: int = 30) -> List[Tuple[float, str]]:
        """
        Extracts frames at a fixed interval.
        Returns a list of (timestamp_seconds, absolute_file_path).
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Pattern: frame_%04d.jpg
        # We need to map frame number back to timestamp.
        # ffmpeg -i input.mp4 -vf fps=1/30 img%03d.jpg
        # fps=1/30 means 1 frame every 30 seconds.
        
        # We'll stick to a simple filename pattern.
        file_pattern = os.path.join(output_dir, "frame_%04d.jpg")
        
        try:
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"fps=1/{interval}",
                "-q:v", "2", # High quality jpg
                file_pattern
            ]
            
            logger.info(f"Running ffmpeg extraction: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            
            # Collect results
            frames = []
            for filename in sorted(os.listdir(output_dir)):
                if filename.startswith("frame_") and filename.endswith(".jpg"):
                    # Calculate timestamp. 
                    # Assuming ffmpeg outputs sequentially. Frame 1 is at ~0s or ~interval/2 depending on settings, 
                    # usually starts at 0 or first interval.
                    # With fps=1/30:
                    # frame_0001.jpg -> 0s-30s window (likely ~0s or ~15s?)
                    # A safer way to get timestamps is to ask ffmpeg to put timestamp in filename, 
                    # but standard fps filter doesn't do that easily.
                    # Simple heuristic: frame_number * interval. 
                    # frame_0001 -> 0 * 30 = 0s? No, usually frame 1.
                    
                    try:
                        frame_num = int(filename.split('_')[1].split('.')[0])
                        # frame 1 is usually the first extracted. 
                        # Let's approximate: timestamp = (frame_num - 1) * interval
                        timestamp = (frame_num - 1) * interval
                        
                        abs_path = os.path.abspath(os.path.join(output_dir, filename))
                        frames.append((float(timestamp), abs_path))
                    except ValueError:
                        continue
            
            return frames

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Frame extraction error: {e}")
            return []
