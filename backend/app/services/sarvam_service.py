import httpx
import logging
from typing import Optional
from config import settings

logger = logging.getLogger("saudagar_ai.sarvam")

class SarvamService:
    def __init__(self):
        self.api_url = "https://api.sarvam.ai/speech-to-text"
        self.api_key = settings.SARVAM_API_KEY
        if not self.api_key:
            logger.warning(
                "\n"
                "==================================================\n"
                "MOCK SARVAM SERVICE ENABLED (NO API KEY)\n"
                "SARVAM_API_KEY was not found in environment or .env file.\n"
                "Sarvam calls will return mock transcribed text.\n"
                "To use real Sarvam speech-to-text, please perform:\n"
                "========================\n"
                "MANUAL STEP REQUIRED\n"
                "========================\n"
                "1. Sign up on Sarvam AI developer portal.\n"
                "2. Generate an API Key.\n"
                "3. Add 'SARVAM_API_KEY=<your_key>' in saudagar_ai/backend/.env\n"
                "4. Restart the FastAPI server.\n"
                "=================================================="
            )

    async def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        """
        Calls Sarvam AI speech-to-text API.
        If no API key is present, returns a mock transcript.
        """
        if not self.api_key:
            # Generate smart mock responses based on filename or simply default
            name = filename.lower()
            if "maggi" in name:
                return "bhaiya maggi packet milega kya"
            elif "butter" in name or "amul" in name:
                return "ek amul butter aur bread de do uncle"
            elif "colgate" in name:
                return "toothpaste colgate chahie bada wala"
            elif "chocolate" in name or "cadbury" in name:
                return "dairy milk chocolate hai kya"
            return "bhaiya maggi hai kya?"

        import time
        start_time = time.time()
        audio_size = len(audio_bytes) if audio_bytes else 0
        logger.info(f"[Trace] Audio Received: {filename} ({audio_size} bytes)")
        
        if audio_size == 0:
            logger.error(f"[Trace] ERROR: Received empty audio bytes! The Flutter app sent 0 bytes.")
            raise ValueError("Received empty audio file (0 bytes). Recording may have failed on the client.")
        
        logger.info(f"[Trace] Sending to Sarvam API: {self.api_url}")

        headers = {
            "api-subscription-key": self.api_key
        }
        
        # Sarvam speech-to-text accepts multipart form-data
        files = {
            "file": (filename, audio_bytes, "audio/wav")
        }
        data = {
            "model": "saaras:v3",
            "language_code": "hi-IN",  # Default to Hindi-English mix
            "mode": "transcribe"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=30.0
                )
                
                elapsed = time.time() - start_time
                logger.info(f"[Trace] Sarvam Response Received in {elapsed:.2f}s (Status: {response.status_code})")
                
                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("transcript", "")
                    logger.info(f"[Trace] Transcript Generated: '{transcript}'")
                    logger.info(f"[Trace] Transcript Sent to Demand Capture Agent")
                    return transcript
                else:
                    error_text = response.text
                    logger.error(f"[Trace] Sarvam API error {response.status_code}: {error_text}")
                    raise RuntimeError(f"Sarvam API returned {response.status_code}: {error_text}")
        except httpx.HTTPError as e:
            logger.error(f"[Trace] Network error calling Sarvam AI STT API: {e}")
            raise RuntimeError(f"Failed to connect to Sarvam AI: {e}")

sarvam_service = SarvamService()
