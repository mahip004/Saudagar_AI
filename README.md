# Saudagar AI

Saudagar AI captures demand from Hinglish/Hindi kirana-store conversations, identifies unavailable products, aggregates demand signals, and prepares procurement recommendations.

## Current runtime architecture

```text
Flutter client
  -> FastAPI backend
     -> Sarvam STT (audio only)
     -> Groq OpenAI-compatible inference endpoint (LLM extraction and recommendations)
     -> Firestore (persistent data)
     -> OpenWeather (weather signal)
```

The backend invokes the demand-intelligence and procurement work after a successful capture. Flutter can either use Firestore snapshot streams or poll the backend endpoints.

## Quick start

Prerequisites: Python 3.12+, Flutter 3.x, and Chrome for the web client.

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
# Used by backend/app/services/gemini_service.py (despite its legacy filename).
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile

SARVAM_API_KEY=your_sarvam_key
OPENWEATHER_API_KEY=your_openweather_key

# Either use a local file for development ...
FIREBASE_CREDENTIALS_PATH=service-account.json
# ... or set FIREBASE_SERVICE_ACCOUNT to the service-account JSON in production.
```

Start the backend:

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

Start Flutter in another terminal:

```bash
cd frontend
flutter pub get
flutter run -d chrome --web-port 3000
```

- Dashboard: <http://localhost:3000>
- Interactive backend API documentation: <http://localhost:8001/docs>

`GEMINI_API_KEY` and `GEMINI_MODEL` remain legacy settings in `backend/config.py`; the active inference implementation uses `GROQ_API_KEY` and `GROQ_MODEL`.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/` | Basic backend liveness response |
| POST | `/capture-demand` | Process a text transcript |
| POST | `/upload-audio` | Transcribe WAV audio then process its transcript |
| POST | `/confirm-product-alias` | Confirm an alias mapping |
| GET/POST | `/products` | Read or add product catalogue items |
| GET | `/recommendations?shop_id=X` | Get recommendations |
| GET | `/demand-summary?shop_id=X` | Get aggregated demand metrics |
| GET | `/business-insights` | Get weather, trends, and festivals |
| POST | `/feedback` | Save recommendation feedback |
| POST | `/run-bi` | Force a business-insights refresh |

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for request, response, and failure behaviour.

## Fallbacks and failure behaviour

This prototype has useful development fallbacks, but they are not a high-availability production solution.

| Dependency | Current behaviour |
| --- | --- |
| Groq LLM | Some calls make one retry. If extraction/verification cannot be trusted, no demand event is saved and `/capture-demand` or `/upload-audio` returns `503`. Product cleaning returns the original phrase; recommendation generation uses rule-based suggestions. |
| Sarvam STT | Without `SARVAM_API_KEY`, the service returns a deterministic mock transcript. With a key, API/network failures are returned as request errors. |
| OpenWeather | Missing key, non-200 response, or request failure uses seasonal mock weather. |
| Firestore startup | Missing/invalid credentials initialise an in-memory mock store. It is ephemeral and must never be used for production data. Runtime Firestore failures are not automatically switched to the mock store. |
| Flutter data streams | When live Firestore is disabled, the client polls backend endpoints. Polling failures are currently silent and may leave stale information on screen. |

### Limits and errors

The backend logs service failures and returns generic `500` errors for most unexpected failures. It does **not** currently classify rate limits (`429`), auth errors (`401`/`403`), provider `5xx` errors, or `Retry-After` values into stable client-facing error codes. The `503` extraction message says a quota limit *may* be responsible, but it is not proof of quota exhaustion.

For production, add structured provider error mapping, retry-after/backoff handling, dependency health checks, persistent logging/alerting, and a visible stale-data/error state in Flutter. See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## Configuration

| Variable | Required for live operation | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes, for LLM extraction/recommendations | Groq inference authentication |
| `GROQ_MODEL` | No | Model name; defaults to `llama-3.3-70b-versatile` |
| `SARVAM_API_KEY` | Yes, for live transcription | Sarvam STT authentication |
| `OPENWEATHER_API_KEY` | No | Live weather; mock weather is used otherwise |
| `FIREBASE_SERVICE_ACCOUNT` | Yes in production | Service-account JSON passed as an environment variable |
| `FIREBASE_CREDENTIALS_PATH` | Development alternative | Local service-account JSON path |

## Project documentation

- [System architecture](SYSTEM_ARCHITECTURE.md)
- [API reference](API_DOCUMENTATION.md)
- [Firestore schema](FIRESTORE_SCHEMA.md)
- [Deployment guide](DEPLOYMENT_GUIDE.md)
- [Implementation status](IMPLEMENTATION_PROGRESS.md)

## License

MIT License.
