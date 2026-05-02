"""
J.A.R.V.I.S. - Voice Module
Speech-to-text and text-to-speech
"""

import os
from typing import Optional


class VoiceModule:
    """Voice input/output handler"""
    
    def __init__(self, tts_engine: str = "pyttsx3"):
        self.tts_engine_name = tts_engine
        self.tts_engine = None
        self._init_tts()
    
    def _init_tts(self):
        """Initialize text-to-speech"""
        if self.tts_engine_name == "pyttsx3":
            try:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                
                # Configure voice
                voices = self.tts_engine.getProperty('voices')
                
                # Prefer male/British voice
                for voice in voices:
                    name_lower = voice.name.lower()
                    if 'male' in name_lower or 'british' in name_lower or 'david' in name_lower:
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                
                # Set speech rate
                self.tts_engine.setProperty('rate', 180)
                self.tts_engine.setProperty('volume', 0.9)
                
            except ImportError:
                print("pyttsx3 not installed, TTS disabled")
            except Exception as e:
                print(f"TTS initialization error: {e}")
    
    def speak(self, text: str, block: bool = True):
        """Speak text aloud"""
        if not self.tts_engine:
            return
        
        try:
            self.tts_engine.say(text)
            if block:
                self.tts_engine.runAndWait()
        except Exception as e:
            print(f"Speech error: {e}")
    
    def speak_async(self, text: str):
        """Speak text asynchronously"""
        import threading
        thread = threading.Thread(target=self.speak, args=(text, True))
        thread.daemon = True
        thread.start()
    
    def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice input (placeholder)"""
        # Would integrate with Whisper or Google Speech Recognition
        return None
    
    def set_rate(self, rate: int):
        """Set speech rate"""
        if self.tts_engine:
            self.tts_engine.setProperty('rate', rate)
    
    def set_volume(self, volume: float):
        """Set speech volume (0.0 to 1.0)"""
        if self.tts_engine:
            self.tts_engine.setProperty('volume', max(0.0, min(1.0, volume)))
    
    def get_status(self) -> dict:
        """Get voice module status"""
        return {
            "tts_available": self.tts_engine is not None,
            "engine": self.tts_engine_name
        }


if __name__ == "__main__":
    voice = VoiceModule()
    print("Voice module initialized")
    print(f"Status: {voice.get_status()}")
    voice.speak("Greetings sir, JARVIS voice module online.")
