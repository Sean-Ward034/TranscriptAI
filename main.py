#!/usr/bin/env python3
import os
import sys
import argparse
import time
import warnings
import logging
from queue import Queue
from transcriber.whisper_utils import get_optimal_device
from transcriber.transcription_worker import TranscriptionWorker

# Suppress all warnings globally
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow logging
os.environ["PYTHONWARNINGS"] = "ignore"    # Suppress Python warnings

# Disable most logging
logging.basicConfig(level=logging.ERROR)
for logger_name in ['tensorflow', 'tensorboard', 'matplotlib', 'urllib3', 'pyannote', 'pytorch_metric_learning']:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

def run_cli(args):
    # Setup queues for logs and progress updates
    log_queue = Queue()
    progress_queue = Queue()

    # Verify required CLI arguments
    if not args.input_files or not args.output_dir:
        print("Error: CLI mode requires --input-files and --output-dir.")
        return

    # Determine device if not provided
    if args.device is None:
        args.device = get_optimal_device()

    # Convert flag strings to booleans
    chunk_bool = True if args.chunk == "Yes" else False
    enhance_bool = True if args.enhance == "Yes" else False
    diarization_bool = True if args.diarization == "Yes" else False

    # Print configuration for confirmation
    print("Starting CLI transcription with the following options:")
    print(f" Input files: {args.input_files}")
    print(f" Output directory: {args.output_dir}")
    print(f" Model: {args.model}")
    print(f" Device: {args.device}")
    print(f" Sample rate: {args.sample_rate}")
    print(f" Channels: {args.channels}")
    print(f" Chunking enabled: {chunk_bool}")
    print(f" Chunk length: {args.chunk_length}")
    print(f" Audio enhancement: {enhance_bool}")
    print(f" Speaker diarization: {diarization_bool}")
    if diarization_bool:
        print(f" Min speakers: {args.min_speakers}")
        print(f" Max speakers: {args.max_speakers}")
        print(f" Segmentation: {args.segmentation}")
    print("------------------------------------------------------")

    # Initialize and start the transcription worker
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        
        worker = TranscriptionWorker(
            input_files=args.input_files,
            out_dir=args.output_dir,
            model_name=args.model,
            device=args.device,
            sample_rate=args.sample_rate,
            channels=args.channels,
            chunk=chunk_bool,
            chunk_length=args.chunk_length,
            log_queue=log_queue,
            progress_queue=progress_queue,
            enhance_audio=enhance_bool,
            enable_diarization=diarization_bool,
            huggingface_token=args.huggingface_token,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
            segmentation=args.segmentation
        )
        worker.start()

        # Poll queues until transcription completes
        while worker.is_alive():
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("Termination requested. Stopping transcription.")
                worker.stop()
                break
            while not log_queue.empty():
                print(log_queue.get_nowait())
            while not progress_queue.empty():
                current, total = progress_queue.get_nowait()
                percent = int((current / total) * 100)
                print(f"Progress: {percent}%")

    # Flush any remaining log messages
    while not log_queue.empty():
        print(log_queue.get_nowait())
    print("Transcription completed.")

def main():
    # Suppress warnings globally
    warnings.filterwarnings("ignore")
    
    # Check for CLI mode in arguments
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="Audio2Word Transcription Application")
        parser.add_argument("--mode", default="GUI", help="Mode to run: GUI (default) or CLI")
        parser.add_argument("--input-files", nargs="*", help="Path(s) to audio/video input files (required for CLI mode)")
        parser.add_argument("--output-dir", help="Directory to save transcript files (required for CLI mode)")
        parser.add_argument("--model", default="medium", help="Whisper model to use (tiny, base, small, medium, large, large-v2)")
        parser.add_argument("--device", default=None, help="Device to use (cpu or cuda); if not provided, the optimal device is chosen")
        parser.add_argument("--sample-rate", type=int, default=16000, help="Sample rate for audio processing")
        parser.add_argument("--channels", type=int, default=1, help="Number of audio channels (1 for mono, 2 for stereo)")
        parser.add_argument("--chunk", choices=["Yes", "No"], default="Yes", help="Enable chunking for long files")
        parser.add_argument("--chunk-length", type=int, default=300, help="Length (in seconds) of each audio chunk")
        parser.add_argument("--enhance", choices=["Yes", "No"], default="No", help="Enable audio enhancement (Yes/No)")
        parser.add_argument("--diarization", choices=["Yes", "No"], default="No", help="Enable speaker diarization (Yes/No)")
        parser.add_argument("--huggingface-token", help="HuggingFace token for accessing diarization models")
        parser.add_argument("--min-speakers", type=int, default=1, help="Minimum number of speakers for diarization")
        parser.add_argument("--max-speakers", type=int, default=2, help="Maximum number of speakers for diarization")
        parser.add_argument("--segmentation", type=float, default=1.0, help="Segmentation parameter (higher = more segments)")
        
        args = parser.parse_args()

        # Run CLI mode if specified
        if args.mode.upper() == "CLI":
            run_cli(args)
            return
    
    # If not CLI mode, start GUI
    from qt_gui.app import run as run_qt_app
    run_qt_app()

if __name__ == "__main__":
    main()
