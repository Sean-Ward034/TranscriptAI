"""Audio transcription utilities using Whisper and FFmpeg."""
from .ffmpeg_utils import convert_to_wav_ffmpeg, chunk_wav_file, get_duration_seconds
from .whisper_utils import load_whisper_model, transcribe_audio_segment, get_optimal_device, get_available_models
from .transcription_worker import TranscriptionWorker
from .diarization import get_diarization_pipeline, perform_diarization, assign_speakers_to_segments, is_diarization_available

__all__ = [
    'convert_to_wav_ffmpeg',
    'chunk_wav_file',
    'get_duration_seconds',
    'load_whisper_model',
    'transcribe_audio_segment',
    'get_optimal_device',
    'get_available_models',
    'TranscriptionWorker',
    'get_diarization_pipeline',
    'perform_diarization',
    'assign_speakers_to_segments',
    'is_diarization_available',
]
