QT Transition Plan for Audio2Word
==================================

Overview
--------
Transition the GUI layer from Kivy to PyQt while keeping all CLI functionality and backend transcription logic unchanged. The resulting program will work in both CLI and GUI modes with an identical transcription engine.

Implementation Steps
--------------------

1. Create a new folder for the PyQt GUI (e.g. “qt_gui”) that will contain the new GUI files.

2. Develop the main window using PyQt in a new file:
   - File: qt_gui/main_window.py
   - Use QMainWindow as the base class.
   - Build UI elements to match the current Kivy UI:
     - Title label (“Audio/Video Transcription”)
     - File selection area: a QLabel to display selected files and a QPushButton (“Pick Audio/Video File(s)”) with a click event that calls QFileDialog.getOpenFileNames.
     - Output directory selection: a QLabel and a QPushButton (“Pick Output Directory”) to call QFileDialog.getExistingDirectory.
     - Advanced settings area using a QGridLayout:
       • Model: QComboBox with values from get_available_models() (default “medium”)
       • Device: QComboBox configured with “cpu” or “cuda” based on get_optimal_device() logic.
       • Sample Rate: QLineEdit (default “16000”)
       • Channels: QLineEdit (default “1”)
       • Chunking: QComboBox (“Yes”, “No”)
       • Chunk Length: QLineEdit (default “300”)
       • Enhance Audio: QComboBox (“Yes”, “No”)
       • Speaker Diarization: QComboBox (“Yes”, “No”)
     - Control buttons: “Start”, “Stop”, and “Quit” in an HBoxLayout.
     - A QProgressBar for progress updates.
     - A read-only QTextEdit (or QPlainTextEdit) for log display.
   - Use a QTimer (with 500ms interval) to periodically poll the log and progress queues (from TranscriptionWorker) and update the UI accordingly.
   - Methods to implement include:
     • pickFiles() – to handle file selection.
     • pickOutputDirectory() – to select an output folder.
     • startTranscription() – to read values from UI, instantiate a TranscriptionWorker (using the same parameters as CLI), and start it.
     • stopTranscription() – to signal the running worker to stop.
     • updateQueues() – invoked by the QTimer; process log updates and progress numbers.

   Example snippet (pseudocode):
   -----------------------------------------------------------------------
   class MainWindow(QMainWindow):
       def __init__(self):
           super().__init__()
           self.setWindowTitle("Audio/Video Transcription")
           # Create central widget & layout.
           self.central = QWidget()
           self.setCentralWidget(self.central)
           layout = QVBoxLayout(self.central)
           
           # Title Label
           self.titleLabel = QLabel("Audio/Video Transcription")
           layout.addWidget(self.titleLabel)
           
           # File selection row
           fileLayout = QHBoxLayout()
           self.fileLabel = QLabel("No files selected")
           fileLayout.addWidget(self.fileLabel)
           self.pickFilesBtn = QPushButton("Pick Audio/Video File(s)")
           self.pickFilesBtn.clicked.connect(self.pickFiles)
           fileLayout.addWidget(self.pickFilesBtn)
           layout.addLayout(fileLayout)
           
           # Output directory selection
           outLayout = QHBoxLayout()
           self.outDirLabel = QLabel("No output directory selected")
           outLayout.addWidget(self.outDirLabel)
           self.pickOutDirBtn = QPushButton("Pick Output Directory")
           self.pickOutDirBtn.clicked.connect(self.pickOutputDirectory)
           outLayout.addWidget(self.pickOutDirBtn)
           layout.addLayout(outLayout)
           
           # Advanced settings (using QGridLayout)
           grid = QGridLayout()
           grid.addWidget(QLabel("Whisper Model:"), 0, 0)
           self.modelCombo = QComboBox()
           self.modelCombo.addItems(get_available_models())
           self.modelCombo.setCurrentText("medium")
           grid.addWidget(self.modelCombo, 0, 1)
           
           grid.addWidget(QLabel("Device:"), 1, 0)
           self.deviceCombo = QComboBox()
           optimal = get_optimal_device()
           if optimal == "cuda":
               self.deviceCombo.addItems(["cpu", "cuda"])
           else:
               self.deviceCombo.addItem("cpu")
           grid.addWidget(self.deviceCombo, 1, 1)
           
           grid.addWidget(QLabel("Sample Rate (Hz):"), 2, 0)
           self.sampleRateEdit = QLineEdit("16000")
           grid.addWidget(self.sampleRateEdit, 2, 1)
           
           grid.addWidget(QLabel("Channels (1=mono,2=stereo):"), 3, 0)
           self.channelsEdit = QLineEdit("1")
           grid.addWidget(self.channelsEdit, 3, 1)
           
           grid.addWidget(QLabel("Enable Chunking:"), 4, 0)
           self.chunkCombo = QComboBox()
           self.chunkCombo.addItems(["Yes", "No"])
           grid.addWidget(self.chunkCombo, 4, 1)
           
           grid.addWidget(QLabel("Chunk Length (seconds):"), 5, 0)
           self.chunkLengthEdit = QLineEdit("300")
           grid.addWidget(self.chunkLengthEdit, 5, 1)
           
           grid.addWidget(QLabel("Enhance Audio:"), 6, 0)
           self.enhanceCombo = QComboBox()
           self.enhanceCombo.addItems(["Yes", "No"])
           grid.addWidget(self.enhanceCombo, 6, 1)
           
           grid.addWidget(QLabel("Enable Diarization:"), 7, 0)
           self.diarizationCombo = QComboBox()
           self.diarizationCombo.addItems(["Yes", "No"])
           grid.addWidget(self.diarizationCombo, 7, 1)
           
           layout.addLayout(grid)
           
           # Control buttons
           buttonLayout = QHBoxLayout()
           self.startBtn = QPushButton("Start")
           self.startBtn.clicked.connect(self.startTranscription)
           buttonLayout.addWidget(self.startBtn)
           self.stopBtn = QPushButton("Stop")
           self.stopBtn.clicked.connect(self.stopTranscription)
           buttonLayout.addWidget(self.stopBtn)
           self.quitBtn = QPushButton("Quit")
           self.quitBtn.clicked.connect(self.close)
           buttonLayout.addWidget(self.quitBtn)
           layout.addLayout(buttonLayout)
           
           # Progress bar and log output
           self.progressBar = QProgressBar()
           layout.addWidget(self.progressBar)
           self.logOutput = QTextEdit(readOnly=True)
           layout.addWidget(self.logOutput)
           
           # QTimer to update queues
           self.timer = QTimer()
           self.timer.setInterval(500)
           self.timer.timeout.connect(self.updateQueues)
           self.timer.start()
           
           # Storage for selected files and output folder, and worker reference
           self.inputFiles = []
           self.outputDir = ""
           self.worker = None
       
       # Define methods: pickFiles(), pickOutputDirectory(), startTranscription(), stopTranscription(), updateQueues()
       # [Implement each with appropriate QFileDialog calls, parsing from QLineEdit/QComboBox, and using TranscriptionWorker]
   -----------------------------------------------------------------------

