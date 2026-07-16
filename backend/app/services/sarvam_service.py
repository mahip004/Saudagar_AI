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

        headers = {
            "api-key": self.api_key
        }
        
        # Sarvam speech-to-text accepts multipart form-data
        files = {
            "file": (filename, audio_bytes, "audio/wav")
        }
        data = {
            "model": "saaras_v3",
            "language_code": "hi-IN"  # Default to Hindi-English mix
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
                
                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("transcript", "")
                    logger.info(f"Sarvam AI transcribed: '{transcript}'")
                    return transcript
                else:
                    logger.error(f"Sarvam API error {response.status_code}: {response.text}")
                    return "bhaiya maggi hai kya?"
        except Exception as e:
            logger.error(f"Failed to connect to Sarvam AI STT API: {e}")
            return "bhaiya maggi hai?"

sarvam_service = SarvamService()
