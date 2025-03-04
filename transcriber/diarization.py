import os
import sys
import numpy as np
import torch
import logging
import contextlib
import warnings
from typing import Dict, List, Tuple, Optional, Union
from queue import Queue
from io import StringIO

# Set environment variables to disable various warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow logging
os.environ["PYTHONWARNINGS"] = "ignore"    # Suppress Python warnings

# Suppress TensorBoard warnings
logging.getLogger('tensorboard').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)  # Only show errors from our logger

# Global flag to track if diarization is available
DIARIZATION_AVAILABLE = False
DIARIZATION_ERROR = None

# Create a context manager to suppress stdout, stderr and warnings
@contextlib.contextmanager
def suppress_stdout_stderr():
    """Context manager to suppress stdout and stderr."""
    # Save the original stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    # Create StringIO objects to redirect output
    new_stdout = StringIO()
    new_stderr = StringIO()
    
    # Save original warnings filter
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        
        try:
            # Redirect stdout and stderr
            sys.stdout = new_stdout
            sys.stderr = new_stderr
            yield  # Execute the code block
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # The captured output can be accessed but we're ignoring it

# Try to import pyannote.audio but handle import errors
try:
    # Suppress warnings during import
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from pyannote.audio import Pipeline
    DIARIZATION_AVAILABLE = True
except ImportError as e:
    DIARIZATION_ERROR = str(e)
    logger.warning(f"Could not import pyannote.audio: {e}")
    logger.warning("Speaker diarization will not be available.")

def is_diarization_available() -> Tuple[bool, Optional[str]]:
    """
    Check if diarization functionality is available.
    
    Returns:
        Tuple of (is_available, error_message)
    """
    return DIARIZATION_AVAILABLE, DIARIZATION_ERROR

def get_diarization_pipeline(auth_token: Optional[str] = None, device: str = None):
    """
    Load and return the pyannote.audio diarization pipeline.
    
    Args:
        auth_token: HuggingFace token for accessing the model
                   If None, will try to use the HUGGING_FACE_TOKEN env variable
        device: Device to use for inference ('cuda' or 'cpu')
               If None, will use CUDA if available
    
    Returns:
        Loaded diarization pipeline or None if not available
    """
    if not DIARIZATION_AVAILABLE:
        raise ImportError(
            f"Speaker diarization is not available: {DIARIZATION_ERROR}. "
            "Please install pyannote.audio version 3.0.0."
        )
    
    # Use environment variable if no token provided
    if auth_token is None:
        auth_token = os.environ.get("HUGGING_FACE_TOKEN")
        
    if auth_token is None:
        raise ValueError(
            "No authentication token provided for HuggingFace. "
            "Please set the HUGGING_FACE_TOKEN environment variable "
            "or provide a token directly."
        )
    
    # Determine device to use
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        # Suppress all output during pipeline creation
        with suppress_stdout_stderr():
            # Disable logging temporarily
            logging.disable(logging.CRITICAL)
            
            # Initialize the pipeline with the specified device
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization@2.1",
                use_auth_token=auth_token
            )
            
            # Move the pipeline to the specified device
            pipeline = pipeline.to(torch.device(device))
            
            # In pyannote.audio 3.0.0, the structure might be different
            # Only try to move models if the attribute exists
            if hasattr(pipeline, 'models'):
                for model in pipeline.models.values():
                    model = model.to(torch.device(device))
            
            # Re-enable logging
            logging.disable(logging.NOTSET)
        
        return pipeline
    except Exception as e:
        logger.error(f"Error loading diarization pipeline: {e}")
        raise

