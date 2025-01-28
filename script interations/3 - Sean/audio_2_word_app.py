import os
import math
import subprocess
import threading
import queue

# Kivy imports
import kivy
kivy.require("2.1.0")
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView

# For native file dialogs
import tkinter as tk
from tkinter import filedialog

import whisper
import torch
from docx import Document

###############################################################################
# Debug/Configuration Constants
###############################################################################
CHUNK_AUDIO = True    # Set to False to disable chunking if you suspect that causes issues.
CHUNK_LENGTH = 300    # 5 minutes. Adjust as needed for your files.

###############################################################################
# Logging Helpers
###############################################################################

def _log(log_queue, msg):
    """Helper to push log messages into a queue (or print if None)."""
    if log_queue is not None:
        log_queue.put(msg)
    else:
        print(msg)

def _log_subprocess_error(e, log_queue=None):
    """
    Prints stdout and stderr from subprocess.CalledProcessError
    for more detailed debugging.
    """
    _log(log_queue, f"Subprocess error: {e}")
    if hasattr(e, 'stdout') and e.stdout:
        _log(log_queue, f"STDOUT:\n{e.stdout.decode('utf-8', errors='replace')}")
    if hasattr(e, 'stderr') and e.stderr:
        _log(log_queue, f"STDERR:\n{e.stderr.decode('utf-8', errors='replace')}")

###############################################################################
# FFmpeg Conversion
###############################################################################

def convert_to_wav_ffmpeg(input_file, sample_rate=16000, channels=1, log_queue=None):
    """
    Converts an audio/video file to WAV using FFmpeg and returns the WAV file path.
    """
    output_wav = os.path.splitext(input_file)[0] + ".wav"
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
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _log(log_queue, f"Converted '{input_file}' -> '{output_wav}'")
        return output_wav
    except subprocess.CalledProcessError as e:
        _log_subprocess_error(e, log_queue)
        return None

###############################################################################
# FFprobe Duration
###############################################################################

