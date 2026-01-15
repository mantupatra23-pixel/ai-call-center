from gtts import gTTS
import uuid
import os

def text_to_voice(text, lang="hi"):
    filename = f"data/{uuid.uuid4()}.mp3"
    tts = gTTS(text=text, lang=lang)
    tts.save(filename)
    return filename
