import os
from voice.google_tts import google_tts
from voice.elevenlabs_tts import elevenlabs_tts

def generate_audio(text, language="hi-IN"):
    provider = os.getenv("TTS_PROVIDER", "google")
    if provider == "elevenlabs":
        return elevenlabs_tts(text)
    return google_tts(text, language)
