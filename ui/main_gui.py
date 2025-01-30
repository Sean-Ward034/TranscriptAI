import os
import queue
import tkinter as tk
from tkinter import filedialog

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

from transcriber.whisper_utils import get_available_models, get_optimal_device
from transcriber.transcription_worker import TranscriptionWorker

class ColoredProgressBar(ProgressBar):
    """Progress bar that updates its color based on percentage."""
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
    """Main application layout and logic."""
    
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=5, padding=10, **kwargs)
        
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.worker = None
        self.input_files = []
        self.output_dir = None
        
        self._init_ui()
        Clock.schedule_interval(self.update_queues, 0.5)

    def _init_ui(self):
        """Initialize all UI components."""
        # Title
        self.add_widget(Label(
            text="Audio/Video Transcription",
            font_size=24,
            size_hint=(1, 0.1)
        ))

        # File selection
        file_box = BoxLayout(orientation="horizontal", size_hint=(1, 0.1))
        self.file_label = Label(
            text="No files selected",
            halign="left",
            valign="middle"
        )
        file_box.add_widget(self.file_label)
        
        btn_pick_files = Button(text="Pick Audio/Video File(s)")
        btn_pick_files.bind(on_press=self.pick_files)
        file_box.add_widget(btn_pick_files)
        
        self.add_widget(file_box)

        # Output directory
        out_box = BoxLayout(orientation="horizontal", size_hint=(1, 0.1))
        self.out_dir_label = Label(
            text="No output directory selected",
            halign="left",
            valign="middle",
            size_hint=(0.7, 1)
        )
        out_box.add_widget(self.out_dir_label)
        
        btn_pick_outdir = Button(
            text="Pick Output Directory",
            size_hint=(0.3, 1)
        )
        btn_pick_outdir.bind(on_press=self.pick_output_directory)
        out_box.add_widget(btn_pick_outdir)
        
        self.add_widget(out_box)

        # Advanced settings
        adv_layout = GridLayout(cols=2, spacing=5, size_hint=(1, 0.3))
        
        # Model selection
        adv_layout.add_widget(Label(text="Whisper Model:", halign="right"))
        self.model_spinner = Spinner(
            text="medium",
            values=get_available_models()
        )
        adv_layout.add_widget(self.model_spinner)
        
        # Device selection
        adv_layout.add_widget(Label(text="Device:", halign="right"))
        optimal_device = get_optimal_device()
        if optimal_device == "cuda":
            self.device_spinner = Spinner(
                text="cuda",
                values=["cpu", "cuda"]
            )
        else:
            self.device_spinner = Spinner(
                text="cpu",
                values=["cpu"]
            )
        adv_layout.add_widget(self.device_spinner)
        
        # Sample rate
        adv_layout.add_widget(Label(text="Sample Rate (Hz):", halign="right"))
        self.sample_rate_input = TextInput(text="16000", multiline=False)
        adv_layout.add_widget(self.sample_rate_input)
        
        # Channels
        adv_layout.add_widget(Label(
            text="Channels (1=mono,2=stereo):",
            halign="right"
        ))
        self.channels_input = TextInput(text="1", multiline=False)
        adv_layout.add_widget(self.channels_input)
        
        # Chunking options
        adv_layout.add_widget(Label(text="Enable Chunking:", halign="right"))
        self.chunk_spinner = Spinner(
            text="Yes",
            values=["Yes", "No"]
        )
        adv_layout.add_widget(self.chunk_spinner)
        
        adv_layout.add_widget(Label(text="Chunk Length (seconds):", halign="right"))
        self.chunk_length_input = TextInput(text="300", multiline=False)
        adv_layout.add_widget(self.chunk_length_input)

        # NEW: Audio Enhancement
        adv_layout.add_widget(Label(text="Enhance Audio:", halign="right"))
        self.enhance_spinner = Spinner(
            text="No",
            values=["Yes", "No"]
        )
        adv_layout.add_widget(self.enhance_spinner)

        self.add_widget(adv_layout)

        # Control buttons
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
        self.progress_bar = ColoredProgressBar(
            value=0,
            max=100,
            size_hint=(1, 0.05)
        )
        self.add_widget(self.progress_bar)

        # Log output
        self.log_output = TextInput(
            readonly=True,
            size_hint=(1, 0.45)
        )
        scroll = ScrollView(size_hint=(1, 0.45))
        scroll.add_widget(self.log_output)
        self.add_widget(scroll)

    def pick_files(self, instance):
        """Open native file dialog for selecting input files."""
        root = tk.Tk()
        root.withdraw()
        file_paths = filedialog.askopenfilenames(
            title="Select Audio/Video Files",
            filetypes=[
                ("Media Files", "*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.mkv *.avi *.mov *.wmv *.flv"),
                ("All Files", "*.*")
            ]
        )
        root.destroy()

        if not file_paths:
            self._log("No files selected.")
            return

        self.input_files = list(file_paths)
        short_list = [os.path.basename(p) for p in self.input_files]
        self.file_label.text = f"Selected: {', '.join(short_list)}"

    def pick_output_directory(self, instance):
        """Open native dialog for selecting output directory."""
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
        """Start the transcription process."""
        if not self.input_files:
            self._log("No input files selected.")
            return

        if not self.output_dir:
            self._log("No output directory selected.")
            return

        # Parse settings
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

        try:
            chunk_len = int(self.chunk_length_input.text)
        except ValueError:
            chunk_len = 300
            self._log("Invalid chunk length, defaulting to 300 seconds.")

        # Enhance audio or not
        enhance_audio_flag = (self.enhance_spinner.text == "Yes")

        # Reset UI state
        self.log_output.text = ""
        self.progress_bar.value = 0

        self._log(f"Starting transcription on {len(self.input_files)} file(s).")
        self._log(
            f"Model={self.model_spinner.text}, "
            f"Device={self.device_spinner.text}, "
            f"SampleRate={sr_val}, "
            f"Channels={ch_val}"
        )
        self._log(
            f"Chunking: {self.chunk_spinner.text == 'Yes'} "
            f"(chunk size = {chunk_len}s)\n"
        )
        if enhance_audio_flag:
            self._log("Audio enhancement: ENABLED")
        else:
            self._log("Audio enhancement: disabled")

        self.worker = TranscriptionWorker(
            input_files=self.input_files,
            out_dir=self.output_dir,
            model_name=self.model_spinner.text,
            device=self.device_spinner.text,
            sample_rate=sr_val,
            channels=ch_val,
            chunk=(self.chunk_spinner.text == "Yes"),
            chunk_length=chunk_len,
            log_queue=self.log_queue,
            progress_queue=self.progress_queue,
            enhance_audio=enhance_audio_flag  # <-- pass it here
        )
        self.worker.start()

    def stop_transcription(self, instance):
        """Stop the worker thread if active."""
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self._log("Stop requested.")

    def quit_app(self, instance):
        """Stop worker if needed, then close the app."""
        if self.worker and self.worker.is_alive():
            self.worker.stop()
        from kivy.app import App
        App.get_running_app().stop()

    def update_queues(self, dt):
        """Check log/progress queues from the worker thread."""
        # Process logs
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self._log(msg)

        # Process progress updates
        while not self.progress_queue.empty():
            current, total = self.progress_queue.get_nowait()
            percent = int((current / total) * 100)
            self.progress_bar.value = percent

    def _log(self, message):
        """Append a message to the log output."""
        self.log_output.text += f"{message}\n"
