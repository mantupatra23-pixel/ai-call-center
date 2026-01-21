import uuid, os, requests

API_KEY = os.getenv("ELEVENLABS_API_KEY")

def elevenlabs_tts(text, voice_id="Rachel"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.7}
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()

    fname = f"tts_{uuid.uuid4()}.mp3"
    with open(f"static/{fname}", "wb") as f:
        f.write(r.content)
    return fname
