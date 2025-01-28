import threading
import queue
from typing import List, Optional
import os
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .ffmpeg_utils import convert_to_wav_ffmpeg, chunk_wav_file
from .whisper_utils import load_whisper_model, transcribe_audio_segment, format_timecode

class TranscriptionWorker(threading.Thread):
    """Process multiple files in a background thread."""
    
    def __init__(
        self,
        input_files: List[str],
        out_dir: str,
        model_name: str = "medium",
        device: str = "cpu",
        sample_rate: int = 16000,
        channels: int = 1,
        chunk: bool = True,
        chunk_length: int = 300,
        log_queue: Optional[queue.Queue] = None,
        progress_queue: Optional[queue.Queue] = None
    ):
        super().__init__()
        self.input_files = input_files
        self.out_dir = out_dir
        self.model_name = model_name
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk = chunk
        self.chunk_length = chunk_length
        self.log_queue = log_queue
        self.progress_queue = progress_queue
        self.stop_event = threading.Event()
        self.doc_messages = []

    def _log(self, msg: str) -> None:
        """Helper to push log messages to queue or print."""
        if self.log_queue:
            self.log_queue.put(msg)
        else:
            print(msg)
        self.doc_messages.append(msg)

    def _create_document(self, filename: str) -> Document:
        """Create and initialize a new document with basic styling."""
        doc = Document()
        # Add title
        title = doc.add_heading(f"Transcript: {os.path.basename(filename)}", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add processing details
        details = doc.add_paragraph()
        details.add_run("Processing Details\n").bold = True
        details.add_run(f"Model: {self.model_name}\n")
        details.add_run(f"Device: {self.device}\n")
        details.add_run(f"Sample Rate: {self.sample_rate} Hz\n")
        details.add_run(f"Channels: {self.channels}\n")
        if self.chunk:
            details.add_run(f"Chunk Length: {self.chunk_length} seconds\n")
        
        # Add a separator
        doc.add_paragraph("=" * 80)
        
        # Add transcription heading
        doc.add_heading("Transcription", level=2)
        return doc

    def _add_segment_to_doc(self, doc: Document, segment: dict, chunk_idx: Optional[int] = None):
        """Add a single transcription segment to the document."""
        # Create paragraph for this segment
        p = doc.add_paragraph()
        
        # Add chunk indicator if provided
        if chunk_idx is not None:
            chunk_run = p.add_run(f"[Chunk {chunk_idx}] ")
            chunk_run.bold = True
            chunk_run.font.color.rgb = RGBColor(128, 128, 128)

        # Add timestamp
        start_str = format_timecode(segment["start"])
        end_str = format_timecode(segment["end"])
        time_run = p.add_run(f"[{start_str} - {end_str}] ")
        time_run.bold = True
        time_run.font.color.rgb = RGBColor(0, 0, 139)  # Dark blue

        # Add transcribed text
        text_run = p.add_run(segment["text"].strip())
        text_run.font.size = Pt(11)

    def run(self) -> None:
        """Main processing loop."""
        total = len(self.input_files)
        if total == 0:
            self._log("No files to process.")
            return

        # Load Whisper model once
        model = load_whisper_model(
            self.model_name,
            self.device,
            log_queue=self.log_queue
        )
        if not model:
            self._log(f"Failed to load Whisper model '{self.model_name}'")
            return

        for idx, f in enumerate(self.input_files, start=1):
            if self.stop_event.is_set():
                self._log("Stop requested. Halting worker.")
                break

            self._log(f"Processing file {idx}/{total}: '{f}'")
            
            # Create new document for this file
            doc = self._create_document(f)
            
            # Convert to WAV
            wav_file = convert_to_wav_ffmpeg(
                f,
                self.sample_rate,
                self.channels,
                log_queue=self.log_queue
            )
            if not wav_file:
                self._log(f"WAV conversion failed for '{f}'. Skipping.")
                continue

            # Split into chunks if needed
            if self.chunk:
                chunks = chunk_wav_file(
                    wav_file,
                    self.chunk_length,
                    log_queue=self.log_queue
                )
            else:
                chunks = [wav_file]

            # Process all chunks
            all_segments = []
            for chunk_idx, chunk_path in enumerate(chunks, start=1):
                if self.stop_event.is_set():
                    self._log("Stop requested during chunk processing.")
                    break
                
                self._log(f"Transcribing chunk {chunk_idx}/{len(chunks)}")
                result = transcribe_audio_segment(
                    model,
                    chunk_path,
                    verbose=True,
                    log_queue=self.log_queue
                )
                
                # Add segments to document
                for segment in result["segments"]:
                    self._add_segment_to_doc(doc, segment, 
                                          chunk_idx if len(chunks) > 1 else None)
                all_segments.extend(result["segments"])

            # Add processing log if we have messages
            if self.doc_messages:
                doc.add_page_break()
                doc.add_heading("Processing Log", level=2)
                log_para = doc.add_paragraph()
                for msg in self.doc_messages:
                    log_para.add_run(msg + "\n")

            # Save document
            base = os.path.splitext(os.path.basename(f))[0]
            out_path = os.path.join(self.out_dir, base + ".docx")
            doc.save(out_path)
            self._log(f"Saved transcript to '{out_path}'")

            # Clear messages for next file
            self.doc_messages = []

            # Update progress
            if self.progress_queue:
                self.progress_queue.put((idx, total))

        self._log("Transcription worker finished.")

    def stop(self) -> None:
        """Signal the thread to stop gracefully."""
        self.stop_event.set()
