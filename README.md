# 🏪 Saudagar AI — AI-Powered Kirana Store Intelligence

> **An end-to-end AI assistant for offline Indian kirana (grocery) stores that captures customer demand from natural Hinglish conversations, identifies stockouts, analyzes trends, and generates smart procurement recommendations.**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![Flutter](https://img.shields.io/badge/Flutter-Web-02569B?logo=flutter)
![Gemini](https://img.shields.io/badge/Google_Gemini-2.0_Flash-4285F4?logo=google)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?logo=firebase)

---

## 🎯 Problem Statement

India's 12M+ kirana stores operate **completely offline** — no POS systems, no demand tracking. When a customer asks *"Bhaiya Maggi hai kya?"* and the shopkeeper says *"Nahi, khatam ho gaya"*, that **lost demand is invisible**. Saudagar AI captures it.

## 🧠 What It Does

1. **🎤 Listens** to natural customer-shopkeeper conversations in Hinglish/Hindi
2. **🤖 Extracts** product name, availability, alternatives, and purchase status using **Gemini 2.0 Flash**
3. **📊 Aggregates** demand intelligence using **Pandas** (stockout frequency, demand scores, trending products)
4. **🌦️ Cross-references** external signals — live weather (OpenWeather), upcoming festivals, market trends
5. **🛒 Generates** AI-powered procurement recommendations with priority and reasoning

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐
│   Flutter Web    │────▶│              FastAPI Backend                 │
│   Dashboard      │◀────│                                              │
│                  │     │  ┌─────────────┐  ┌────────────────────┐    │
│  • Demand Feed   │     │  │ Demand      │  │ Business           │    │
│  • Demand Metrics│     │  │ Capture     │──│ Intelligence       │    │
│  • Weather/Fest  │     │  │ Agent       │  │ Agent              │    │
│  • AI Recs       │     │  │ (Gemini+    │  │ (Weather+Festivals │    │
│  • Simulator     │     │  │  RapidFuzz) │  │  +Trends)          │    │
│                  │     │  └──────┬──────┘  └──────────┬─────────┘    │
│                  │     │         │                     │              │
│                  │     │  ┌──────▼──────┐  ┌──────────▼─────────┐    │
│                  │     │  │ Demand      │  │ Procurement        │    │
│                  │     │  │Intelligence │──│ Agent              │    │
│                  │     │  │ Agent       │  │ (Gemini cross-ref) │    │
│                  │     │  │ (Pandas)    │  │                    │    │
│                  │     │  └─────────────┘  └────────────────────┘    │
│                  │     │         │                     │              │
│                  │     │  ┌──────▼─────────────────────▼─────────┐   │
│                  │     │  │        Firebase Firestore             │   │
│                  │     │  │    (In-memory fallback available)     │   │
│                  │     │  └──────────────────────────────────────┘   │
└─────────────────┘     └──────────────────────────────────────────────┘
```

### Agent Pipeline

```
Customer speaks Hinglish ──▶ Sarvam STT ──▶ Gemini 2.0 Flash ──▶ RapidFuzz Matching
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
                                    Flutter Dashboard
```

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
│   │   │   ├── gemini_service.py         # Google Gemini 2.0 Flash integration
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
├── SYSTEM_ARCHITECTURE.md
├── DEPLOYMENT_GUIDE.md
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

- **Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API Docs**: [http://localhost:8001/docs](http://localhost:8001/docs)

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/capture-demand` | Submit a Hinglish transcript for demand NLU extraction & matching |
| `POST` | `/upload-audio` | Upload recorded WAV audio for Sarvam STT transcription + demand capture |
| `POST` | `/confirm-product-alias` | Register shopkeeper alias mapping for self-learning pipeline |
| `GET` | `/recommendations?shop_id=X` | Retrieve AI-powered procurement recommendations |
| `GET` | `/demand-summary?shop_id=X` | Retrieve Pandas-aggregated demand scores & stockout frequencies |
| `GET` | `/business-insights` | Retrieve weather forecast, upcoming festivals, and search trends |
| `GET` | `/products` | List all canonical products and their aliases |
| `POST` | `/products` | Register a new canonical product and initial aliases |
| `POST` | `/feedback` | Submit shopkeeper feedback on recommendations (Accept/Dismiss) |
| `POST` | `/run-bi` | Force update Business Intelligence agent insights |

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

| Conversation | Product | Available | Alternative | Purchased |
|---|---|---|---|---|
| *"Chocolate hai kya? Nahi khatam ho gaya"* | Dairy Milk | ❌ | — | ❌ |
| *"Maggi hai? Nahi, Yippee rakh lu? Haan de do"* | Maggi | ❌ | Yippee ✅ | ✅ |
| *"Surf Excel hai? Haan de do. 30 rupaye."* | Surf Excel | ✅ | — | ✅ |
| *"Amul butter milega? Nahi khatam. Chodo phir."* | Amul Butter | ❌ | — | ❌ |

---

## 🤖 AI Services Used

| Service | Purpose | Fallback |
|---------|---------|----------|
| **Google Gemini 2.0 Flash** | NLU extraction from Hinglish transcripts + procurement recommendations | Heuristic keyword parser |
| **Sarvam AI** | Hinglish/Hindi speech-to-text | Mock transcription |
| **OpenWeather API** | Live Mumbai weather data | Seasonal mock (monsoon/summer/winter) |
| **RapidFuzz** | Fuzzy string matching for product canonicalization | Exact substring matching |
| **Pandas** | Demand aggregation, scoring, and trending analysis | — |
| **Firebase Firestore** | Persistent cloud database | In-memory dictionary store |
| **APScheduler** | Scheduled BI agent updates (every 6 hours) | — |

---

## 🏪 Flutter Dashboard Features

- **🎤 Demand Capture Terminal** — Pulsing mic button + Hinglish conversation simulator chips
- **📊 Demand Intelligence Panel** — Live bar charts showing demand scores per product
- **🌦️ Business Insights** — Real-time weather, festival countdown, market trend indexes
- **🛒 AI Procurement Advisor** — Actionable recommendations with Accept/Dismiss buttons
- **🔄 Real-time Updates** — Auto-polls backend every 4 seconds (or uses Firestore snapshots)

---

## ⚙️ Configuration

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Recommended | Google AI Studio API key |
| `SARVAM_API_KEY` | Optional | Sarvam AI speech-to-text key |
| `OPENWEATHER_API_KEY` | Optional | OpenWeather API key for live weather |
| `FIREBASE_CREDENTIALS_PATH` | Optional | Path to Firebase service account JSON |

### Frontend (`frontend/lib/config.dart`)

| Setting | Default | Description |
|---------|---------|-------------|
| `backendUrl` | `http://localhost:8001` | FastAPI backend URL |
| `shopId` | `shop_001` | Default kirana store ID |
| `useLiveFirestore` | `false` | Toggle Firestore snapshots vs HTTP polling |

---

## 📐 Design Decisions

1. **Agents communicate only through Firestore** — No direct agent-to-agent calls. Each agent reads from and writes to Firestore, enabling event-driven decoupling.
2. **Flutter never performs AI inference** — All NLU, analytics, and recommendation logic runs server-side. Flutter is a pure presentation layer.
3. **Mock fallback for every external service** — The app runs fully without any API keys, using heuristic parsers, seasonal weather mocks, and in-memory storage.
4. **RapidFuzz for product canonicalization** — Handles Hindi/English spelling variants (e.g., "Maggi", "maggie", "MAGGI" → "Maggi Noodles").

---

## 🔮 Future Improvements

- [ ] Real-time Firestore streaming (when billing is enabled)
- [ ] Multi-product extraction from single conversation
- [ ] Voice recording in Flutter with Sarvam STT
- [ ] WhatsApp integration for shopkeeper notifications
- [ ] Historical demand trends with time-series charts
- [ ] Multi-store support with comparative analytics
- [ ] Google Maps integration for supplier recommendations

---

## 📄 License

MIT License — Built for the Google AI Hackathon 2026

---

<p align="center">
  <b>Built with ❤️ for India's 12M+ Kirana Stores</b><br>
  <i>Powered by Google Gemini • Firebase • Flutter</i>
</p>
