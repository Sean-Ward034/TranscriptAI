# file: transcriber/audio_enhancement.py
import os
import librosa
import soundfile as sf
import noisereduce as nr
import numpy as np

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
