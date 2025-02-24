from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QProgressBar,
    QTextEdit, QFileDialog
)
from PyQt6.QtCore import QTimer
import os
from queue import Queue
from transcriber.whisper_utils import get_available_models, get_optimal_device
from transcriber.transcription_worker import TranscriptionWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio/Video Transcription")
        
        # Initialize queues and worker
        self.log_queue = Queue()
        self.progress_queue = Queue()
        self.worker = None
        self.input_files = []
        self.output_dir = ""
        
        # Setup UI
        self._init_ui()
        
        # Setup timer for queue processing
        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_queues)
        self.timer.start()

    def _init_ui(self):
        # Create central widget and main layout
        self.central = QWidget()
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)
        
        # Title
        self.title_label = QLabel("Audio/Video Transcription")
        layout.addWidget(self.title_label)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No files selected")
        file_layout.addWidget(self.file_label)
        self.pick_files_btn = QPushButton("Pick Audio/Video File(s)")
        self.pick_files_btn.clicked.connect(self.pick_files)
        file_layout.addWidget(self.pick_files_btn)
        layout.addLayout(file_layout)
        
        # Output directory
        out_layout = QHBoxLayout()
        self.out_dir_label = QLabel("No output directory selected")
        out_layout.addWidget(self.out_dir_label)
        self.pick_outdir_btn = QPushButton("Pick Output Directory")
        self.pick_outdir_btn.clicked.connect(self.pick_output_directory)
        out_layout.addWidget(self.pick_outdir_btn)
        layout.addLayout(out_layout)
        
        # Advanced settings
        grid = QGridLayout()
        
        # Model selection
        grid.addWidget(QLabel("Whisper Model:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(get_available_models())
        self.model_combo.setCurrentText("medium")
        grid.addWidget(self.model_combo, 0, 1)
        
        # Device selection
        grid.addWidget(QLabel("Device:"), 1, 0)
        self.device_combo = QComboBox()
        optimal_device = get_optimal_device()
        if optimal_device == "cuda":
            self.device_combo.addItems(["cpu", "cuda"])
            self.device_combo.setCurrentText("cuda")
        else:
            self.device_combo.addItems(["cpu"])
        grid.addWidget(self.device_combo, 1, 1)
        
        # Sample rate
        grid.addWidget(QLabel("Sample Rate (Hz):"), 2, 0)
        self.sample_rate_edit = QLineEdit("16000")
        grid.addWidget(self.sample_rate_edit, 2, 1)
        
        # Channels
        grid.addWidget(QLabel("Channels (1=mono,2=stereo):"), 3, 0)
        self.channels_edit = QLineEdit("1")
        grid.addWidget(self.channels_edit, 3, 1)
        
        # Chunking
        grid.addWidget(QLabel("Enable Chunking:"), 4, 0)
        self.chunk_combo = QComboBox()
        self.chunk_combo.addItems(["Yes", "No"])
        grid.addWidget(self.chunk_combo, 4, 1)
        
        # Chunk length
        grid.addWidget(QLabel("Chunk Length (seconds):"), 5, 0)
        self.chunk_length_edit = QLineEdit("300")
        grid.addWidget(self.chunk_length_edit, 5, 1)
        
        # Audio enhancement
        grid.addWidget(QLabel("Enhance Audio:"), 6, 0)
        self.enhance_combo = QComboBox()
        self.enhance_combo.addItems(["No", "Yes"])
        grid.addWidget(self.enhance_combo, 6, 1)
        
        layout.addLayout(grid)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_transcription)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_transcription)
        button_layout.addWidget(self.stop_btn)
        
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.close)
        button_layout.addWidget(self.quit_btn)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio/Video Files",
            "",
            "Media Files (*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.mkv *.avi *.mov *.wmv *.flv);;All Files (*.*)"
        )
        
        if files:
            self.input_files = files
            short_list = [os.path.basename(p) for p in self.input_files]
            self.file_label.setText(f"Selected: {', '.join(short_list)}")
            self._log("Selected files: " + ", ".join(short_list))

    def pick_output_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if dir_path:
            self.output_dir = dir_path
            self.out_dir_label.setText(f"Output: {dir_path}")
            self._log(f"Selected output directory: {dir_path}")

    def start_transcription(self):
        if not self.input_files:
            self._log("No input files selected.")
            return
            
        if not self.output_dir:
            self._log("No output directory selected.")
            return
            
        try:
            sr_val = int(self.sample_rate_edit.text())
        except ValueError:
            sr_val = 16000
            self._log("Invalid sample rate, defaulting to 16000.")
            
        try:
            ch_val = int(self.channels_edit.text())
        except ValueError:
            ch_val = 1
            self._log("Invalid channels, defaulting to 1.")
            
        try:
            chunk_len = int(self.chunk_length_edit.text())
        except ValueError:
            chunk_len = 300
            self._log("Invalid chunk length, defaulting to 300 seconds.")
            
        # Reset UI state
        self.log_output.clear()
        self.progress_bar.setValue(0)
        
        self._log(f"Starting transcription on {len(self.input_files)} file(s).")
        self._log(
            f"Model={self.model_combo.currentText()}, "
            f"Device={self.device_combo.currentText()}, "
            f"SampleRate={sr_val}, "
            f"Channels={ch_val}"
        )
        
        # Initialize worker
        self.worker = TranscriptionWorker(
            input_files=self.input_files,
            out_dir=self.output_dir,
            model_name=self.model_combo.currentText(),
            device=self.device_combo.currentText(),
            sample_rate=sr_val,
            channels=ch_val,
            chunk=(self.chunk_combo.currentText() == "Yes"),
            chunk_length=chunk_len,
            log_queue=self.log_queue,
            progress_queue=self.progress_queue,
            enhance_audio=(self.enhance_combo.currentText() == "Yes")
        )
        self.worker.start()

    def stop_transcription(self):
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self._log("Stop requested.")

    def update_queues(self):
        # Process logs
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self._log(msg)
            
        # Process progress updates
        while not self.progress_queue.empty():
            current, total = self.progress_queue.get_nowait()
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

    def _log(self, message):
        self.log_output.append(message)

    def closeEvent(self, event):
        if self.worker and self.worker.is_alive():
            self.worker.stop()
        event.accept()
