# Audio2Word Command Line Interface (CLI) Usage Guide

This guide explains how to use the CLI mode for the Audio2Word transcription application. The CLI mode provides full access to the advanced features available in the GUI.

## Invoking CLI Mode

To run the application in CLI mode, include the `--mode CLI` flag when executing `main.py`. For example:

  python main.py --mode CLI --input-files "path/to/file1.mp3" "path/to/file2.mp4" --output-dir "path/to/output"

## Available Flags

- **--mode**  
  Specifies the mode in which to run the application.  
  **Values:**  
    - `GUI` (default) – Launches the graphical interface.  
    - `CLI` – Runs the command line interface.

- **--input-files**  
  One or more paths to input audio/video files.  
  **Example:**  
    --input-files "audio1.mp3" "video1.mp4"  
  **Note:** Required in CLI mode.

- **--output-dir**  
  Directory path where the transcript files (.docx) will be saved.  
  **Example:**  
    --output-dir "C:\Transcripts" or --output-dir "/home/user/transcripts"  
  **Note:** Required in CLI mode.

- **--model**  
  The Whisper model to use for transcription.  
  **Options:** tiny, base, small, medium, large, large-v2  
  **Default:** medium

- **--device**  
  The computation device to use.  
  **Options:** cpu or cuda  
  If not specified, the application automatically selects the optimal device.

- **--sample-rate**  
  The sample rate (in Hz) for audio processing.  
  **Default:** 16000

- **--channels**  
  Number of audio channels.  
  **Options:** 1 (mono) or 2 (stereo)  
  **Default:** 1

- **--chunk**  
  Flag to enable chunking for long files.  
  **Options:** Yes or No  
  **Default:** Yes

- **--chunk-length**  
  The length (in seconds) of each audio chunk when chunking is enabled.  
  **Default:** 300

- **--enhance**  
  Flag to enable audio enhancement.  
  **Options:** Yes or No  
  **Default:** No

- **--diarization**  
  Flag to enable speaker diarization.  
  **Options:** Yes or No  
  **Default:** No

- **--huggingface-token**  
  HuggingFace token for accessing diarization models.  
  **Note:** Required if diarization is enabled, unless the HUGGING_FACE_TOKEN environment variable is set.

- **--min-speakers**  
  Minimum number of speakers to detect in diarization.  
  **Range:** 1-10  
  **Default:** 1

- **--max-speakers**  
  Maximum number of speakers to detect in diarization.  
  **Range:** 1-10  
  **Default:** 2

- **--segmentation**  
  Segmentation parameter for diarization.  
  **Range:** 0.1-5.0  
  **Default:** 1.0  
  Lower values merge segments, higher values create more segments.

## Example Commands

### Example 1: Basic Transcription
Run the transcription on two files using default settings:
  
  python main.py --mode CLI --input-files "audio1.mp3" "video1.mp4" --output-dir "./transcripts"

### Example 2: Custom Transcription Settings
Run with custom model, device, enhanced audio, and speaker diarization enabled:
  
  python main.py --mode CLI --input-files "audio1.mp3" --output-dir "./transcripts" --model small --device cuda --sample-rate 22050 --channels 2 --chunk Yes --chunk-length 180 --enhance Yes --diarization Yes --huggingface-token "YOUR_TOKEN_HERE" --min-speakers 1 --max-speakers 2 --segmentation 1.0

### Example 3: Optimized for Interview (2 speakers)
Run with settings optimized for a two-person interview:

  python main.py --mode CLI --input-files "interview.mp3" --output-dir "./transcripts" --diarization Yes --huggingface-token "YOUR_TOKEN_HERE" --min-speakers 1 --max-speakers 2 --segmentation 1.0

### Example 4: Optimized for Single Speaker
Run with settings optimized for a single speaker (lecture, monologue):

  python main.py --mode CLI --input-files "lecture.mp3" --output-dir "./transcripts" --diarization Yes --huggingface-token "YOUR_TOKEN_HERE" --min-speakers 1 --max-speakers 1 --segmentation 0.5

### Example 5: Optimized for Group Discussion
Run with settings optimized for a group discussion or meeting:

  python main.py --mode CLI --input-files "meeting.mp3" --output-dir "./transcripts" --diarization Yes --huggingface-token "YOUR_TOKEN_HERE" --min-speakers 2 --max-speakers 5 --segmentation 1.5

## Diarization Settings Guide

The diarization feature identifies different speakers in the audio. The settings can be tuned for different scenarios:

- **min-speakers and max-speakers**:
  - For interviews or podcasts with 2 speakers: min=1, max=2
  - For single speaker recordings: min=1, max=1
  - For group discussions or meetings: min=2, max=3-10 (depending on number of participants)

- **segmentation**:
  - Lower values (0.1-0.5): Fewer segments, may merge different speakers, faster processing
  - Default (1.0): Balanced segmentation
  - Higher values (1.5-5.0): More segments, better speaker separation, slower processing

## Additional Notes

- **FFmpeg Requirement:**  
  Ensure that FFmpeg (and ffprobe) is installed and accessible from your system PATH.

- **Platform Compatibility:**  
  This CLI mode is compatible with both Windows and Linux operating systems.

- **Logging and Progress:**  
  During execution, progress updates and log messages are printed to the console.

- **HuggingFace Token:**  
  To use speaker diarization, you need a HuggingFace token with access to the pyannote/speaker-diarization model.
  You can set it using the --huggingface-token parameter or by setting the HUGGING_FACE_TOKEN environment variable.

This CLI integration retains all the features provided in the GUI while offering a flexible command line alternative.
