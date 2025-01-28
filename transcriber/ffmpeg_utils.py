import os
import subprocess
from typing import List, Optional

def _log_subprocess_error(e: subprocess.CalledProcessError, log_queue=None) -> None:
    """Log subprocess errors with stdout/stderr details."""
    msg = f"Subprocess error: {e}"
    if log_queue:
        log_queue.put(msg)
    else:
        print(msg)
    if hasattr(e, 'stdout') and e.stdout:
        stdout_msg = f"STDOUT:\n{e.stdout.decode('utf-8', errors='replace')}"
        if log_queue:
            log_queue.put(stdout_msg)
        else:
            print(stdout_msg)
    if hasattr(e, 'stderr') and e.stderr:
        stderr_msg = f"STDERR:\n{e.stderr.decode('utf-8', errors='replace')}"
        if log_queue:
            log_queue.put(stderr_msg)
        else:
            print(stderr_msg)

def convert_to_wav_ffmpeg(
    input_file: str,
    sample_rate: int = 16000,
    channels: int = 1,
    log_queue = None
) -> Optional[str]:
    """Convert audio/video file to WAV format using FFmpeg."""
    base, ext = os.path.splitext(input_file)
    if ext.lower() == ".wav":
        if log_queue:
            log_queue.put(f"Skipping conversion. '{input_file}' is already .wav")
        return input_file

    output_wav = f"{base}.wav"
    if os.path.isfile(output_wav):
        os.remove(output_wav)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        output_wav
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if log_queue:
            log_queue.put(f"Converted '{input_file}' -> '{output_wav}'")
        return output_wav
    except subprocess.CalledProcessError as e:
        _log_subprocess_error(e, log_queue)
        return None

def get_duration_seconds(file_path: str, log_queue = None) -> float:
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(proc.stdout.strip())
        if log_queue:
            log_queue.put(f"Duration of '{file_path}' is {duration:.2f} seconds.")
        return duration
    except subprocess.CalledProcessError as e:
        _log_subprocess_error(e, log_queue)
        return 0.0
    except Exception as ex:
        if log_queue:
            log_queue.put(f"Error reading duration of '{file_path}': {ex}")
        return 0.0

def chunk_wav_file(
    file_path: str,
    chunk_length: int = 300,
    log_queue = None
) -> List[str]:
    """Split WAV file into chunks using FFmpeg segments."""
    total_duration = get_duration_seconds(file_path, log_queue=log_queue)
    if total_duration <= 0:
        if log_queue:
            log_queue.put(f"Couldn't read duration for '{file_path}', skipping split.")
        return [file_path]

    if total_duration <= chunk_length:
        if log_queue:
            log_queue.put(f"No chunking needed for '{file_path}'.")
        return [file_path]

    # Create temp directory for chunks if it doesn't exist
    dir_ = os.path.dirname(file_path)
    temp_dir = os.path.join(dir_, "temp_chunks")
    os.makedirs(temp_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(file_path))[0]
    segment_pattern = os.path.join(temp_dir, f"{base}_chunk_%03d.wav")

    # Remove old chunks if they exist
    for f in os.listdir(temp_dir):
        if f.startswith(f"{base}_chunk_") and f.endswith(".wav"):
            os.remove(os.path.join(temp_dir, f))

    cmd = [
        "ffmpeg", "-y",
        "-i", file_path,
        "-f", "segment",
        "-segment_time", str(chunk_length),
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        segment_pattern
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        _log_subprocess_error(e, log_queue)
        return [file_path]

    # Collect chunk files
    chunks = []
    for f in sorted(os.listdir(temp_dir)):
        if f.startswith(f"{base}_chunk_") and f.endswith(".wav"):
            chunks.append(os.path.join(temp_dir, f))

    if log_queue:
        log_queue.put(f"Split '{file_path}' into {len(chunks)} chunks.")
    return chunks
