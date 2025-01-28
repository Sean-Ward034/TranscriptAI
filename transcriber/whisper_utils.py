from typing import Dict, Optional, Union
import whisper
import torch

def load_whisper_model(
    model_name: str = "medium",
    device: str = "cpu",
    log_queue = None
) -> Optional[whisper.Whisper]:
    """Load and return a Whisper model."""
    try:
        if log_queue:
            log_queue.put(f"Loading Whisper model '{model_name}' on device={device}")
        return whisper.load_model(model_name, device=device)
    except Exception as e:
        if log_queue:
            log_queue.put(f"Error loading model '{model_name}': {e}")
        return None

def format_timecode(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def transcribe_audio_segment(
    model: whisper.Whisper,
    wav_path: str,
    verbose: bool = True,
    log_queue = None
) -> Dict:
    """
    Transcribe a single audio segment using Whisper.
    Returns a dictionary with:
      - "full_text": str  (the entire concatenated transcription)
      - "segments": list (each segment with timestamps, etc.)
    """
    try:
        result = model.transcribe(wav_path, verbose=verbose)
        text = result.get("text", "")
        segments = result.get("segments", [])
        
        if log_queue:
            log_queue.put(f"Transcribed segment length: {len(text)} characters.")
            
        return {
            "full_text": text,
            "segments": segments
        }
    except Exception as e:
        if log_queue:
            log_queue.put(f"Error transcribing '{wav_path}': {e}")
        return {
            "full_text": "",
            "segments": []
        }

def get_optimal_device() -> str:
    """Return 'cuda' if available, otherwise 'cpu'."""
    return "cuda" if torch.cuda.is_available() else "cpu"

def get_available_models() -> list:
    """Return list of available Whisper model sizes."""
    return ["tiny", "base", "small", "medium", "large", "large-v2"]
