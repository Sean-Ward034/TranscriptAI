import os
from setuptools import setup, find_packages

# Read README.md for long description
this_dir = os.path.abspath(os.path.dirname(__file__))
long_description = ""
readme_path = os.path.join(this_dir, "README.md")
if os.path.isfile(readme_path):
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="audio2word",
    version="0.2.0",
    description="A cross-platform Kivy + Whisper-based transcription tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/YourUsername/audio2word",
    packages=find_packages(exclude=["tests", "docs"]),
    install_requires=[
        "kivy>=2.1.0",
        "python-docx",
        "openai-whisper",
        "torch",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "audio2word=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Text Processing :: Linguistic",
    ],
)
