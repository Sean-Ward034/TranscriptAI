# **Transcription Application (Kivy + Whisper)**

A **cross-platform** transcription tool built with [Kivy](https://kivy.org/) and [OpenAI Whisper](https://github.com/openai/whisper). This application can:

* **Convert** audio or video files (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.mkv`, etc.) to `.wav` using [FFmpeg](https://ffmpeg.org).  
* **Transcribe** the `.wav` file(s) using Whisper.  
* **Chunk** longer audio into segments to avoid truncation.  
* **Save** final transcripts to **Word documents** (`.docx`).  
* Provide a **GUI** with progress tracking, logging, and advanced settings (Whisper model, GPU/CPU selection, sample rate, etc.).

## **Project Structure**

```
project_root/
├─ transcriber/           # Core transcription functionality
│   ├─ ffmpeg_utils.py    # FFmpeg conversion and chunking
│   ├─ whisper_utils.py   # Whisper model loading and transcription
│   └─ transcription_worker.py  # Background processing thread
├─ ui/                    # Kivy user interface
│   ├─ main_gui.py        # Main application layout
│   └─ app.py            # Kivy app class
├─ main.py               # Application entry point
├─ setup.py              # Package configuration
└─ requirements.txt      # Dependencies
```

## **Requirements**

* **Python 3.8+** (tested primarily on 3.9+)
* **FFmpeg** installed and on your system PATH (including `ffprobe`)
* **Pip packages**:
  * Kivy (>=2.1.0)
  * OpenAI Whisper
  * PyTorch (with CUDA support if you want GPU acceleration)
  * python-docx

## **Installation**

1. **Clone or Download** this repository
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Verify FFmpeg**:
   ```bash
   ffmpeg -version
   ffprobe -version
   ```

## **Usage**

1. **Start the Application**:
   ```bash
   python main.py
   ```

2. **Using the Interface**:
   * Click "Pick Audio/Video File(s)" to select input files
   * Choose an output directory for the transcripts
   * Adjust settings if needed:
     * Whisper Model (tiny to large-v2)
     * Device (CPU/GPU)
     * Sample Rate
     * Audio Channels
     * Chunking Options
   * Click "Start" to begin transcription
   * Monitor progress in the log window
   * Use "Stop" to cancel if needed

## **Advanced Features**

* **Chunking**: Long files are automatically split into manageable segments
* **GPU Support**: Uses CUDA if available for faster processing
* **Progress Tracking**: Real-time updates on transcription progress
* **Native File Dialogs**: Uses system file pickers for better integration

## **Contributing**

Contributions welcome! Please feel free to submit a Pull Request.

## **License**

MIT License - see LICENSE file for details.