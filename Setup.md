## **How to Use**

**Install** dependencies from `requirements.txt` directly:  
bash  
CopyEdit  
`pip install -r requirements.txt`  
or  
bash  
CopyEdit  
`pip install .`

1. in the directory containing `setup.py`.

**Ensure FFmpeg** is installed separately and on your PATH:  
bash  
CopyEdit  
`ffmpeg -version`  
`ffprobe -version`

2. If you see version info, you’re set.  
3. **Run** your main Python script (e.g., `python audio_2_word_app.py`) after installing dependencies.

That’s it\! This approach is **general**, avoids version pinning, and helps prevent confusion about version conflicts.

