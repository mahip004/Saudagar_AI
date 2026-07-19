# Saudagar AI - Deployment Guide

This guide details how to compile, containerize, and deploy both the FastAPI Cloud Backend and Flutter Frontend to production.

---

## 1. Firebase Firestore Setup

1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Create or select your project: `saudagar-ai`.
3. Select **Firestore Database** from the build menu and click **Create Database**.
4. Set the location (e.g., `asia-south1` or `us-central1`) and choose **Start in Test Mode** for sandbox testing, or configure Firestore Security Rules:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Read-only access for Flutter Client App
    match /demand_summary/{shop_id} { allow read; }
    match /business_insights/{doc} { allow read; }
    match /recommendations/{shop_id} { allow read; }
    
    // Deny direct client writes (Only FastAPI backend can write)
    match /{document=**} {
      allow write: if false; 
    }
  }
}
```
5. Go to **Project Settings -> Service Accounts**, click **Generate New Private Key**, and download the JSON. For local development, place it at `backend/service-account.json`. For production, prefer the `FIREBASE_SERVICE_ACCOUNT` environment variable containing the JSON rather than shipping a credential file in the image.

---

## 2. Deploying FastAPI Backend to Google Cloud Run

We can easily containerize the FastAPI app and deploy it on Google Cloud Run.

### Step 2.1: Verify Dockerfile
A `Dockerfile` has been created in the `backend/` folder (see project root).

### Step 2.2: Build and Deploy using gcloud CLI
Ensure the Google Cloud SDK is installed, authenticated, and configured to your project:
```bash
# Navigate to the backend folder
cd backend

# Submit build to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/saudagar-backend

# Deploy to Cloud Run (allow unauthenticated access for client access)
gcloud run deploy saudagar-backend \
    --image gcr.io/YOUR_PROJECT_ID/saudagar-backend \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars="GROQ_API_KEY=your_groq_key,GROQ_MODEL=llama-3.3-70b-versatile,SARVAM_API_KEY=your_sarvam_key,OPENWEATHER_API_KEY=your_weather_key"
```
*Take note of the Service URL returned by Cloud Run (e.g., `https://saudagar-backend-xxxxx.run.app`).*

The active LLM integration is Groq. `gemini_service.py` is a legacy filename; `GEMINI_API_KEY` is not used by the active inference code.

### Production reliability checklist

- Configure `FIREBASE_SERVICE_ACCOUNT` securely and confirm the service is using live Firestore, not the in-memory demo fallback.
- Restrict CORS to the deployed frontend origin; the current wildcard is only suitable for a prototype.
- Add structured handling for provider `429`, `401`/`403`, timeout, and `5xx` responses before relying on the service operationally. The current backend logs these failures but does not expose provider-specific error codes or retry timing.
- Add monitoring/alerting and dependency health checks. The root endpoint confirms that FastAPI is running; it does not prove Groq, Sarvam, Firestore, or OpenWeather are healthy.
- Do not treat in-memory Firestore, mock STT, or seasonal weather as a production fallback: they are local-demo behaviour and may lead to non-persistent or synthetic data.

---

## 3. Deploying Flutter Frontend

### Option A: Firebase Hosting (Web App)
1. Install the Firebase CLI tool: `npm install -g firebase-tools`.
2. Update `frontend/lib/config.dart`:
   - Change `backendUrl` to your Cloud Run URL.
   - Set `useLiveFirestore = true`.
   - Update `firebaseConfig` keys.
3. Build the Flutter Web bundle:
```bash
cd frontend
flutter build web --release
```
4. Initialize and deploy Hosting:
```bash
firebase login
firebase init hosting
# Select your project, set directory to: build/web, configure as single-page app: Yes
firebase deploy --only hosting
```

### Option B: Build Android APK
Compile a standalone APK to test on a physical Android mobile device:
```bash
cd frontend
flutter build apk --release
```
The resulting binary will be saved at:
`frontend/build/app/outputs/flutter-apk/app-release.apk`
Copy this file to your Android phone to install and demonstrate.
