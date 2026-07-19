# Saudagar AI - Prototype Submission Guide

## Prototype showcase

| Submission field | Value |
|---|---|
| Product | Saudagar AI - voice-led demand capture and procurement intelligence for kirana stores |
| Apk-download-Link       | https://drive.google.com/file/d/1Ek5OELKtCBaXq4GQN0TzGmLD-KfTbqDT/view?usp=drive_link |
| Hosted backend / API URL | https://saudagar-ai-api.onrender.com |
| Source repository | https://github.com/mahip004/Saudagar_AI |
| Local setup guide | [README.md](../README.md) |
| Architecture overview | [SYSTEM_ARCHITECTURE.md](../SYSTEM_ARCHITECTURE.md) |
| High-level design | [HLD_Saudagar_AI.docx](HLD_Saudagar_AI.docx) |
| Low-level design | [LLD_Saudagar_AI.docx](LLD_Saudagar_AI.docx) |
| Open-source attribution | [OPEN_SOURCE_ATTRIBUTION.md](OPEN_SOURCE_ATTRIBUTION.md)
Demo Video URL|

## Reviewer journey

1. Open the Flutter app or run the local client.
2. Select a demo interaction or record a Hinglish customer request.
3. Submit audio to `/upload-audio` or a transcript to `/capture-demand`.
4. Observe the structured demand event, the updated demand summary, and the procurement recommendation.
5. Inspect the product catalogue and feedback flow through the documented API endpoints.

## Local verification

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Flutter client (new terminal)
cd frontend
flutter pub get
flutter run
```

Configure the required API/service credentials using the backend environment configuration described in the main README. The active LLM provider is Groq (`GROQ_API_KEY`, optional `GROQ_MODEL`); the `gemini_service.py` filename is legacy. In the absence of Firebase credentials, the backend uses its in-memory mock Firestore implementation for local demonstration only.

