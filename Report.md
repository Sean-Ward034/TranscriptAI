## **Transcription Application: Project Report**

### **1\. Overview and Motivation**

Modern speech-to-text applications can handle various sources—podcasts, videos, phone recordings, etc.—but extracting text **directly from music videos or mixed audio** still poses unique challenges. The ultimate goal of this project is to build a **cross-platform application** that can ingest audio or video files, **transcribe** them using [OpenAI’s Whisper](https://github.com/openai/whisper), and conveniently output the results to `.docx` files. Additionally, the app should be user-friendly, provide **debug/logging** features for troubleshooting, and allow **non-technical** users to operate it without fuss.

### **2\. Project History and Thought Process**

1. **Initial Scripts**  
   * The project began with a **simple Python script** that used `pydub` or `moviepy` to convert `.m4a` or `.mp4` into `.wav`, then called `whisper.transcribe()` to produce a transcript. Output was then saved to a Word doc (`.docx` using `python-docx`).  
   * This was effective for **short, straightforward audio** but occasionally truncated longer files, especially music. The code also used Windows-only directory paths, limiting cross-platform usage.  
2. **Expanding Functionality**  
   * We wanted to **process videos** (e.g., `.avi`, `.mp4`, `.mkv`) by extracting the audio track.  
   * We needed to handle **multiple file types** in one go: `.mp3`, `.wav`, `.m4a`, `.mp4`, etc.  
   * We introduced **FFmpeg** to unify all conversions, removing dependencies on `pydub` and `moviepy`. FFmpeg is more robust, has consistent CLI usage, and is widely supported on Windows, Linux, and macOS.  
3. **Chunking for Long Files**  
   * Whisper can process entire files at once, but for **very long** media (over 10-15 minutes), it might skip or truncate. To address this, we implemented a **chunk-based** approach:  
     * Convert input to WAV using FFmpeg.  
     * Split or “chunk” the WAV into smaller segments (e.g., 5 minutes each).  
     * Transcribe each chunk, then combine transcripts.  
   * This approach improved **completeness** of transcriptions for lengthy material.  
4. **Kivy GUI for Cross-Platform**  
   * To accommodate non-technical users, we built a **Kivy GUI** that runs on Windows, macOS, Linux, and potentially on mobile devices (Android, iOS).  
   * The GUI:  
     * Prompts for input files and output directories.  
     * Lets users choose audio-only, video-only, or both.  
     * Offers advanced settings, like device (CPU/GPU), Whisper model size (`tiny`, `base`, `medium`, `large`, etc.), sample rate, and channel count.  
     * Includes a progress bar and logging panel.  
     * Provides a “Stop” button to abort mid-transcription and a “Quit” button for exiting gracefully.  
5. **Debug Logging and Verbose Output**  
   * Due to some users experiencing **incomplete transcripts**, we added robust logging:  
     * FFmpeg’s `stdout`/`stderr` are captured on error.  
     * Whisper’s `verbose=True` output is available to diagnose chunk skipping or silent audio.  
   * This aids in pinpointing whether issues come from file conversion, chunk splitting, or Whisper’s recognition engine.

### **3\. Technical Concepts and Implementation**

**FFmpeg Command Construction**  
python  
CopyEdit  
`cmd = [`  
    `"ffmpeg", "-y",`  
    `"-i", input_file,`  
    `"-vn",`                     
    `"-acodec", "pcm_s16le",`  
    `"-ar", str(sample_rate),`  
    `"-ac", str(channels),`  
    `output_wav`  
`]`

1.   
   * **`-i input_file`**: The input (audio/video).  
   * **`-vn`**: Disables video.  
   * **`-acodec pcm_s16le`**: Encodes the result in 16-bit little-endian PCM (standard WAV).  
   * **`-ar 16000`**: A typical sample rate for speech recognition.  
   * **`-ac 1`**: Mono.  
   * **`-y`**: Overwrites existing output silently.  
2. **Chunk-Based Splitting**

Using the FFmpeg **segment** feature:  
bash  
CopyEdit  
`ffmpeg -i file.wav -f segment -segment_time 300 -acodec pcm_s16le -ar 16000 -ac 1 out_%03d.wav`

*   
  * This cuts the audio into **5-minute** segments, each transcribed individually and then concatenated in text form.  
3. **Whisper Transcription**

We load a chosen **model** (e.g. `medium`, `large`) and do:  
python  
CopyEdit  
`result = model.transcribe(chunk_file)`  
`transcript = result["text"]`

*   
  * The larger the model, the more accurate it tends to be—though it also requires more GPU memory and time.  
4. **Kivy GUI**  
   * We created a `BoxLayout`\-based interface that:  
     * Requests input via **native Windows file dialogs** (`tkinter.filedialog`) for convenience.  
     * Displays logs in a `TextInput` widget and updates progress via a `ProgressBar`.  
     * Runs the transcription in a **background `threading.Thread`** so the GUI doesn’t freeze.  
   * The user can **stop** or **quit** at any time.

### **4\. Challenges and Lessons**

1. **Truncation of Large Files**  
   * Without chunking, Whisper can fail or skip after a certain length. Splitting the file overcame this, but introduced additional complexity in code.  
2. **Music and Lyrics**  
   * Whisper is primarily trained for **speech**. Purely “musical” segments can yield inaccurate or partial transcripts.  
   * For better lyric extraction, we’ve found that:  
     * **Bigger models** (e.g., `"large-v2"`) help.  
     * **Vocal isolation** (via external tools like Demucs) can remove background noise and enhance transcription accuracy.  
3. **Cross-Platform & Distribution**  
   * The Kivy approach is cross-platform, but shipping `ffmpeg` for each OS can be tricky. On Windows, the user must install FFmpeg or place it on the PATH; on Linux/macOS, system packages or a custom build might be needed.  
4. **Performance**  
   * Large models on CPU can be very slow. A GPU with **CUDA** acceleration dramatically speeds up transcriptions.  
   * The chunk approach also helps handle memory usage better.

### **5\. Recommendations and Future Work**

1. **Improve GUI Flow**  
   * Add a dedicated “FileChooser” or a popup instead of re-initializing layouts.  
   * Provide real-time “chunk X of Y” progress.  
2. **Add Timestamps or SRT Export**  
   * Whisper can provide timestamps. We could generate **.srt** or **.vtt** subtitles for video files. This is invaluable for subtitles or precise time-coded transcripts.  
3. **Vocal Isolation**  
   * Consider integrating a **vocal separation** library like [Demucs](https://github.com/facebookresearch/demucs) so that only vocals are transcribed—reducing background noise confusion.  
4. **Cloud Integration / Web App**  
   * Offer a web interface so users can upload files and receive transcripts online. Integrate with a GPU cloud service if local hardware is insufficient.  
5. **Packaging & Installers**  
   * Tools like [PyInstaller](https://www.pyinstaller.org/) or [Briefcase](https://briefcase.readthedocs.io/) can bundle the Python code and Kivy dependencies into a single `.exe` (Windows) or `.app` (macOS). This would let end-users install without dealing with Python environment complexity.

### **6\. Conclusion**

This project has evolved from a **simple script** to a **full-fledged Kivy GUI** capable of handling multiple audio/video formats, chunking long files, providing progress/logging feedback, and letting users choose advanced Whisper settings.

By merging **ffmpeg** for conversions, **Whisper** for transcription, and **Kivy** for the user interface, we have a **versatile** transcription tool that can be further extended or packaged for broader distribution. For better lyric capture, we suggest using **larger Whisper models** or performing **vocal isolation** first. Ongoing improvements can focus on **more robust file selection**, **cloud-based usage**, and **streamlined installers** for non-technical users.