def prepare_audio_for_diarization(
    audio_path: str,
    log_queue: Optional[Queue] = None,
    apply_preprocessing: bool = True
) -> str:
    """
    Apply specialized preprocessing to optimize audio for diarization.
    Optimized for police call recordings with radio static and background noise.
    
    Args:
        audio_path: Path to the audio file
        log_queue: Optional queue for logging messages
        apply_preprocessing: Whether to apply preprocessing or return original path
        
    Returns:
        Path to the preprocessed audio file or original if preprocessing disabled
    """
    if not apply_preprocessing:
        return audio_path
    
    try:
        if log_queue:
            log_queue.put("Analyzing audio quality for optimal preprocessing...")
        
        # Import here to avoid circular imports
        from .audio_enhancement import analyze_audio_quality, enhance_audio_for_diarization
        
        # Analyze audio to determine optimal parameters
        noise_level, dynamic_range, recommended_prop_decrease = analyze_audio_quality(audio_path)
        
        if log_queue:
            log_queue.put(f"Audio analysis: noise level={noise_level:.6f}, dynamic range={dynamic_range:.1f}dB")
            log_queue.put(f"Applying preprocessing with noise reduction={recommended_prop_decrease:.2f}")
        
        # Apply the specialized preprocessing for diarization
        # Using the optimized settings for police calls
        enhanced_path = enhance_audio_for_diarization(
            audio_path,
            vad_threshold=0.02,  # More aggressive VAD for police calls
            normalize=True,
            noise_reduction=True,
            prop_decrease=0.9    # More aggressive noise reduction for radio static
        )
        
        if log_queue:
            log_queue.put(f"Audio preprocessing for diarization complete: {enhanced_path}")
        
        return enhanced_path
    except Exception as e:
        if log_queue:
            log_queue.put(f"Audio preprocessing failed: {str(e)}. Using original audio.")
        return audio_path

def perform_diarization(
    audio_path: str,
    pipeline,
    log_queue: Optional[Queue] = None,
    min_speakers: Optional[int] = 1,
    max_speakers: Optional[int] = 2,
    segmentation: float = 1.0,
    apply_preprocessing: bool = True
) -> Dict:
    """
    Perform speaker diarization on an audio file.
    
    Args:
        audio_path: Path to the audio file
        pipeline: Loaded diarization pipeline
        log_queue: Optional queue for logging messages
        min_speakers: Minimum number of speakers (if None, no constraint)
        max_speakers: Maximum number of speakers (if None, no constraint)
        segmentation: Segmentation parameter (higher values = more segments)
        apply_preprocessing: Whether to apply specialized preprocessing
    
    Returns:
        Dictionary with diarization results
    """
    if not DIARIZATION_AVAILABLE:
        if log_queue:
            log_queue.put("Speaker diarization is not available. Skipping.")
        return {
            "speakers": {},
            "num_speakers": 0,
            "error": DIARIZATION_ERROR
        }
        
    try:
        if log_queue:
            log_queue.put(f"Starting diarization for {audio_path}")
            # Make sure to log the device being used
            device_info = f"Using device: {pipeline.device}"
            log_queue.put(device_info)
            
            if min_speakers is not None and max_speakers is not None:
                log_queue.put(f"Speaker constraints: min={min_speakers}, max={max_speakers}")
            elif max_speakers is not None:
                log_queue.put(f"Speaker constraint: max={max_speakers}")
            
            log_queue.put(f"Segmentation parameter: {segmentation}")
        
        # Apply preprocessing if requested
        if apply_preprocessing:
            preprocessed_path = prepare_audio_for_diarization(audio_path, log_queue)
            diarization_audio_path = preprocessed_path
        else:
            diarization_audio_path = audio_path
        
        # Prepare parameters for diarization
        parameters = {}
        
        # Apply speaker constraints if provided
        if min_speakers is not None and max_speakers is not None:
            # If min and max are the same, set exact number of speakers
            if min_speakers == max_speakers:
                parameters["num_speakers"] = min_speakers
                if log_queue:
                    log_queue.put(f"Fixed number of speakers: {min_speakers}")
            else:
                parameters["min_speakers"] = min_speakers
                parameters["max_speakers"] = max_speakers
        elif max_speakers is not None:
            parameters["max_speakers"] = max_speakers
        elif min_speakers is not None:
            parameters["min_speakers"] = min_speakers
        
        # The segmentation parameter structure has changed in pyannote.audio 3.0.0
        # Let's try different parameter formats based on the version
        try:
            # Run the diarization pipeline with stdout/stderr suppressed
            with suppress_stdout_stderr():
                # Disable logging temporarily
                logging.disable(logging.CRITICAL)
                
                # First try with the segmentation parameter as in the documentation
                diarization = pipeline(diarization_audio_path, **parameters)
                
                # Re-enable logging
                logging.disable(logging.NOTSET)
        except TypeError as e:
            if "segmentation" in str(e) and log_queue:
                log_queue.put("Adjusting segmentation parameter format...")
                
            # If that fails, try without the segmentation parameter
            with suppress_stdout_stderr():
                logging.disable(logging.CRITICAL)
                diarization = pipeline(diarization_audio_path, **parameters)
                logging.disable(logging.NOTSET)
        
        # Process the results into a more usable format
        speakers = {}
        original_speaker_ids = set()
        
        # First collect all original speaker IDs
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            original_speaker_ids.add(speaker)
        
        # Create a mapping from original speaker IDs to sequential ones
        speaker_mapping = {}
        for i, original_id in enumerate(sorted(original_speaker_ids)):
            speaker_mapping[original_id] = f"SPEAKER_{i:02d}"
        
        # Now process the diarization with the new speaker IDs
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            start_time = turn.start
            end_time = turn.end
            
            # Use the mapped speaker ID
            mapped_speaker = speaker_mapping[speaker]
            
            if mapped_speaker not in speakers:
                speakers[mapped_speaker] = []
                
            speakers[mapped_speaker].append({
                "start": start_time,
                "end": end_time
            })
        
        if log_queue:
            log_queue.put(f"Diarization complete. Found {len(speakers)} speakers.")
            
        return {
            "speakers": speakers,
            "num_speakers": len(speakers),
            "speaker_mapping": speaker_mapping
        }
    except Exception as e:
        if log_queue:
            log_queue.put(f"Error during diarization: {str(e)}")
        return {
            "speakers": {},
            "num_speakers": 0,
            "error": str(e)
        }

