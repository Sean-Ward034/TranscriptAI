from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QProgressBar,
    QTextEdit, QFileDialog, QMessageBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QCheckBox
)
from PyQt6.QtCore import QTimer
import os
import warnings
from queue import Queue
from transcriber.whisper_utils import get_available_models, get_optimal_device
from transcriber.transcription_worker import TranscriptionWorker
from transcriber.diarization import is_diarization_available

# Suppress tokenizers warning globally
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio/Video Transcription")
        
        # Suppress warnings
        warnings.filterwarnings("ignore")
        
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
        
        # Check if diarization is available
        diarization_available, diarization_error = is_diarization_available()
        if not diarization_available:
            self._log(f"Speaker diarization is not available: {diarization_error}")
            self._log("Speaker diarization will be disabled.")
            # Disable the diarization option
            self.diarization_combo.setCurrentText("No")
            self.diarization_combo.setEnabled(False)
            self.huggingface_token_edit.setEnabled(False)
            self.token_help_btn.setEnabled(False)
            self.diarization_settings_group.setEnabled(False)

    def _init_ui(self):
        # Create central widget and main layout
        self.central = QWidget()
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)
        
        # Title
        self.title_label = QLabel("Audio/Video Transcription")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
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
        
        # Speaker diarization
        grid.addWidget(QLabel("Speaker Diarization:"), 7, 0)
        self.diarization_combo = QComboBox()
        self.diarization_combo.addItems(["No", "Yes"])
        self.diarization_combo.currentTextChanged.connect(self._update_diarization_ui)
        grid.addWidget(self.diarization_combo, 7, 1)
        
        # HuggingFace token
        grid.addWidget(QLabel("HuggingFace Token:"), 8, 0)
        self.huggingface_token_edit = QLineEdit("")
        self.huggingface_token_edit.setPlaceholderText("Required for diarization")
        grid.addWidget(self.huggingface_token_edit, 8, 1)
        
        # Add button to get help with HF token
        self.token_help_btn = QPushButton("?")
        self.token_help_btn.setMaximumWidth(30)
        self.token_help_btn.clicked.connect(self._show_token_help)
        grid.addWidget(self.token_help_btn, 8, 2)
        
        layout.addLayout(grid)
        
        # Diarization Settings Group
        self.diarization_settings_group = QGroupBox("Diarization Settings")
        diarization_form = QFormLayout()
        
        # Min Speakers
        self.min_speakers_spin = QSpinBox()
        self.min_speakers_spin.setRange(1, 10)
        self.min_speakers_spin.setValue(1)
        self.min_speakers_spin.setToolTip("Minimum number of speakers to detect (1-10)")
        diarization_form.addRow("Min Speakers:", self.min_speakers_spin)
        
        # Max Speakers
        self.max_speakers_spin = QSpinBox()
        self.max_speakers_spin.setRange(1, 10)
        self.max_speakers_spin.setValue(2)
        self.max_speakers_spin.setToolTip("Maximum number of speakers to detect (1-10)")
        diarization_form.addRow("Max Speakers:", self.max_speakers_spin)
        
        # Segmentation
        self.segmentation_spin = QDoubleSpinBox()
        self.segmentation_spin.setRange(0.1, 5.0)
        self.segmentation_spin.setSingleStep(0.1)
        self.segmentation_spin.setValue(1.0)
        self.segmentation_spin.setToolTip("Segmentation parameter: lower values merge segments, higher values create more segments")
        diarization_form.addRow("Segmentation:", self.segmentation_spin)
        
        # Apply Preprocessing - Set checked by default as requested
        self.apply_preproc_check = QCheckBox("Apply Specialized Preprocessing")
        self.apply_preproc_check.setChecked(True)  # Default ON as requested
        self.apply_preproc_check.setToolTip("Apply VAD, normalization, and noise reduction optimized for police calls")
        diarization_form.addRow("", self.apply_preproc_check)
        
        # Add help button for diarization settings
        self.diarization_help_btn = QPushButton("Diarization Help")
        self.diarization_help_btn.clicked.connect(self._show_diarization_help)
        diarization_form.addRow("", self.diarization_help_btn)
        
        self.diarization_settings_group.setLayout(diarization_form)
        layout.addWidget(self.diarization_settings_group)
        
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
        
        # Initialize the diarization UI state
        self._update_diarization_ui(self.diarization_combo.currentText())

    def _update_diarization_ui(self, diarization_state):
        """Update the UI based on diarization being enabled/disabled"""
        is_enabled = (diarization_state == "Yes")
        self.huggingface_token_edit.setEnabled(is_enabled)
        self.token_help_btn.setEnabled(is_enabled)
        self.diarization_settings_group.setEnabled(is_enabled)
        
        if is_enabled:
            diarization_available, error_msg = is_diarization_available()
            if not diarization_available:
                QMessageBox.warning(
                    self,
                    "Diarization Not Available",
                    f"Speaker diarization is not available: {error_msg}\n\n"
                    "Please check your installation of pyannote.audio."
                )
                self.diarization_combo.setCurrentText("No")
                
        # Ensure min_speakers <= max_speakers
        if self.min_speakers_spin.value() > self.max_speakers_spin.value():
            self.min_speakers_spin.setValue(self.max_speakers_spin.value())

    def _show_token_help(self):
        """Show information about getting a HuggingFace token"""
        QMessageBox.information(
            self,
            "HuggingFace Token Help",
            "To use speaker diarization, you need a HuggingFace token with access to the pyannote/speaker-diarization model.\n\n"
            "Steps to get a token:\n"
            "1. Create a HuggingFace account at huggingface.co\n"
            "2. Go to https://huggingface.co/settings/tokens\n"
            "3. Create a new token with 'read' access\n"
            "4. Copy the token and paste it in the field\n"
            "5. Accept the user agreement for pyannote/speaker-diarization model\n"
            "   at https://huggingface.co/pyannote/speaker-diarization\n\n"
            "You can also set the HUGGING_FACE_TOKEN environment variable instead."
        )

    def _show_diarization_help(self):
        """Show information about diarization settings"""
        QMessageBox.information(
            self,
            "Diarization Settings Help",
            "Speaker Diarization Settings:\n\n"
            "Min Speakers (1-10):\n"
            "The minimum number of speakers to detect in the audio. Set to 1 for monologues or interviews with a single subject.\n\n"
            "Max Speakers (1-10):\n"
            "The maximum number of speakers to detect. For conversations between 2 people, set to 2. For panel discussions or meetings, increase as needed.\n\n"
            "Segmentation (0.1-5.0):\n"
            "Controls how aggressively to segment the audio:\n"
            "- Lower values (0.1-0.5): Fewer segments, may merge different speakers together\n"
            "- Default (1.0): Balanced segmentation\n"
            "- Higher values (1.5-5.0): More segments, may split a single speaker into multiple speakers\n\n"
            "Apply Specialized Preprocessing:\n"
            "When enabled (recommended for police calls), the system will:\n"
            "- Apply aggressive Voice Activity Detection (0.02 threshold)\n"
            "- Normalize audio levels to handle varying volumes\n"
            "- Apply strong noise reduction (0.9) optimized for radio static\n"
            "- Focus on speech frequency ranges common in police communications\n\n"
            "Recommended Settings for Police Calls:\n"
            "- Min Speakers: 2 (dispatcher and caller)\n"
            "- Max Speakers: 3 (allow for third participant)\n"
            "- Segmentation: 0.8\n"
            "- Keep 'Apply Specialized Preprocessing' enabled"
        )

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
            
        # Get diarization settings
        enable_diarization = (self.diarization_combo.currentText() == "Yes")
        huggingface_token = self.huggingface_token_edit.text() or None
        min_speakers = self.min_speakers_spin.value()
        max_speakers = self.max_speakers_spin.value()
        segmentation = self.segmentation_spin.value()
        apply_diarization_preprocessing = self.apply_preproc_check.isChecked()
        
        # Ensure min_speakers <= max_speakers
        if min_speakers > max_speakers:
            min_speakers = max_speakers
            self.min_speakers_spin.setValue(min_speakers)
            self._log(f"Adjusted min_speakers to {min_speakers} to match max_speakers")
        
        # Check if diarization is enabled but no token provided
        if enable_diarization and not huggingface_token:
            token_from_env = os.environ.get("HUGGING_FACE_TOKEN")
            if not token_from_env:
                choice = QMessageBox.question(
                    self,
                    "No HuggingFace Token",
                    "Diarization is enabled but no HuggingFace token was provided.\n\n"
                    "Do you want to:\n"
                    "- Yes: Get help setting up a token\n"
                    "- No: Continue without diarization",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if choice == QMessageBox.StandardButton.Yes:
                    self._show_token_help()
                    return
                
                enable_diarization = False
                self._log("Continuing without diarization as no token was provided.")
        
        # Check if diarization is available if enabled
        if enable_diarization:
            diarization_available, diarization_error = is_diarization_available()
            if not diarization_available:
                choice = QMessageBox.question(
                    self,
                    "Diarization Not Available",
                    f"Speaker diarization is not available: {diarization_error}\n\n"
                    "Do you want to continue without diarization?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if choice == QMessageBox.StandardButton.No:
                    self._log("Transcription cancelled.")
                    return
                
                enable_diarization = False
                self._log("Continuing without diarization.")
            
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
        
        if enable_diarization:
            preproc_status = "enabled (optimized for police calls)" if apply_diarization_preprocessing else "disabled"
            self._log(
                f"Diarization enabled with: "
                f"min_speakers={min_speakers}, "
                f"max_speakers={max_speakers}, "
                f"segmentation={segmentation}, "
                f"preprocessing={preproc_status}"
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
            enhance_audio=(self.enhance_combo.currentText() == "Yes"),
            enable_diarization=enable_diarization,
            huggingface_token=huggingface_token,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            segmentation=segmentation,
            apply_diarization_preprocessing=apply_diarization_preprocessing
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
