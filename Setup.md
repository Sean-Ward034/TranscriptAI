# **Setup Guide**

## **Prerequisites**

1. **Python Environment**
   * Python 3.9.13 (recommended)
   * pip package manager

2. **FFmpeg Installation**
   * Windows:
     - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
     - Extract the archive
     - Add the bin folder to your system PATH
     - Restart your terminal/application
   * Linux:
     - Ubuntu/Debian: `sudo apt install ffmpeg`
     - Fedora/RHEL: `sudo yum install ffmpeg`
     - Arch: `sudo pacman -S ffmpeg`
   * macOS:
     - Using Homebrew: `brew install ffmpeg`

## **Installation Steps**

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd audio2word
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   Or install as a package:
   ```bash
   pip install .
   ```

3. **Verify Installation**
   ```bash
   # Check FFmpeg
   ffmpeg -version
   ffprobe -version
   
   # Run the application
   python main.py
   ```

## **Development Setup**

1. **Create Virtual Environment** (recommended)
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Unix/macOS
   source venv/bin/activate
   ```

2. **Install Development Dependencies**
   ```bash
   pip install -e .
   ```

## **Troubleshooting**

1. **FFmpeg Not Found**
   * The application will provide platform-specific installation instructions
   * After installing FFmpeg, ensure it's in your system PATH
   * Restart your terminal after installing FFmpeg
   * On Windows, you might need to log out and back in

2. **CUDA/GPU Issues**
   * Install PyTorch with CUDA support if needed
   * Verify CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`

3. **Qt Installation**
   * If Qt fails to install, check your Python version compatibility
   * You might need additional system packages depending on your OS