def post_process_speaker_segments(speakers: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Apply post-processing to speaker segments to make them more coherent.
    
    Args:
        speakers: Dictionary of speaker IDs to lists of segments
    
    Returns:
        Processed dictionary with more coherent speaker segments
    """
    processed_speakers = {speaker: [] for speaker in speakers}
    
    # Merge very close segments from the same speaker
    for speaker, segments in speakers.items():
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda x: x["start"])
        
        if not sorted_segments:
            continue
            
        # Start with the first segment
        current_segment = sorted_segments[0].copy()
        
        for next_segment in sorted_segments[1:]:
            # If the gap is very small (less than 0.5 seconds), merge the segments
            if next_segment["start"] - current_segment["end"] < 0.5:
                # Extend the current segment
                current_segment["end"] = next_segment["end"]
            else:
                # Add the current segment to processed results and start a new one
                processed_speakers[speaker].append(current_segment)
                current_segment = next_segment.copy()
                
        # Add the last segment
        processed_speakers[speaker].append(current_segment)
    
    return processed_speakers

def assign_speakers_to_segments(
    segments: List[Dict],
    diarization_result: Dict
) -> List[Dict]:
    """
    Assign speaker labels to transcription segments based on diarization results.
    
    Args:
        segments: List of transcription segments with start/end times
        diarization_result: Results from the diarization process
    
    Returns:
        Updated segments with speaker information
    """
    speakers = diarization_result.get("speakers", {})
    if not speakers:
        return segments
    
    # Apply post-processing to improve speaker consistency
    processed_speakers = post_process_speaker_segments(speakers)
    
    # For each segment, find the speaker who talks the most during that segment
    for segment in segments:
        segment_start = segment["start"]
        segment_end = segment["end"]
        
        # Calculate overlap with each speaker
        max_overlap = 0
        assigned_speaker = None
        
        for speaker, turns in processed_speakers.items():
            total_overlap = 0
            
            for turn in turns:
                turn_start = turn["start"]
                turn_end = turn["end"]
                
                # Calculate overlap between segment and turn
                overlap_start = max(segment_start, turn_start)
                overlap_end = min(segment_end, turn_end)
                
                if overlap_end > overlap_start:
                    overlap_duration = overlap_end - overlap_start
                    total_overlap += overlap_duration
            
            if total_overlap > max_overlap:
                max_overlap = total_overlap
                assigned_speaker = speaker
        
        # Assign the speaker with the most overlap
        if assigned_speaker:
            segment["speaker"] = assigned_speaker
        else:
            segment["speaker"] = "UNKNOWN"
    
    # Add speaker consistency across small gaps
    # Sort segments by start time
    sorted_segments = sorted(segments, key=lambda x: x["start"])
    
    # Ensure consistent speaker assignment across small gaps
    for i in range(1, len(sorted_segments)):
        prev_segment = sorted_segments[i-1]
        curr_segment = sorted_segments[i]
        
        # If the gap is small (less than 1 second) and the previous speaker is known
        gap = curr_segment["start"] - prev_segment["end"]
        if gap < 1.0 and prev_segment.get("speaker") != "UNKNOWN":
            # If the current segment has a very low overlap (assigned to UNKNOWN or low confidence)
            if curr_segment.get("speaker") == "UNKNOWN":
                # Inherit the speaker from the previous segment
                curr_segment["speaker"] = prev_segment["speaker"]
    
    return segments
