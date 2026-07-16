# Saudagar AI - Project Structure

This file provides a directory hierarchy and reference index for all files written during Saudagar AI implementation.

---

## Folder Tree

```
saudagar_ai/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── demand_capture.py       # Gemini text analysis & routing
│   │   │   ├── demand_intelligence.py  # Pandas analytics (scores, trends)
│   │   │   ├── business_intelligence.py # Fetch weather, holidays, and search spikes
│   │   │   └── procurement.py          # Inventory logic advisor via Gemini
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── firestore_service.py    # Firebase live config & mock database fallback
│   │   │   ├── gemini_service.py       # Structured prompting & mock fallbacks
│   │   │   ├── sarvam_service.py       # Speech-to-Text API proxy
│   │   │   └── matching_service.py     # RapidFuzz catalog alias matching
│   │   ├── __init__.py
│   │   └── models.py                   # Pydantic schemas (requests & DB documents)
│   ├── data/
│   │   └── festivals.json              # Catalog of holiday seasons
│   ├── config.py                       # Settings manager
│   ├── Dockerfile                      # Production build container
│   ├── main.py                         # FastAPI webserver
│   └── requirements.txt                # Pip requirements list
├── frontend/
│   ├── lib/
│   │   ├── services/
│   │   │   ├── api_service.dart        # Client HTTP POST methods
│   │   │   └── firestore_service.dart  # Snapshot streams & periodic polling
│   │   ├── config.dart                 # Endpoint URLs & Firebase project options
│   │   └── main.dart                   # Material 3 responsive dashboard & simulator
│   └── pubspec.yaml                    # Flutter package specs
├── README.md                           # Main quickstart manual
├── SYSTEM_ARCHITECTURE.md              # Layout & agent interactions
├── API_DOCUMENTATION.md                # Endpoint specs
├── FIRESTORE_SCHEMA.md                 # Database collections catalog
├── DEPLOYMENT_GUIDE.md                 # Production guides
├── PROJECT_STRUCTURE.md                # This layout file
└── IMPLEMENTATION_PROGRESS.md          # Feature log tracker
```
