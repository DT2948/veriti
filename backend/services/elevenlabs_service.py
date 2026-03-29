import httpx

from config import get_settings


settings = get_settings()

VOICE_ID = "w9xM4Spfmuw28ZXAirWK"
MODEL_ID = "eleven_flash_v2_5"
TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"


def generate_audio(text: str) -> bytes:
    """Send text to ElevenLabs TTS and return MP3 bytes."""
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ElevenLabs API key is not configured.")

    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.15,
        },
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(TTS_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.content
