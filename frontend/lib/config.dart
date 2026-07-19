class AppConfig {
  // FastAPI Backend Endpoint URL
  static const String backendUrl = 'https://saudagar-ai-api.onrender.com';
  
  // Default Shop ID representing the Kirana Store
  static const String shopId = 'shop_001';

  // Toggle this to true after completing the Firebase setup in Firebase Console.
  // When false, the app automatically polls the FastAPI endpoints to mock Firestore snapshots.
  static const bool useLiveFirestore = false;

  // Paste your Firebase configurations here after creating your project in the console.
  static const Map<String, String> firebaseConfig = {
    'apiKey': 'YOUR_API_KEY_HERE',
    'authDomain': 'YOUR_PROJECT_ID.firebaseapp.com',
    'projectId': 'YOUR_PROJECT_ID',
    'storageBucket': 'YOUR_PROJECT_ID.appspot.com',
    'messagingSenderId': 'YOUR_SENDER_ID',
    'appId': 'YOUR_APP_ID',
  };
}
