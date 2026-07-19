
# 🏪 Saudagar AI — AI-Powered Kirana Store Intelligence

> **An end-to-end, multi-agent AI system for offline Indian kirana (grocery) stores that captures customer demand from natural Hinglish conversations, identifies stockouts, cross-references real-world context, and generates smart, explainable procurement recommendations.**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![Flutter](https://img.shields.io/badge/Flutter-Web-02569B?logo=flutter)
![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?logo=google)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?logo=firebase)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📑 Table of Contents

- [Problem Statement](#-problem-statement)
- [What It Does](#-what-it-does)
- [System Architecture](#️-system-architecture)
- [The Four Agents](#-the-four-agents)
- [End-to-End Data Flow](#-end-to-end-data-flow)
- [Project Structure](#️-project-structure)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Firestore Data Model](#-firestore-data-model)
- [Example: Multi-Speaker Conversation](#-example-multi-speaker-conversation)
- [AI Services Used](#-ai-services-used)
- [Flutter Dashboard Features](#-flutter-dashboard-features)
- [Configuration](#️-configuration)
- [Design Decisions](#-design-decisions)
- [Security Model](#-security-model)
- [Future Improvements](#-future-improvements)
- [License](#-license)

---

## 🎯 Problem Statement

India's 12M+ kirana stores operate **completely offline** — no POS systems, no demand tracking. When a customer asks *"Bhaiya Maggi hai kya?"* and the shopkeeper says *"Nahi, khatam ho gaya"*, that **lost demand is invisible**. No one records it, no one reorders against it, and the store keeps losing the same sale, day after day.

**Saudagar AI captures that lost demand** — directly from the natural conversation, with no manual data entry — and turns it into prioritized, explainable purchasing action.

## 🧠 What It Does

1. **🎤 Listens** to natural customer–shopkeeper conversations in Hinglish/Hindi (live voice or transcript).
2. **🤖 Extracts** product name, availability, alternatives offered, and purchase status using **Gemini 2.5 Flash**.
3. **🔤 Canonicalizes** noisy product references ("maggi" / "maggie" / "migi") to a clean catalog entry using **RapidFuzz**.
4. **📊 Aggregates** demand intelligence using **Pandas** — stockout frequency, weighted demand scores, and trending products.
5. **🌦️ Cross-references** external signals — live weather (OpenWeather), upcoming festivals, and market search trends.
6. **🛒 Generates** AI-powered procurement recommendations with priority (HIGH/MEDIUM/LOW) and a stated reason — never a black box.
7. **📱 Surfaces** everything in real time on a Flutter Web dashboard the shopkeeper actually uses.

---

## 🏗️ System Architecture

Saudagar AI is a **layered, event-driven, multi-agent system**. The Flutter client is a pure presentation layer — it performs **zero AI inference** and **never writes to the database**. All intelligence lives server-side in four independent agents that coordinate exclusively through Firestore, not through direct function calls to one another. This keeps the pipeline decoupled: any agent can be redeployed, rewritten, or scaled on its own.

![High-Level System Architecture](docs/architecture/01_high_level_architecture.png)

| Layer | Responsibility |
|---|---|
| **Presentation** | Flutter Web dashboard — demand feed, metrics, weather/festival panel, AI recommendations, conversation simulator |
| **Application** | FastAPI backend (`main.py`) — REST routing, Pydantic validation, APScheduler bootstrap, BackgroundTasks orchestration |
| **Agent Orchestration** | Four independent agents (`backend/app/agents/`), each owning one pipeline stage |
| **Shared Services** | `gemini_service.py`, `sarvam_service.py`, `matching_service.py`, `firestore_service.py` — each with a documented fallback |
| **Data & Integration** | Firebase Firestore (in-memory fallback) + Gemini, Sarvam AI, OpenWeather, Google Trends |

> 📌 **Every external service has a graceful fallback.** The entire application runs end-to-end with **zero configured API keys**, using heuristic parsers, seasonal weather mocks, and in-memory storage — essential for demos and low-connectivity kirana environments.

---

## 🤖 The Four Agents

Saudagar AI's intelligence is split across four purpose-built backend agents. Each has its own trigger, reads only the Firestore state it needs, and writes its output back to Firestore for the next stage to pick up.

### ① Demand Capture Agent
`backend/app/agents/demand_capture.py`

![Demand Capture Agent](docs/architecture/03_agent_demand_capture.png)

- **Trigger:** `POST /capture-demand` (text transcript) or `POST /upload-audio` (WAV recording)
- **Process:** Sarvam AI Saras v3 transcribes audio → Gemini 2.5 Flash extracts product / availability / alternative / purchase status → RapidFuzz resolves the canonical product name → unresolved matches escalate to Gemini for category-level matching
- **Output:** New document in `demand_events` → triggers the Demand Intelligence Agent
- **Fallback:** Heuristic keyword parser (no Gemini) · mock transcription (no Sarvam) · exact substring matching (no fuzzy catalog match)

### ② Demand Intelligence Agent
`backend/app/agents/demand_intelligence.py`

![Demand Intelligence Agent](docs/architecture/04_agent_demand_intelligence.png)

- **Trigger:** Fires immediately after the Demand Capture Agent writes a new event (via FastAPI `BackgroundTasks`)
- **Process:** Loads the shop's last 30 days of `demand_events` into a **Pandas** DataFrame; computes `unavailable_counts`, `request_frequencies`, weighted `demand_scores`, and `trending_products`
- **Output:** Overwrites `demand_summary/{shop_id}` → triggers the Procurement Agent; also powers `GET /demand-summary`
- **Fallback:** In-memory dictionary store if Firebase credentials are absent — aggregation logic is unchanged

### ③ Business Intelligence Agent
`backend/app/agents/business_intelligence.py`

![Business Intelligence Agent](docs/architecture/05_agent_business_intelligence.png)

- **Trigger:** `APScheduler` — once on startup, then automatically **every 6 hours** (also callable via `POST /run-bi`)
- **Process:** Fetches live weather from **OpenWeather**, search-interest scores from **Google Trends**, and reads the static Indian festival calendar (`backend/data/festivals.json`) to compute days-away and impact categories
- **Output:** Overwrites `business_insights/latest` → read by the Procurement Agent and streamed to the dashboard's weather/festival widget
- **Fallback:** Seasonal mock weather (monsoon/summer/winter) if `OPENWEATHER_API_KEY` is absent

### ④ Procurement Agent
`backend/app/agents/procurement.py`

![Procurement Agent](docs/architecture/06_agent_procurement.png)

- **Trigger:** Conceptually listens for `demand_summary` changes; triggered directly once the Demand Intelligence Agent's update completes
- **Process:** Reads both `demand_summary` and `business_insights`; feeds both into **Gemini 2.5 Flash** with instructions to cross-reference internal demand against external context (e.g. rain → umbrellas, festival → sweets) and return structured `action` / `percentage_increase` / `reason` / `priority`
- **Output:** Overwrites `recommendations/{shop_id}` → streamed to the Flutter AI Procurement Advisor panel with Accept/Dismiss actions (`POST /feedback`)
- **Fallback:** Deterministic rule-based recommendation generator using demand-score thresholds and festival/weather keyword rules if `GEMINI_API_KEY` is absent

---

## 🔄 End-to-End Data Flow

![Event-Driven Data Flow](docs/architecture/02_event_driven_flow.png)

```
Customer speaks Hinglish ──▶ Sarvam STT ──▶ Gemini 2.5 Flash ──▶ RapidFuzz Matching
                                                                        │
                                               ┌────────────────────────┘
                                               ▼
                              Demand Intelligence Agent (Pandas)
                                               │
                              ┌─────────────────┴─────────────────┐
                              ▼                                   ▼
                    Business Intelligence              Procurement Agent
                    (Weather + Festivals)              (Cross-referenced AI Recs)
                              │                                   │
                              └─────────────┬─────────────────────┘
                                            ▼
                                    Firebase Firestore
                                            │
                                            ▼
                                    Flutter Dashboard (realtime)
```

**Design principle:** Agents communicate **only through Firestore** — never through direct agent-to-agent calls. Each agent reads from and writes to Firestore, giving event-driven decoupling.

---

## 🗂️ Project Structure

```
saudagar_ai/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── demand_capture.py         # Gemini NLU + RapidFuzz product matching
│   │   │   ├── demand_intelligence.py    # Pandas aggregation & demand scoring
│   │   │   ├── business_intelligence.py  # Weather API + festival calendar + trends
│   │   │   └── procurement.py            # AI-powered stock recommendations
│   │   ├── services/
│   │   │   ├── gemini_service.py         # Google Gemini 2.5 Flash integration
│   │   │   ├── firestore_service.py      # Firebase Firestore (+ in-memory fallback)
│   │   │   ├── sarvam_service.py         # Sarvam AI Speech-to-Text
│   │   │   └── matching_service.py       # RapidFuzz fuzzy string matching
│   │   └── models.py                     # Pydantic request/response models
│   ├── data/
│   │   └── festivals.json                # Indian festival calendar with impact categories
│   ├── main.py                           # FastAPI entrypoint + APScheduler
│   ├── config.py                         # Pydantic Settings configuration
│   ├── requirements.txt                  # Python dependencies
│   └── .env                              # API keys (not committed)
├── frontend/
│   ├── lib/
│   │   ├── main.dart                     # Flutter Web dashboard UI
│   │   ├── config.dart                   # App configuration (backend URL, Firebase)
│   │   └── services/
│   │       ├── api_service.dart          # HTTP client for FastAPI
│   │       └── firestore_service.dart    # Firestore / polling fallback
│   └── pubspec.yaml                      # Flutter dependencies
├── docs/
│   └── architecture/                     # System & agent architecture diagrams (this README)
├── SYSTEM_ARCHITECTURE.md                # Detailed architecture & sequence reference
├── FIRESTORE_SCHEMA.md                   # Authoritative Firestore schema reference
├── API_DOCUMENTATION.md                  # Full endpoint request/response reference
├── DEPLOYMENT_GUIDE.md                   # Environment setup & deployment steps
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Flutter SDK 3.x** (with web support enabled)
- **Chrome browser**

### 1. Clone the Repository

```bash
git clone https://github.com/mahip004/Saudagar_AI.git
cd Saudagar_AI
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
# Google Gemini AI (https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_key_here

# Sarvam AI Speech-to-Text (https://dashboard.sarvam.ai)
SARVAM_API_KEY=your_sarvam_key_here

# OpenWeather API (https://openweathermap.org/api)
OPENWEATHER_API_KEY=your_openweather_key_here

# Firebase (optional - app works without it using in-memory storage)
FIREBASE_CREDENTIALS_PATH=service-account.json
```

Start the server:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### 3. Frontend Setup

```bash
cd frontend
flutter pub get
flutter run -d chrome --web-port 3000
```

### 4. Open in Browser

- **Dashboard**: <http://localhost:3000>
- **API Docs**: <http://localhost:8001/docs>

---

## 🔌 API Endpoints

| Method | Endpoint                     | Description                                                             | Owning Agent |
| ------ | ----------------------------- | ------------------------------------------------------------------------ | ------------- |
| `POST` | `/capture-demand`            | Submit a Hinglish transcript for demand NLU extraction & matching       | Demand Capture |
| `POST` | `/upload-audio`              | Upload recorded WAV audio for Sarvam STT transcription + demand capture | Demand Capture |
| `POST` | `/confirm-product-alias`     | Register shopkeeper alias mapping for self-learning pipeline            | Demand Capture |
| `GET`  | `/recommendations?shop_id=X` | Retrieve AI-powered procurement recommendations                         | Procurement |
| `GET`  | `/demand-summary?shop_id=X`  | Retrieve Pandas-aggregated demand scores & stockout frequencies         | Demand Intelligence |
| `GET`  | `/business-insights`         | Retrieve weather forecast, upcoming festivals, and search trends        | Business Intelligence |
| `GET`  | `/products`                  | List all canonical products and their aliases                           | Catalog |
| `POST` | `/products`                  | Register a new canonical product and initial aliases                    | Catalog |
| `POST` | `/feedback`                  | Submit shopkeeper feedback on recommendations (Accept/Dismiss)          | Procurement |
| `POST` | `/run-bi`                    | Force update Business Intelligence agent insights                       | Business Intelligence |

Full request/response payloads: see [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md).

---

## 🗄️ Firestore Data Model

| Collection | Document ID | Written By | Purpose |
|---|---|---|---|
| `products` | auto / canonical slug | Catalog seed / self-learning | Canonical product library used for fuzzy alias mapping |
| `demand_events` | auto UUID | Demand Capture Agent | One record per customer query/conversation processed |
| `demand_summary` | `{shop_id}` | Demand Intelligence Agent | Stockout counts, request frequencies, demand scores, trends |
| `business_insights` | `latest` | Business Intelligence Agent | Current weather, category search trends, upcoming festivals |
| `recommendations` | `{shop_id}` | Procurement Agent | AI-generated purchase recommendations with priority & reasoning |
| `procurement_feedback` | auto UUID | Client (via API) | Shopkeeper Accept/Reject feedback audit log |

Full schema definitions: see [`FIRESTORE_SCHEMA.md`](./FIRESTORE_SCHEMA.md).

---

## 🧪 Example: Multi-Speaker Conversation

```bash
curl -X POST http://localhost:8001/capture-demand \
  -H "Content-Type: application/json" \
  -d '{"shop_id":"shop_001","transcript":"Chocolate hai kya? Nahi bhai khatam ho gaya"}'
```

**Response:**

```json
{
  "event_id": "4613892d-...",
  "product": "Chocolate",
  "canonical_product": "Cadbury Dairy Milk 100g",
  "available": false,
  "alternative": null,
  "purchase_completed": false
}
```

### More Examples

| Conversation                                     | Product     | Available | Alternative | Purchased |
| ------------------------------------------------ | ----------- | --------- | ----------- | --------- |
| *"Chocolate hai kya? Nahi khatam ho gaya"*        | Dairy Milk  | ❌         | —           | ❌         |
| *"Maggi hai? Nahi, Yippee rakh lu? Haan de do"*   | Maggi       | ❌         | Yippee ✅    | ✅         |
| *"Surf Excel hai? Haan de do. 30 rupaye."*        | Surf Excel  | ✅         | —           | ✅         |
| *"Amul butter milega? Nahi khatam. Chodo phir."*  | Amul Butter | ❌         | —           | ❌         |

---

## 🤖 AI Services Used

| Service                     | Purpose                                                                 | Fallback                              |
| --------------------------- | ------------------------------------------------------------------------ | -------------------------------------- |
| **Google Gemini 2.5 Flash** | NLU extraction from Hinglish transcripts + procurement recommendations  | Heuristic keyword parser / rule engine |
| **Sarvam AI**                | Hinglish/Hindi speech-to-text                                           | Mock transcription                     |
| **OpenWeather API**          | Live local weather data                                                 | Seasonal mock (monsoon/summer/winter)  |
| **RapidFuzz**                 | Fuzzy string matching for product canonicalization                      | Exact substring matching               |
| **Pandas**                    | Demand aggregation, scoring, and trending analysis                      | —                                       |
| **Firebase Firestore**        | Persistent cloud database & agent coordination substrate                | In-memory dictionary store             |
| **APScheduler**               | Scheduled Business Intelligence agent updates (every 6 hours)           | —                                       |

---

## 🏪 Flutter Dashboard Features

- **🎤 Demand Capture Terminal** — pulsing mic button + Hinglish conversation simulator chips
- **📊 Demand Intelligence Panel** — live bar charts showing demand scores per product
- **🌦️ Business Insights** — real-time weather, festival countdown, market trend indexes
- **🛒 AI Procurement Advisor** — actionable recommendations with Accept/Dismiss buttons
- **🔄 Real-time Updates** — auto-polls backend every 4 seconds, or uses Firestore snapshot listeners

---

## ⚙️ Configuration

### Backend (`backend/.env`)

| Variable                    | Required    | Description                            |
| ---------------------------- | ------------ | --------------------------------------- |
| `GEMINI_API_KEY`            | Recommended | Google AI Studio API key                |
| `SARVAM_API_KEY`            | Optional    | Sarvam AI speech-to-text key            |
| `OPENWEATHER_API_KEY`       | Optional    | OpenWeather API key for live weather    |
| `FIREBASE_CREDENTIALS_PATH` | Optional    | Path to Firebase service account JSON   |

### Frontend (`frontend/lib/config.dart`)

| Setting            | Default                 | Description                                 |
| -------------------- | -------------------------- | --------------------------------------------- |
| `backendUrl`        | `http://localhost:8001` | FastAPI backend URL                          |
| `shopId`            | `shop_001`               | Default kirana store ID                     |
| `useLiveFirestore`  | `false`                   | Toggle Firestore snapshots vs HTTP polling  |

---

## 📐 Design Decisions

1. **Agents communicate only through Firestore** — no direct agent-to-agent calls. Each agent reads from and writes to Firestore, enabling event-driven decoupling; any agent can be redeployed, rewritten, or scaled independently.
2. **Flutter never performs AI inference** — all NLU, analytics, and recommendation logic runs server-side. Flutter is a pure presentation layer, which also keeps every API key off the device.
3. **Mock fallback for every external service** — the app runs fully without any API keys, using heuristic parsers, seasonal weather mocks, and in-memory storage.
4. **RapidFuzz for product canonicalization** — handles Hindi/English spelling variants (e.g., "Maggi", "maggie", "MAGGI" → "Maggi Noodles") without an LLM call on every match.
5. **Client never writes to Firestore** — all state transitions are initiated through FastAPI, which uses the Firebase Admin SDK on secure server instances; the client holds read-only listener credentials only.

---

## 🔒 Security Model

- **Secrets isolation** — API keys (Gemini, Sarvam AI, OpenWeather) and Firebase private credentials are never stored on or transmitted to the Flutter client.
- **Direct-to-client DB streaming is read-only** — the Flutter client opens listening streams straight to specific Firestore documents/collections (`demand_summary`, `business_insights`, `recommendations`) but cannot write.
- **Restricted database writes** — every state transition is initiated through the FastAPI backend using the Firebase Admin SDK from a trusted server context.
- **.env-based configuration** keeps all provider keys out of source control; `config.py` (Pydantic Settings) validates and types configuration at startup.

Full details: see [`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md).

---

## 🔮 Future Improvements

- [ ] Real-time Firestore streaming end-to-end (when billing is enabled)
- [ ] Multi-product extraction from a single conversation turn
- [ ] In-app voice recording in Flutter with direct Sarvam STT streaming
- [ ] WhatsApp integration for shopkeeper notifications
- [ ] Historical demand trends with time-series charts
- [ ] Multi-store support with comparative analytics
- [ ] Google Maps integration for supplier recommendations

---

## 📄 License

MIT License — Built for the Google AI Hackathon 2026

---

**Built with ❤️ for India's 12M+ Kirana Stores**
*Powered by Google Gemini • Firebase • Flutter*
