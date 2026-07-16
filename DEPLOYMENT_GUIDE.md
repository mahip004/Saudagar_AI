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
5. Go to **Project Settings -> Service Accounts**, click **Generate New Private Key**, and download the JSON. Place it at `backend/service-account.json`.

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
    --set-env-vars="GEMINI_API_KEY=your_gemini_key,SARVAM_API_KEY=your_sarvam_key,OPENWEATHER_API_KEY=your_weather_key"
```
*Take note of the Service URL returned by Cloud Run (e.g., `https://saudagar-backend-xxxxx.run.app`).*

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
