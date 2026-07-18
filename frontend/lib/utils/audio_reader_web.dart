import 'dart:typed_data';
import 'package:http/http.dart' as http;

/// Web: the recorder returns a blob URL, so we fetch bytes via HTTP.
Future<Uint8List> readRecordedAudioBytes(String path) async {
  final response = await http.get(Uri.parse(path));
  return response.bodyBytes;
}
