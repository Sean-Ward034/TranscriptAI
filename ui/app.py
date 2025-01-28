from kivy.app import App
from .main_gui import MainGUI

class Audio2WordApp(App):
    """Main Kivy application class."""
    
    def build(self):
        """Build and return the root widget."""
        self.title = "Audio/Video Transcription"
        return MainGUI()

    def on_stop(self):
        """Clean up resources when the app is closing."""
        root = self.root
        if root and root.worker and root.worker.is_alive():
            root.worker.stop()