def get_duration_seconds(file_path, log_queue=None):
    """Uses ffprobe to get the duration (in seconds) of a WAV file."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(proc.stdout.strip())
        _log(log_queue, f"Duration of '{file_path}' is {duration:.2f} seconds.")
        return duration
    except subprocess.CalledProcessError as e:
        _log_subprocess_error(e, log_queue)
        return 0.0
    except Exception as ex:
        _log(log_queue, f"Error reading duration of '{file_path}': {ex}")
        return 0.0

###############################################################################
# Chunking
###############################################################################

def chunk_wav_file(file_path, chunk_length=300, log_queue=None):
    """
    Splits a WAV file into chunks of `chunk_length` seconds using FFmpeg segments.
    Returns a list of chunk file paths.
    """
    total_duration = get_duration_seconds(file_path, log_queue=log_queue)
    if total_duration <= 0:
        _log(log_queue, f"Couldn't read duration for '{file_path}', skipping split.")
        return [file_path]

    if total_duration <= chunk_length:
        # No need to chunk
        _log(log_queue, f"No chunking needed for '{file_path}'.")
        return [file_path]

    base = os.path.splitext(file_path)[0]
    segment_pattern = base + "_chunk_%03d.wav"

    # Remove old chunks if they exist
    dir_ = os.path.dirname(file_path)
    fname_ = os.path.basename(base)
    for f in os.listdir(dir_):
        if f.startswith(fname_ + "_chunk_") and f.endswith(".wav"):
            os.remove(os.path.join(dir_, f))

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
    for f in sorted(os.listdir(dir_)):
        if f.startswith(fname_ + "_chunk_") and f.endswith(".wav"):
            chunks.append(os.path.join(dir_, f))

    _log(log_queue, f"Split '{file_path}' into {len(chunks)} chunks.")
    return chunks

###############################################################################
# Transcription
###############################################################################

def transcribe_chunked(
    wav_file, model_name="medium", device="cpu", stop_event=None, log_queue=None
):
    """
    If CHUNK_AUDIO=True, split the file into ~5-min chunks, transcribe each chunk
    (with verbose logging), and return the combined text. Otherwise, transcribe
    the entire wav_file in one go.
    """
    # Optional chunking
    if CHUNK_AUDIO:
        chunk_files = chunk_wav_file(wav_file, chunk_length=CHUNK_LENGTH, log_queue=log_queue)
    else:
        chunk_files = [wav_file]

    # Load model once
    try:
        _log(log_queue, f"Loading Whisper model '{model_name}' on device={device} with verbose=True ...")
        model = whisper.load_model(model_name, device=device)
    except Exception as e:
        _log(log_queue, f"Error loading model '{model_name}': {e}")
        return ""

    combined_text = ""

    for i, chunk_path in enumerate(chunk_files, start=1):
        if stop_event and stop_event.is_set():
            _log(log_queue, "Stop event triggered. Halting transcription.")
            break

        _log(log_queue, f"Transcribing chunk {i}/{len(chunk_files)}: {chunk_path}")
        try:
            # Setting verbose=True for more debug info in the console
            result = model.transcribe(chunk_path, verbose=True)
            chunk_text = result.get("text", "")
            _log(log_queue, f"Chunk {i}/{len(chunk_files)} length: {len(chunk_text)} characters.")
            combined_text += chunk_text + "\n"
        except Exception as e:
            _log(log_queue, f"Error transcribing '{chunk_path}': {e}")

    _log(log_queue, f"Total combined transcript length: {len(combined_text)} characters.")
    return combined_text

def process_file(
    in_file, out_dir, model_name="medium", device="cpu",
    sample_rate=16000, channels=1,
    stop_event=None, log_queue=None
):
    """
    Converts `in_file` to WAV, transcribes (optionally chunked), and saves `.docx` in `out_dir`.
    """
    _log(log_queue, f"Converting '{in_file}' to WAV...")
    wav_file = convert_to_wav_ffmpeg(in_file, sample_rate, channels, log_queue=log_queue)
    if not wav_file:
        _log(log_queue, f"WAV conversion failed for '{in_file}'. Skipping.")
        return None

    text = transcribe_chunked(wav_file, model_name, device, stop_event, log_queue)
    doc = Document()
    doc.add_paragraph(text)

    base = os.path.splitext(os.path.basename(in_file))[0]
    out_path = os.path.join(out_dir, base + ".docx")
    doc.save(out_path)
    _log(log_queue, f"Saved transcript to '{out_path}'")
    return out_path

###############################################################################
# Background Worker
###############################################################################

class TranscriptionWorker(threading.Thread):
    """
    Processes multiple files in a background thread.
    """
    def __init__(
        self, input_files, out_dir, model_name="medium", device="cpu",
        sample_rate=16000, channels=1,
        log_queue=None, progress_queue=None
    ):
        super().__init__()
        self.input_files = input_files
        self.out_dir = out_dir
        self.model_name = model_name
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels

        self.log_queue = log_queue
        self.progress_queue = progress_queue

        self.stop_event = threading.Event()

    def run(self):
        total = len(self.input_files)
        if total == 0:
            _log(self.log_queue, "No files to process.")
            return

        for idx, f in enumerate(self.input_files, start=1):
            if self.stop_event.is_set():
                _log(self.log_queue, "Stop requested. Stopping worker.")
                break

            _log(self.log_queue, f"Processing file {idx}/{total}: '{f}'")
            process_file(
                f, self.out_dir, self.model_name, self.device,
                self.sample_rate, self.channels,
                stop_event=self.stop_event,
                log_queue=self.log_queue
            )

            if self.progress_queue:
                self.progress_queue.put((idx, total))

        _log(self.log_queue, "Transcription worker finished.")

    def stop(self):
        """Signal the thread to stop gracefully."""
        self.stop_event.set()

###############################################################################
# GUI
###############################################################################

class ColoredProgressBar(ProgressBar):
    """
    Progress bar that updates its color based on percentage:
      0–33% (red), 34–66% (yellow), 67–93% (light green), 94–100% (dark green).
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(value=self.on_value)

    def on_value(self, instance, val):
        pct = (val / self.max) * 100
        if pct <= 33:
            self.color = (1, 0, 0, 1)         # red
        elif pct <= 66:
            self.color = (1, 1, 0, 1)         # yellow
        elif pct <= 93:
            self.color = (0.5, 1, 0.5, 1)     # light green
        else:
            self.color = (0, 0.6, 0, 1)       # dark green

