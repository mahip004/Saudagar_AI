import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:frontend/config.dart';

class ApiService {
  final String baseUrl = AppConfig.backendUrl;
  final String shopId = AppConfig.shopId;

  /// Sends a raw text transcript directly to the capture-demand endpoint.
  Future<Map<String, dynamic>> captureDemandText(String transcript) async {
    final url = Uri.parse('$baseUrl/capture-demand');
    
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'shop_id': shopId,
          'transcript': transcript,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Server returned status: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      throw Exception('Failed to connect to backend: $e');
    }
  }

  /// Uploads audio bytes to /upload-audio endpoint.
  Future<Map<String, dynamic>> uploadAudio(Uint8List audioBytes, String filename) async {
    final url = Uri.parse('$baseUrl/upload-audio');
    
    try {
      final request = http.MultipartRequest('POST', url)
        ..fields['shop_id'] = shopId
        ..files.add(
          http.MultipartFile.fromBytes(
            'file',
            audioBytes,
            filename: filename,
          ),
        );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Audio upload failed with status: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      throw Exception('Failed to upload audio: $e');
    }
  }

  /// Registers a new product inside our matching database catalog.
  Future<Map<String, dynamic>> addProduct({
    required String canonicalName,
    required List<String> aliases,
    required String category,
    required String brand,
  }) async {
    final url = Uri.parse('$baseUrl/products');
    
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'canonical_name': canonicalName,
          'aliases': aliases,
          'category': category,
          'brand': brand,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to add product: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error adding product: $e');
    }
  }

  /// Sends feedback for generated procurement recommendations (e.g. accepted/rejected actions).
  Future<void> submitFeedback(String recId, String feedbackStatus) async {
    final url = Uri.parse('$baseUrl/feedback');
    
    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'shop_id': shopId,
          'recommendation_id': recId,
          'feedback': feedbackStatus,
          'comments': 'Submitted from Flutter dashboard client.',
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('Feedback submission failed: ${response.statusCode}');
      }
    } catch (e) {
      print('Error sending feedback: $e');
    }
  }

  /// Force updates Business Intelligence collection (monsoon weather, google trends).
  Future<Map<String, dynamic>> forceBIUpdate() async {
    final url = Uri.parse('$baseUrl/run-bi');
    
    try {
      final response = await http.post(url);
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('BI Agent trigger failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to trigger BI update: $e');
    }
  }
}
