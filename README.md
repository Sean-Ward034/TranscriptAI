# **Transcription Application (Kivy \+ Whisper)**

A **cross-platform** transcription tool built with [Kivy](https://kivy.org/) and [OpenAI Whisper](https://github.com/openai/whisper). This application can:

* **Convert** audio or video files (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.mkv`, etc.) to `.wav` using [FFmpeg](https://ffmpeg.org).  
* **Transcribe** the `.wav` file(s) using Whisper.  
* **Chunk** longer audio into segments to avoid truncation.  
* **Save** final transcripts to **Word documents** (`.docx`).  
* Provide a **GUI** with progress tracking, logging, and advanced settings (Whisper model, GPU/CPU selection, sample rate, etc.).

---

## **Table of Contents**

* Features  
* Requirements  
* Installation  
* Usage  
  * Running the App  
  * Choosing Files and Directories  
  * Advanced Settings  
* Notes on Chunking & Larger Files  
* FAQ  
* License

---

## **Features**

1. **Kivy GUI**  
   * User-friendly interface for picking files, output directories, and advanced options.  
   * Real-time log output and progress bar with color-coded stages.  
2. **Multi-Format Conversion**  
   * Uses FFmpeg to extract or convert audio tracks from any video/audio source into WAV.  
3. **Chunking for Long Files**  
   * Automatically splits large WAV files (e.g., 5-minute chunks) to ensure Whisper processes the entire file.  
4. **Whisper Integration**  
   * Choose from different models (`tiny`, `base`, `small`, `medium`, `large`, `large-v2`) for better accuracy or performance.  
   * Supports CPU or GPU (`cuda`), if available.  
5. **Threaded Processing**  
   * Transcription happens in a background thread, so the GUI remains responsive.  
   * Stop button to gracefully halt mid-transcription.  
6. **DOCX Output**  
   * Final transcripts are saved as `.docx` files (one per file or combined, depending on your setup).

---

## **Requirements**

* **Python 3.8+** (tested primarily on 3.9+).  
* **FFmpeg** installed and on your system PATH (including `ffprobe`).  
  * [Download FFmpeg here](https://ffmpeg.org/download.html) or from third-party sources (e.g., Gyan.dev builds).  
* **Pip packages**:  
  * [Kivy](https://kivy.org/): `pip install kivy`  
  * [OpenAI Whisper](https://github.com/openai/whisper): `pip install openai-whisper`  
    * Or install from GitHub: `pip install git+https://github.com/openai/whisper.git`  
  * [PyTorch](https://pytorch.org/) (with CUDA support if you want GPU acceleration).  
  * `python-docx` for `.docx` output: `pip install python-docx`  
  * `tkinter` for native file dialogs (often included with standard Python on Windows; on some Linux distros you may need `sudo apt-get install python3-tk`).

---

## **Installation**

1. **Clone or Download** this repository.

**Install Python Dependencies**:  
bash  
CopyEdit  
`pip install -r requirements.txt`

2. Or install individually (see **Requirements** above).

**Confirm FFmpeg**:  
bash  
CopyEdit  
`ffmpeg -version`  
`ffprobe -version`

3. If this fails, follow [FFmpeg installation](https://ffmpeg.org/download.html) instructions.

---

## **Usage**

### **Running the App**

**Navigate** to the project folder:  
bash  
CopyEdit  
`cd path/to/this/project`

1. 

**Launch** the script (Windows example):  
bash  
CopyEdit  
`python audio_2_word_app.py`  
or  
bash  
CopyEdit  
`python3 audio_2_word_app.py`

2. (depending on your system’s Python command).

### **Choosing Files and Directories**

* **Pick Audio/Video File(s)**:  
  * Click **“Pick Audio/Video File(s)”** → select one or multiple files (mp3, mp4, wav, etc.) → OK.  
* **Pick Output Directory**:  
  * Click **“Pick Output Directory”** → choose a folder to store `.docx` files.

### **Advanced Settings**

* **Whisper Model**: Choose between `tiny`, `base`, `small`, `medium`, `large`, or `large-v2`.  
* **Device**: `cpu` or `cuda` (if you have a compatible NVIDIA GPU \+ CUDA-enabled PyTorch).  
* **Sample Rate (Hz)**: Defaults to `16000`. (Whisper resamples internally, so leaving it at `16000` is usually fine.)  
* **Channels (1=mono, 2=stereo)**: Typically `1` for speech recognition.  
* **Start**: Begins the transcription in a background thread.  
* **Stop**: Cancels mid-transcription.  
* **Quit**: Exits the app.

Once transcription starts, a **progress bar** indicates how many files are done, and the **log panel** shows details (e.g., “Converting file…,” “Transcribing chunk…,” “Saved transcript…”).

---

## **Notes on Chunking & Larger Files**

* **Chunk-Based Approach**: By default, long files (over \~5 minutes) can be split into smaller `.wav` segments. This avoids Whisper’s occasional issues with single, very large audio.  
* **Performance**: Larger models (e.g., `"large-v2"`) can greatly improve lyric transcription but require more memory and compute time, especially on CPU. For best performance, use a **GPU** by selecting `cuda`.

---

## **FAQ**

1. **Q**: “I get no output / empty `.docx`?”  
   **A**: Check the log for errors about FFmpeg or chunking. Make sure your WAV file is valid and that you have the correct path. Try disabling chunking or switching to a smaller model.  
2. **Q**: “Transcription ends early on music tracks\!”  
   **A**: Music with vocals is inherently harder. Consider:  
   * Using a **bigger Whisper model** (`"large"` or `"large-v2"`).  
   * **Vocal isolation** (demucs, etc.) to reduce background instruments.  
3. **Q**: “FFmpeg isn’t recognized?”  
   **A**: Ensure you installed FFmpeg and added it to your system PATH.  
   * On Windows, place `ffmpeg.exe` and `ffprobe.exe` in a folder, then add that folder to PATH in **System → Environment Variables**.

**Q**: “CUDA not available?”  
**A**: Check your PyTorch install:  
bash  
CopyEdit  
`python -c "import torch; print(torch.cuda.is_available())"`

4.   
   * If `False`, reinstall or use a different build of PyTorch that supports CUDA on your system.

---

## **License**

MIT License (or whichever license you choose). You are free to use and modify this code for your own projects. Contributions welcome—open a pull request or file an issue on the repository.