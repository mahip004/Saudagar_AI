import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:frontend/config.dart';

class FirestoreService {
  final String shopId = AppConfig.shopId;
  final String backendUrl = AppConfig.backendUrl;
  bool _firebaseInitialized = false;

  FirestoreService() {
    _initializeFirebaseIfNeeded();
  }

  Future<void> _initializeFirebaseIfNeeded() async {
    if (AppConfig.useLiveFirestore && !_firebaseInitialized) {
      try {
        await Firebase.initializeApp(
          options: FirebaseOptions(
            apiKey: AppConfig.firebaseConfig['apiKey'] ?? '',
            authDomain: AppConfig.firebaseConfig['authDomain'] ?? '',
            projectId: AppConfig.firebaseConfig['projectId'] ?? '',
            storageBucket: AppConfig.firebaseConfig['storageBucket'] ?? '',
            messagingSenderId: AppConfig.firebaseConfig['messagingSenderId'] ?? '',
            appId: AppConfig.firebaseConfig['appId'] ?? '',
          ),
        );
        _firebaseInitialized = true;
        print("Firebase core successfully initialized in Flutter app.");
      } catch (e) {
        print("Firebase initialization error: \$e. Falling back to HTTP polling.");
      }
    }
  }

  /// Listens to real-time updates for the Demand Summary document.
  Stream<Map<String, dynamic>> listenToDemandSummary() {
    if (AppConfig.useLiveFirestore) {
      return FirebaseFirestore.instance
          .collection('demand_summary')
          .doc(shopId)
          .snapshots()
          .map((snapshot) {
            return snapshot.data() ?? {};
          });
    } else {
      // Fallback: poll FastAPI demand-summary endpoint periodically
      final controller = StreamController<Map<String, dynamic>>();
      
      Timer.periodic(const Duration(seconds: 4), (timer) async {
        if (controller.isClosed) {
          timer.cancel();
          return;
        }
        try {
          final res = await http.get(Uri.parse('$backendUrl/demand-summary?shop_id=$shopId'));
          if (res.statusCode == 200) {
            controller.add(jsonDecode(res.body));
          }
        } catch (e) {
          // Silent catch to keep UI active
        }
      });
      
      return controller.stream;
    }
  }

  /// Listens to real-time updates for the Business Insights document.
  Stream<Map<String, dynamic>> listenToBusinessInsights() {
    if (AppConfig.useLiveFirestore) {
      return FirebaseFirestore.instance
          .collection('business_insights')
          .doc('latest')
          .snapshots()
          .map((snapshot) {
            return snapshot.data() ?? {};
          });
    } else {
      // Fallback: poll FastAPI business-insights endpoint periodically
      final controller = StreamController<Map<String, dynamic>>();
      
      Timer.periodic(const Duration(seconds: 5), (timer) async {
        if (controller.isClosed) {
          timer.cancel();
          return;
        }
        try {
          final res = await http.get(Uri.parse('$backendUrl/business-insights'));
          if (res.statusCode == 200) {
            controller.add(jsonDecode(res.body));
          }
        } catch (e) {
          // Silent catch to keep UI active
        }
      });
      
      return controller.stream;
    }
  }

  /// Listens to real-time updates for final AI Procurement Recommendations.
  Stream<Map<String, dynamic>> listenToRecommendations() {
    if (AppConfig.useLiveFirestore) {
      return FirebaseFirestore.instance
          .collection('recommendations')
          .doc(shopId)
          .snapshots()
          .map((snapshot) {
            return snapshot.data() ?? {};
          });
    } else {
      // Fallback: poll FastAPI recommendations endpoint periodically
      final controller = StreamController<Map<String, dynamic>>();
      
      Timer.periodic(const Duration(seconds: 4), (timer) async {
        if (controller.isClosed) {
          timer.cancel();
          return;
        }
        try {
          final res = await http.get(Uri.parse('$baseUrl/recommendations?shop_id=$shopId'));
          if (res.statusCode == 200) {
            controller.add(jsonDecode(res.body));
          }
        } catch (e) {
          // Silent catch to keep UI active
        }
      });
      
      return controller.stream;
    }
  }

  // Helper alias to resolve base URL
  String get baseUrl => AppConfig.backendUrl;
}
