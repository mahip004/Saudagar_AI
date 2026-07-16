# Saudagar AI - System Architecture

This document details the software architecture, sequence diagrams, and agent roles for Saudagar AI.

---

## Architecture Diagram (Event-Driven Data Flow)

```mermaid
graph TD
    A[Flutter App UI] -->|1. Record Voice / Select Demo| B(Sarvam AI Saras v3 STT)
    B -->|2. Returns Hinglish Transcript| A
    A -->|3. POST /capture-demand| C[FastAPI Cloud Backend]
    
    subgraph FastAPI Agent & Service Layer
        C -->|4. Request Extraction| D[Gemini 2.5 Flash]
        D -->|5. Extract Product & Availability| C
        C -->|6. Run Fuzzy Align| E[RapidFuzz Alias Mapping]
        E -->|7. Return Canonical Name| C
    end
    
    C -->|8. Add Demand Event| F[(Firestore: demand_events)]
    
    subgraph Asynchronous Event Listeners
        F -->|Trigger on doc write| G[Demand Intelligence Agent]
        G -->|9. Fetch last 30d events| F
        G -->|10. Calculate score & trends using Pandas| H[(Firestore: demand_summary)]
        
        H -->|Trigger on summary change| I[Procurement Agent]
        J[(Firestore: business_insights)] -->|11. Read insights| I
        H -->|11. Read statistics| I
        I -->|12. Reasoning via Gemini| K[Gemini 2.5 Flash]
        K -->|13. Write suggestions| L[(Firestore: recommendations)]
    end
    
    subgraph Background Scheduler
        M[APScheduler] -->|Every 6 hours| N[Business Intelligence Agent]
        N -->|14. Fetch weather OpenWeather & google trends| O[External APIs]
        N -->|15. Read static holidays| P[festivals.json]
        N -->|16. Update insights| J
    end
    
    L -->|17. Realtime Sync Snapshot| A
    J -->|17. Realtime Sync Snapshot| A
    H -->|17. Realtime Sync Snapshot| A
```

---

## Agent Roles and Specifications

### 1. Demand Capture Agent
- **Trigger**: Receives POST to `/capture-demand` (or audio bytes on `/upload-audio`).
- **Function**: Uses Gemini to extract a structured representation of the customer's request. Uses RapidFuzz to match spelling/variant aliases against the catalog. If unresolved, queries Gemini to match existing categories.
- **Write**: Stores the final aligned request in the `demand_events` collection.

### 2. Demand Intelligence Agent
- **Trigger**: Fires immediately after the Demand Capture Agent writes a new event (simulated via FastAPI BackgroundTasks).
- **Function**: Queries all recent events for the specific shop, parses them into a Pandas DataFrame, and calculates aggregated metrics (unavailable counts, request frequency, demand scores, moving averages).
- **Write**: Overwrites the single document for the shop in `demand_summary`.

### 3. Business Intelligence Agent
- **Trigger**: APScheduler runs it once on startup and then every 6 hours.
- **Function**: Gathers external variables: local weather (OpenWeather API), search interest metrics (Google Trends), and upcoming public holidays (local `festivals.json`).
- **Write**: Overwrites the `latest` document in `business_insights`.

### 4. Procurement Agent
- **Trigger**: Conceptually listens to `demand_summary` changes. Simulated via direct trigger after `demand_summary` updates.
- **Function**: Reads the updated `demand_summary` and `business_insights`. Feeds both JSON bodies into Gemini 2.5 Flash with specific instructions to generate purchasing instructions (increase factor, category alignment, timing) matching the `ProcurementRecommendation` schema.
- **Write**: Updates the shop's document in the `recommendations` collection.

---

## Security Framework
- **Secrets Isolation**: No API keys (Gemini, Sarvam AI, OpenWeather) or Firebase private credentials are ever stored or transmitted to the Flutter client.
- **Direct-to-Client DB Streaming**: The Flutter client establishes read-only listening streams directly to Firestore public client channels (`demand_summary`, `business_insights`, `recommendations`).
- **Restricted Database Writes**: The client is prohibited from writing to Firestore. All state transitions are initiated through FastAPI, which utilizes the Firebase Admin SDK on secure server instances.
