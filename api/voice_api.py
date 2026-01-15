from fastapi import APIRouter
from voice.tts import text_to_voice

router = APIRouter()

@router.post("/speak")
def speak(text: str, lang: str = "hi"):
    file_path = text_to_voice(text, lang)
    return {
        "voice_file": file_path
    }
