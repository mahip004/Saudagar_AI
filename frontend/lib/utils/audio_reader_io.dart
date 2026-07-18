import 'dart:io';
import 'dart:typed_data';

/// Mobile/Desktop: reads audio bytes from a local file path.
Future<Uint8List> readRecordedAudioBytes(String path) async {
  final file = File(path);
  return await file.readAsBytes();
}