3. Create the application bootstrap file for the new Qt GUI:
   - File: qt_gui/app.py
   - In this file, instantiate a QApplication and create an instance of MainWindow.
   - Example snippet:
   -----------------------------------------------------------------------
   from PyQt5.QtWidgets import QApplication
   import sys
   from qt_gui.main_window import MainWindow

   def run():
       app = QApplication(sys.argv)
       window = MainWindow()
       window.show()
       sys.exit(app.exec_())

   if __name__ == "__main__":
       run()
   -----------------------------------------------------------------------

4. Update main.py to use the new PyQt interface for GUI mode:
   - In the main() function, retain the CLI mode branch (checking for "--mode -CLI"). If CLI mode is not triggered, import and launch the PyQt application from qt_gui/app.py.
   - Remove any Kivy imports.
   - Example modification in main.py:
   -----------------------------------------------------------------------
   def main():
       if len(sys.argv) > 1 and "--mode" in sys.argv and "-CLI" in sys.argv:
           # (Disable Qt-specific settings for CLI)
           # Parse CLI arguments and call run_cli(args)
           ...
       else:
           # GUI mode: launch PyQt application
           from qt_gui.app import run as run_qt_app
           run_qt_app()

   if __name__ == "__main__":
       main()
   -----------------------------------------------------------------------

5. Update dependencies in requirements.txt:
   - Remove the Kivy dependency.
   - Add "PyQt6>=6.4.0" for modern Qt features while maintaining Python 3.9 compatibility.
   - Note: PyQt6 is fully compatible with Python 3.9+ and offers improved high DPI support.

6. Ensure that all CLI and transcription functionalities are untouched:
   - The TranscriptionWorker, whisper_utils, and other backend logic should remain unchanged.
   - The updated GUI should initialize and interact only with these modules.

By following these steps, the application will now use a PyQt-based GUI and continue to support the CLI interface with no loss in backend functionality.

Additional Enhancements:
-----------------------

1. Configuration File Support:
   - Add support for YAML configuration files
   - Allow users to save and load transcription settings
   - Default config location: ~/.config/audio2word/config.yaml (Unix) or %APPDATA%\audio2word\config.yaml (Windows)
   - Config will store:
     * Default output directory
     * Preferred Whisper model
     * Default audio settings (sample rate, channels)
     * Chunking preferences
     * Enhancement and diarization preferences

2. File Dialog Implementation:
   - Use native file dialogs (QFileDialog.DontUseNativeDialog = False)
   - Rationale:
     * Better integration with OS file managers
     * Inherits system accessibility features
     * Consistent look and feel with other applications
     * Better performance on some platforms

3. CLI Enhancements:
   - Add --config flag to specify custom config file
   - Add --save-config flag to save current settings as default
   - Add --list-devices to show available CUDA devices
   - Add --version to show program version
