import os
import subprocess
from docx import Document
from pydub import AudioSegment
import whisper

import moviepy.editor as mp


# Convert ANY AUDIO file into the WAV format.
def convert_to_wav(input_file):
    # Converts any audio file to WAV format.

    try:
        audio = AudioSegment.from_file(input_file)
        output_file = input_file.rsplit('.', 1)[0] + ".wav"
        audio.export(output_file, format="wav")
        print(f"Successfully converted {input_file} to {output_file}")
        
        
    except Exception as e:
        print(f"Error converting {input_file}: {e}")




# Convert ANY VIDEO file to WAV audio format. 
def convert_video_to_wav(video_path, output_path):
    # Converts a video file to WAV audio.

    video_clip = mp.VideoFileClip(video_path)
    audio_clip = video_clip.audio
    audio_clip.write_audiofile(output_path, codec='pcm_s16le')

'''
if __name__ == "__main__":
    video_file = "your_video.mp4"  # Replace with your video file path
    output_file = "output_audio.wav"  # Replace with desired output file name

    convert_video_to_wav(video_file, output_file)
    print("Conversion complete!")
'''




'''
if __name__ == "__main__":
    input_file = input("Enter the path to the audio file: ")
    convert_to_wav(input_file)
'''

'''
def convert_to_wav(audio_file):
    
    # Converts an audio file from the m4a format to the wav format using ffmpeg.

    # Parameters:
    #     audio_file (str): The path to the input audio file in m4a format.
    # 
    # Returns:
    #     str: The path to the converted audio file in wav format.
    
    output_file = audio_file.replace('.m4a', '.wav')
    if os.path.isfile(output_file):
        os.remove(output_file)
    subprocess.run(['ffmpeg', '-i', audio_file, output_file], check=True)
    return output_file
'''

def transcribe_audio(audio_file):
    """Transcribes an audio file using Whisper."""
    model = whisper.load_model("base")  # Choose a Whisper model
    result = model.transcribe(audio_file)
    return result["text"]

def process_directory(directory):
    """Transcribes all audio files in a directory and saves the results to Word documents."""
    
    
    # convert_to_wav() 
    # m4a 
    
    for filename in os.listdir(directory):
        if filename.endswith(".wav") or filename.endswith(".mp3") or filename.endswith(".m4a"):  # Check for audio files
            
            
            audio_path = os.path.join(directory, filename)
            
            # Convert to WAV format if needed
            if filename.endswith(".mp3"):
                audio = AudioSegment.from_mp3(audio_path)
                audio.export(audio_path.replace(".mp3", ".wav"), format="wav")
                audio_path = audio_path.replace(".mp3", ".wav")
            
            '''
            if filename.endswith(".m4a"):
                audio = convert_to_wav(audio_path)
            '''
            
            transcript = transcribe_audio(audio_path)
            print(transcript)

            # Create a Word document
            doc = Document()
            doc.add_paragraph(transcript)
            doc.save(os.path.join(directory, filename.replace(".wav", ".docx")))

if __name__ == "__main__":
    # Documents\\Projects\\Transcription\\Files\\
    directory_to_process = "C:\\Backups\\Files\\Wav\\"  # Replace with your directory path
    process_directory(directory_to_process)