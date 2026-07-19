# Saudagar AI - Deployment Guide

This guide details how to compile, containerize, and deploy both the FastAPI backend and the Flutter frontend to production.

> **Current live deployment:**
> - **Backend (Render)**: [https://saudagar-ai-api.onrender.com](https://saudagar-ai-api.onrender.com)
> - **Frontend (Android APK)**: [Download link](https://drive.google.com/file/d/1Ek5OELKtCBaXq4GQN0TzGmLD-KfTbqDT/view?usp=drive_link)
>
> The instructions below cover both the deployment already in use (Render) and an alternative path (Google Cloud Run) if you want to migrate off Render later.

---

## 1. Firebase Firestore Setup

1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Create or select your project: `saudagar-ai`.
3. Select **Firestore Database** from the build menu and click **Create Database**.
4. Set the location (e.g., `asia-south1` or `us-central1`) and choose **Start in Test Mode** for sandbox testing, or configure Firestore Security Rules:

```
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

## 2. Deploying the FastAPI Backend

### Option A: Render (current live deployment)

The backend currently running at `https://saudagar-ai-api.onrender.com` is deployed on [Render](https://render.com):

1. Push the `backend/` folder to a GitHub repo Render can access (or use this repo directly with a root directory of `backend/`).
2. In the Render dashboard, create a new **Web Service** pointed at the repo.
3. Set the **Start Command**:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variables in the Render dashboard (Settings → Environment):
   ```
   GROQ_API_KEY=your_groq_key
   GROQ_MODEL=llama-3.3-70b-versatile
   SARVAM_API_KEY=your_sarvam_key
   OPENWEATHER_API_KEY=your_weather_key
   FIREBASE_SERVICE_ACCOUNT=<paste service account JSON here>
   ```
5. Deploy. Render will build and expose the service at a `https://<your-service-name>.onrender.com` URL.

> ⚠️ **Free-tier cold starts**: on Render's free plan, the service spins down after inactivity. The first request after idling can take 30–60 seconds while it wakes up. Upgrade to a paid instance to keep it always-on if this matters for your use case.

### Option B: Google Cloud Run

If you'd rather deploy on Google Cloud instead of Render:

**Step 2.1: Verify Dockerfile**

A `Dockerfile` has been created in the `backend/` folder (see project root).

**Step 2.2: Build and Deploy using gcloud CLI**

Ensure the Google Cloud SDK is installed, authenticated, and configured to your project:

```
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

*Take note of the Service URL returned by Cloud Run (e.g., `https://saudagar-backend-xxxxx.run.app`) — you'll need it for `frontend/lib/config.dart` if you switch the app over to it.*

**Note:** The active LLM integration is Groq. `gemini_service.py` is a legacy filename; `GEMINI_API_KEY` is not used by the active inference code.

### Production reliability checklist

- Configure `FIREBASE_SERVICE_ACCOUNT` securely and confirm the service is using live Firestore, not the in-memory demo fallback.
- Restrict CORS to the deployed frontend origin; a wildcard is only suitable for a prototype.
- Add structured handling for provider `429`, `401`/`403`, timeout, and `5xx` responses before relying on the service operationally. The current backend logs these failures but does not expose provider-specific error codes or retry timing.
- Add monitoring/alerting and dependency health checks. The root endpoint confirms that FastAPI is running; it does not prove Groq, Sarvam, Firestore, or OpenWeather are healthy.
- Do not treat in-memory Firestore, mock STT, or seasonal weather as a production fallback: they are local-demo behaviour and may lead to non-persistent or synthetic data.

---

## 3. Deploying the Flutter Frontend

Before building, point the app at your backend by updating `frontend/lib/config.dart`:

- Set `backendUrl` to your deployed backend URL (currently `https://saudagar-ai-api.onrender.com`).
- Set `useLiveFirestore = true` if you want Firestore snapshots instead of HTTP polling.
- Update `firebaseConfig` keys if using Firebase.

### Option A: Android APK (current distribution method)

```
cd frontend
flutter build apk --release
```

The resulting binary is saved at: `frontend/build/app/outputs/flutter-apk/app-release.apk`

This is the file currently distributed as the [downloadable APK](https://drive.google.com/file/d/1Ek5OELKtCBaXq4GQN0TzGmLD-KfTbqDT/view?usp=drive_link). To publish a new build:

1. Run the build command above.
2. Upload the resulting `app-release.apk` to your distribution channel (Google Drive, Play Store, etc.).
3. Update the download link in `README.md` and here if it changes.

### Option B: Firebase Hosting (Web App)

1. Install the Firebase CLI tool: `npm install -g firebase-tools`.
2. Confirm `frontend/lib/config.dart` points at your live backend (see above).
3. Build the Flutter Web bundle:

```
cd frontend
flutter build web --release
```

4. Initialize and deploy Hosting:

```
firebase login
firebase init hosting
# Select your project, set directory to: build/web, configure as single-page app: Yes
firebase deploy --only hosting
```
