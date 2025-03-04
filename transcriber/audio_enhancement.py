# file: transcriber/audio_enhancement.py
import os
import librosa
import soundfile as sf
import noisereduce as nr
import numpy as np
from typing import Tuple, Optional

def enhance_audio(
    input_path: str,
    output_path: str = None,
    prop_decrease: float = 1.0,
    sr_override: int = None
) -> str:
    """
    Load an audio file, apply noise reduction, and save the enhanced version.
    :param input_path: Path to the input WAV file.
    :param output_path: (Optional) path to save the enhanced file.
    :param prop_decrease: How aggressive the noise reduction is (default=1.0).
    :param sr_override: If provided, resample the audio to this sample rate before enhancement.
    :return: Path to the enhanced output WAV.
    """

    # 1) Load the audio (mono to simplify noise reduction)
    signal, sr = librosa.load(input_path, sr=sr_override, mono=True)

    # 2) Apply spectral gating noise reduction
    enhanced = nr.reduce_noise(y=signal, sr=sr, prop_decrease=prop_decrease)

    # 3) Determine output file
    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_enhanced.wav"

    # 4) Write to disk
    sf.write(output_path, enhanced, sr)

    return output_path

def enhance_audio_for_diarization(
    input_path: str,
    output_path: str = None,
    sr_override: int = None,
    vad_threshold: float = 0.02,  # Increased from 0.01 to 0.02 for more aggressive VAD
    normalize: bool = True,
    noise_reduction: bool = True,
    prop_decrease: float = 0.9    # Increased from 0.75 to 0.9 for more aggressive noise reduction
) -> str:
    """
    Specialized audio enhancement for diarization with Voice Activity Detection,
    audio normalization, and targeted noise reduction.
    Optimized for police call recordings with radio static and background noise.
    
    Args:
        input_path: Path to the input WAV file
        output_path: Optional path to save the enhanced file
        sr_override: If provided, resample the audio to this sample rate
        vad_threshold: Energy threshold for Voice Activity Detection (0-1)
        normalize: Whether to normalize audio levels
        noise_reduction: Whether to apply noise reduction
        prop_decrease: How aggressive the noise reduction is (default=0.9)
        
    Returns:
        Path to the enhanced output WAV
    """
    # 1) Load the audio (mono to simplify processing)
    signal, sr = librosa.load(input_path, sr=sr_override, mono=True)
    
    # 2) Apply Voice Activity Detection to focus on speech segments
    if vad_threshold > 0:
        # Get non-silent intervals using librosa's VAD
        intervals = librosa.effects.split(
            signal, 
            top_db=25,             # Increased from 20 to 25 dB for more aggressive VAD
            frame_length=1024,    
            hop_length=256
        )
        
        # Concatenate the speech segments
        speech_segments = []
        for start, end in intervals:
            speech_segments.append(signal[start:end])
        
        # If we found speech segments, use them; otherwise keep original
        if speech_segments:
            # Create a new signal containing only speech
            speech_signal = np.concatenate(speech_segments)
            
            # If the speech is too short, keep original
            if len(speech_signal) > 0.5 * len(signal):
                signal = speech_signal
    
    # 3) Normalize audio levels
    if normalize:
        # Peak normalization to -3dB
        peak = np.max(np.abs(signal))
        if peak > 0:
            norm_factor = 0.7079 / peak  # -3dB = 10^(-3/20) ≈ 0.7079
            signal = signal * norm_factor
    
    # 4) Apply targeted noise reduction if enabled
    if noise_reduction:
        # More aggressive settings for police call recordings
        signal = nr.reduce_noise(
            y=signal, 
            sr=sr,
            prop_decrease=prop_decrease,  # 0.9 for aggressive noise reduction
            n_fft=1024,
            win_length=1024,
            freq_mask_smooth_hz=300,     # Reduced from 500 to focus more on voice frequencies
            n_std_thresh_stationary=1.2, # Increased to better handle radio static
            stationary=False
        )
    
    # 5) Determine output file
    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_diar_enhanced.wav"

    # 6) Write to disk
    sf.write(output_path, signal, sr)

    return output_path

def analyze_audio_quality(input_path: str, sr_override: int = None) -> Tuple[float, float, float]:
    """
    Analyze audio quality to determine optimal preprocessing parameters.
    Optimized for detecting noise levels in police call recordings.
    
    Args:
        input_path: Path to the input WAV file
        sr_override: If provided, resample the audio to this sample rate
        
    Returns:
        Tuple of (noise_level, dynamic_range, recommended_prop_decrease)
    """
    # Load the audio
    signal, sr = librosa.load(input_path, sr=sr_override, mono=True)
    
    # Calculate noise level from silent sections
    intervals = librosa.effects.split(
        signal, 
        top_db=30,             # Higher threshold to really find silence
        frame_length=1024,    
        hop_length=256
    )
    
    # Extract silent parts (inverse of the intervals)
    silent_segments = []
    last_end = 0
    for start, end in intervals:
        if start > last_end:
            silent_segments.append(signal[last_end:start])
        last_end = end
    if last_end < len(signal):
        silent_segments.append(signal[last_end:])
    
    # Calculate noise level from silent parts
    noise_level = 0
    if silent_segments:
        silent_signal = np.concatenate(silent_segments)
        if len(silent_signal) > 0:
            noise_level = np.sqrt(np.mean(silent_signal**2))  # RMS of silent parts
    
    # Calculate dynamic range
    if np.max(np.abs(signal)) > 0:
        dynamic_range = 20 * np.log10(np.max(np.abs(signal)) / 
                                     (noise_level if noise_level > 0 else 1e-10))
    else:
        dynamic_range = 0
    
    # For police calls, use more aggressive noise reduction by default
    if dynamic_range > 40:  # High quality audio
        recommended_prop_decrease = 0.8  # More aggressive than before (was 0.5)
    elif dynamic_range > 20:  # Medium quality
        recommended_prop_decrease = 0.9  # More aggressive than before (was 0.75)
    else:  # Low quality
        recommended_prop_decrease = 1.0  # Maximum noise reduction
        
    return noise_level, dynamic_range, recommended_prop_decrease
