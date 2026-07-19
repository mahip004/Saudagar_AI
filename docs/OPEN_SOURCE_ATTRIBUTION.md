# Open-Source Attribution

## Saudagar AI

This register identifies the direct open-source libraries and frameworks used by the Saudagar AI prototype. Versions are those declared in `backend/requirements.txt` and `frontend/pubspec.yaml` on 19 July 2026. Transitive dependencies are resolved by the respective package managers and retain their own upstream licenses.

| Component | Version | License | Role in Saudagar AI | Source |
|---|---:|---|---|---|
| Python | 3.x runtime | PSF License | Backend runtime | https://www.python.org/ |
| FastAPI | 0.111.0 | MIT | REST API and request handling | https://github.com/fastapi/fastapi |
| Uvicorn | 0.30.1 | BSD-3-Clause | ASGI server | https://github.com/Kludex/uvicorn |
| Pydantic | 2.7.4 | MIT | Request/response validation and schemas | https://github.com/pydantic/pydantic |
| pydantic-settings | 2.3.3 | MIT | Environment-based configuration | https://github.com/pydantic/pydantic-settings |
| Firebase Admin Python SDK | 6.5.0 | Apache-2.0 | Secure server-side Firestore access | https://github.com/firebase/firebase-admin-python |
| Google Generative AI Python SDK | 0.7.2 | Apache-2.0 | Declared backend dependency; not used by the active inference implementation | https://github.com/google-gemini/generative-ai-python |
| RapidFuzz | 3.9.3 | MIT | Product and alias fuzzy matching | https://github.com/rapidfuzz/RapidFuzz |
| pandas | 2.2.2 | BSD-3-Clause | Demand aggregation and scoring | https://github.com/pandas-dev/pandas |
| HTTPX | 0.27.0 | BSD-3-Clause | External HTTP requests | https://github.com/encode/httpx |
| python-multipart | 0.0.9 | Apache-2.0 | Multipart audio-upload parsing | https://github.com/Kludex/python-multipart |
| python-dotenv | 1.0.1 | BSD-3-Clause | Local environment loading | https://github.com/theskumar/python-dotenv |
| APScheduler | 3.10.4 | MIT | Periodic business-intelligence jobs | https://github.com/agronholm/apscheduler |
| Flutter | SDK | BSD-3-Clause | Cross-platform client framework | https://github.com/flutter/flutter |
| Dart | SDK 3.7.2+ | BSD-3-Clause | Client language and runtime | https://github.com/dart-lang/sdk |
| Cupertino Icons | 1.0.8+ | MIT | iOS-style icon set | https://pub.dev/packages/cupertino_icons |
| http | 1.2.1+ | BSD-3-Clause | Flutter REST client | https://pub.dev/packages/http |
| Firebase Core | 3.1.1+ | BSD-3-Clause | Firebase bootstrap for Flutter | https://pub.dev/packages/firebase_core |
| Cloud Firestore | 5.0.1+ | BSD-3-Clause | Realtime Firestore streams | https://pub.dev/packages/cloud_firestore |
| record | 6.2.1+ | MIT | Device audio capture | https://pub.dev/packages/record |
| path_provider | 2.1.3+ | BSD-3-Clause | Device file locations for audio | https://pub.dev/packages/path_provider |
| provider | 6.1.2+ | MIT | Flutter state management | https://pub.dev/packages/provider |
| intl | 0.19.0+ | BSD-3-Clause | Localisation and formatting | https://pub.dev/packages/intl |
| share_plus | 12.0.2+ | BSD-3-Clause | Native sharing integration | https://pub.dev/packages/share_plus |
| shared_preferences | 2.5.3+ | BSD-3-Clause | Local preferences persistence | https://pub.dev/packages/shared_preferences |
| Flutter Lints | 5.0.0+ | BSD-3-Clause | Static-analysis rules (development) | https://pub.dev/packages/flutter_lints |

## External services and data providers

The prototype integrates service APIs rather than redistributing their software: Groq's OpenAI-compatible inference endpoint (reasoning and extraction; default model `llama-3.3-70b-versatile`), Sarvam AI (speech-to-text), Firebase/Cloud Firestore (managed datastore), and OpenWeather (weather). Their use is governed by their respective service terms and credentials must remain server-side. The `google-generativeai` package remains declared but is not used by the active runtime path.

## Attribution and compliance notes

- Saudagar AI does not copy or modify the source code of the packages above; they are consumed as dependencies.
- This register is not a substitute for upstream notices. Before commercial distribution, regenerate a complete software bill of materials from `requirements.txt`, `pubspec.lock`, and the production build artifacts, then retain all required notices.
- The project itself should publish a clear repository license before external release.