class MainGUI(BoxLayout):
    """
    Main Kivy layout with:
      - Buttons to pick files (native Windows Explorer), pick output dir
      - Model/device selection
      - Start, Stop, Quit
      - Progress bar & log
    """
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=5, padding=10, **kwargs)

        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.worker = None
        self.input_files = []

        # Title
        self.add_widget(Label(text="Audio/Video Transcription (Debug Mode)", font_size=24, size_hint=(1, 0.1)))

        # File selection row
        file_box = BoxLayout(orientation="horizontal", size_hint=(1, 0.1))
        self.file_label = Label(text="No files selected", halign="left", valign="middle")
        file_box.add_widget(self.file_label)

        btn_pick_files = Button(text="Pick Audio/Video File(s)")
        btn_pick_files.bind(on_press=self.pick_files)
        file_box.add_widget(btn_pick_files)

        self.add_widget(file_box)

        # Output directory row
        out_box = BoxLayout(orientation="horizontal", size_hint=(1, 0.1))
        self.out_dir_label = Label(text="No output directory selected", halign="left", valign="middle", size_hint=(0.7,1))
        out_box.add_widget(self.out_dir_label)

        btn_pick_outdir = Button(text="Pick Output Directory", size_hint=(0.3,1))
        btn_pick_outdir.bind(on_press=self.pick_output_directory)
        out_box.add_widget(btn_pick_outdir)

        self.add_widget(out_box)

        # Advanced settings
        adv_layout = GridLayout(cols=2, spacing=5, size_hint=(1, 0.3))

        # Model
        adv_layout.add_widget(Label(text="Whisper Model:", halign="right"))
        self.model_spinner = Spinner(
            text="medium",
            values=["tiny", "base", "small", "medium", "large", "large-v2"]
        )
        adv_layout.add_widget(self.model_spinner)

        # Device
        adv_layout.add_widget(Label(text="Device:", halign="right"))
        if torch.cuda.is_available():
            self.device_spinner = Spinner(text="cuda", values=["cpu", "cuda"])
        else:
            self.device_spinner = Spinner(text="cpu", values=["cpu"])
        adv_layout.add_widget(self.device_spinner)

        # Sample rate
        adv_layout.add_widget(Label(text="Sample Rate (Hz):", halign="right"))
        self.sample_rate_input = TextInput(text="16000", multiline=False)
        adv_layout.add_widget(self.sample_rate_input)

        # Channels
        adv_layout.add_widget(Label(text="Channels (1=mono,2=stereo):", halign="right"))
        self.channels_input = TextInput(text="1", multiline=False)
        adv_layout.add_widget(self.channels_input)

        self.add_widget(adv_layout)

        # Buttons row
        btn_row = BoxLayout(orientation="horizontal", spacing=5, size_hint=(1, 0.1))
        self.start_btn = Button(text="Start")
        self.start_btn.bind(on_press=self.start_transcription)
        btn_row.add_widget(self.start_btn)

        self.stop_btn = Button(text="Stop")
        self.stop_btn.bind(on_press=self.stop_transcription)
        btn_row.add_widget(self.stop_btn)

        self.quit_btn = Button(text="Quit")
        self.quit_btn.bind(on_press=self.quit_app)
        btn_row.add_widget(self.quit_btn)

        self.add_widget(btn_row)

        # Progress bar
        self.progress_bar = ColoredProgressBar(value=0, max=100, size_hint=(1,0.05))
        self.add_widget(self.progress_bar)

        # Log output
        self.log_output = TextInput(readonly=True, size_hint=(1, 0.45))
        scroll = ScrollView(size_hint=(1, 0.45))
        scroll.add_widget(self.log_output)
        self.add_widget(scroll)

        # Schedule a callback to update logs/progress
        Clock.schedule_interval(self.update_queues, 0.5)

        # Keep track of chosen output directory
        self.output_dir = None

    def pick_files(self, instance):
        """
        Opens a native Windows file dialog (via Tkinter) to select multiple files.
        """
        root = tk.Tk()
        root.withdraw()
        # let user pick multiple
        file_paths = filedialog.askopenfilenames(
            title="Select Audio/Video Files",
            filetypes=[("Media Files", "*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.mkv *.avi *.mov *.wmv *.flv"),
                       ("All Files", "*.*")]
        )
        root.destroy()

        if not file_paths:
            self._log("No files selected.")
            return

        self.input_files = list(file_paths)
        # Update label
        short_list = [os.path.basename(p) for p in self.input_files]
        self.file_label.text = f"Selected: {', '.join(short_list)}"

    def pick_output_directory(self, instance):
        """
        Opens a native Windows file dialog (via Tkinter) to pick a folder.
        """
        root = tk.Tk()
        root.withdraw()
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        root.destroy()

        if not dir_path:
            self._log("No output directory selected.")
            return

        self.output_dir = dir_path
        self.out_dir_label.text = f"Output: {dir_path}"

    def start_transcription(self, instance):
        """
        Start the background worker to transcribe selected files.
        """
        if not self.input_files:
            self._log("No input files selected.")
            return

        if not self.output_dir:
            self._log("No output directory selected.")
            return

        # Parse advanced settings
        model_name = self.model_spinner.text
        device_name = self.device_spinner.text

        try:
            sr_val = int(self.sample_rate_input.text)
        except ValueError:
            sr_val = 16000
            self._log("Invalid sample rate, defaulting to 16000.")

        try:
            ch_val = int(self.channels_input.text)
        except ValueError:
            ch_val = 1
            self._log("Invalid channels, defaulting to 1 (mono).")

        # Reset log & progress
        self.log_output.text = ""
        self.progress_bar.value = 0

        self._log(f"Starting transcription on {len(self.input_files)} file(s).")
        self._log(f"Model={model_name}, Device={device_name}, SampleRate={sr_val}, Channels={ch_val}")
        self._log(f"Chunking: {CHUNK_AUDIO} (chunk size = {CHUNK_LENGTH}s)\n")

        self.worker = TranscriptionWorker(
            input_files=self.input_files,
            out_dir=self.output_dir,
            model_name=model_name,
            device=device_name,
            sample_rate=sr_val,
            channels=ch_val,
            log_queue=self.log_queue,
            progress_queue=self.progress_queue
        )
        self.worker.start()

    def stop_transcription(self, instance):
        """
        Stop the worker thread if active.
        """
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self._log("Stop requested.")

    def quit_app(self, instance):
        """
        Stop worker if needed, then close the app.
        """
        if self.worker and self.worker.is_alive():
            self.worker.stop()
        App.get_running_app().stop()

    def update_queues(self, dt):
        """
        Check log/progress queues from the worker thread.
        """
        # Logs
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self._log(msg)

        # Progress
        while not self.progress_queue.empty():
            current, total = self.progress_queue.get_nowait()
            percent = int((current / total) * 100)
            self.progress_bar.value = percent

    def _log(self, message):
        """Append a message to the log output."""
        self.log_output.text += f"{message}\n"


class Audio2WordKivyApp(App):
    def build(self):
        self.title = "Audio/Video Transcription (Kivy + Debug Logging)"
        return MainGUI()

def main():
    Audio2WordKivyApp().run()

if __name__ == "__main__":
    main()
