import os
from setuptools import setup, find_packages

# Optional: read a README.md for a long description
this_dir = os.path.abspath(os.path.dirname(__file__))
long_description = ""
readme_path = os.path.join(this_dir, "README.md")
if os.path.isfile(readme_path):
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="audio2word",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A cross-platform Kivy + Whisper-based transcription tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YourUsername/audio2word",
    packages=find_packages(exclude=["tests", "docs"]),
    install_requires=[
        "kivy",
        "python-docx",
        "openai-whisper",
        "torch",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    entry_points={
        # You can optionally create a CLI entry point, e.g.:
        # "console_scripts": [
        #     "audio2word=src.main:main",
        # ],
    },
)
