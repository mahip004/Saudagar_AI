import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:record/record.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:frontend/utils/audio_reader_stub.dart'
    if (dart.library.io) 'package:frontend/utils/audio_reader_io.dart'
    if (dart.library.html) 'package:frontend/utils/audio_reader_web.dart';

import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/firestore_service.dart';
import 'package:frontend/config.dart';
import 'package:frontend/l10n/app_localizations.dart';
import 'package:frontend/providers/locale_provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    MultiProvider(
      providers: [
        Provider<ApiService>(create: (_) => ApiService()),
        Provider<FirestoreService>(create: (_) => FirestoreService()),
        ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
      ],
      child: const SaudagarApp(),
    ),
  );
}

class SaudagarApp extends StatelessWidget {
  const SaudagarApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final localeProvider = Provider.of<LocaleProvider>(context);
    
    return MaterialApp(
      title: 'Saudagar AI',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.dark,
      locale: localeProvider.locale,
      supportedLocales: const [
        Locale('en', ''),
        Locale('hi', ''),
      ],
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F111A), // Deep obsidian background
        primaryColor: const Color(0xFF6366F1), // Indigo accents
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6366F1),
          secondary: Color(0xFF10B981), // Emerald
          surface: Color(0xFF161925), // Dark card surface
          error: Color(0xFFEF4444), // Coral red
        ),
        textTheme: const TextTheme(
          headlineMedium: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold, color: Colors.white),
          titleLarge: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold, color: Color(0xB3FFFFFF)),
          bodyMedium: TextStyle(fontFamily: 'Inter', color: Color(0x99FFFFFF)),
        ),
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  final AudioRecorder _audioRecorder = AudioRecorder();
  
  bool _isRecording = false;
  String _recordingStatus = "Tap Mic to Record Demand";
  bool _isLoading = false;
  String? _lastTranscript;
  Map<String, dynamic>? _lastExtractedEvent;
  int _currentIndex = 0;
  
  final Set<String> _unselectedRecommendationProducts = {};

  // Pre-configured phrases for simulation testing (multi-speaker conversations)
  final List<String> _simulatedPhrases = [
    // Stockout - shopkeeper says no
    "Chocolate hai kya? Nahi bhai khatam ho gaya",
    // Customer asks, available, purchase completed
    "Bhaiya Maggi de do do packet. Haan ye lo 24 rupaye.",
    // Stockout, no purchase
    "Amul butter milega? Nahi butter khatam hai. Achha chodo phir.",
    // Alternative offered and accepted
    "Maggi hai kya? Sorry Maggi nahi hai, Yippee rakh lu? Haan chalo Yippee de do.",
    // Available, purchase done
    "Uncle Cadbury dairy milk de do bade wale. Haan ye lijiye, 50 rupaye.",
    // Stockout simple
    "Bhaiya Surf Excel hai? Nahi bhai aaj nahi aaya.",
    // Alternative offered, customer bought it
    "Ata hai Aashirvaad? Nahi beta, Fortune hai. Achha wahi de do.",
    // Colgate available and purchased
    "Colgate toothpaste hai? Haan hai. Chhota wala de do. Ye lo.",
    // Lux not available, Dettol offered
    "Bhaiya Lux soap chahiye. Nahi hai, Dettol chalega? Haan de do Dettol.",
  ];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    )..repeat(reverse: true);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final loc = AppLocalizations.of(context);
    if (loc != null) {
      // If currently displaying default idle message, update it to the active language
      if (_recordingStatus == "Tap Mic to Record Demand" || 
          _recordingStatus == "मांग रिकॉर्ड करने के लिए माइक दबाएं") {
        _recordingStatus = loc.translate('tapMicToRecord');
      }
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _audioRecorder.dispose();
    super.dispose();
  }

  // Handle start and stop recording
  Future<void> _toggleRecording(ApiService apiService) async {
    try {
      if (_isRecording) {
        setState(() {
          _isRecording = false;
          _isLoading = true;
          _recordingStatus = AppLocalizations.of(context)?.translate('processingSarvam') ?? "Processing voice on Sarvam AI...";
        });

        final path = await _audioRecorder.stop();
        if (path == null) {
          setState(() {
            _isLoading = false;
            _recordingStatus = AppLocalizations.of(context)?.translate('audioFailed') ?? "Audio recording failed";
          });
          return;
        }

        // Platform-aware: reads blob URL on web, file path on mobile
        final Uint8List audioBytes = await readRecordedAudioBytes(path);
        debugPrint('[Audio] Read ${audioBytes.length} bytes from recording');

        // Send to backend via Multipart
        final response = await apiService.uploadAudio(audioBytes, 'recording.wav');
        if (response != null) {
          final event = response['event'];
          setState(() {
            _isLoading = false;
            _recordingStatus = AppLocalizations.of(context)?.translate('tapMicToRecord') ?? "Tap Mic to Record Demand";
            _lastTranscript = response['transcript'];
            _lastExtractedEvent = event;
          });

          final isHindi = AppLocalizations.of(context)?.locale.languageCode == 'hi';
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              backgroundColor: const Color(0xFF10B981),
              content: Text("${isHindi ? 'कैप्चर किया गया' : 'Captured'}: '${_lastTranscript}'"),
            ),
          );
          
          // Show confirmation dialog if backend requests it
          if (event['needs_confirmation'] == true) {
            final candidates = List<String>.from(event['candidates'] ?? []);
            _showAliasConfirmationDialog(context, apiService, event['product'], candidates);
          }
        }
      } else {
        // Check permissions
        if (await _audioRecorder.hasPermission()) {
          setState(() {
            _isRecording = true;
            _recordingStatus = AppLocalizations.of(context)?.translate('recordingVoice') ?? "Recording voice... Tap again to send";
          });
          // Start recording
          await _audioRecorder.start(
            const RecordConfig(encoder: AudioEncoder.wav, sampleRate: 16000),
            path: 'recording.wav',
          );
        } else {
          setState(() {
            _recordingStatus = AppLocalizations.of(context)?.translate('microphonePermissionDenied') ?? "Microphone permission denied";
          });
        }
      }
    } catch (e) {
      setState(() {
        _isRecording = false;
        _isLoading = false;
        _recordingStatus = "${AppLocalizations.of(context)?.translate('error') ?? 'Error: '}$e";
      });
    }
  }

  // Simulate text capture
  Future<void> _simulateTextCapture(ApiService apiService, String text) async {
    setState(() {
      _isLoading = true;
      _recordingStatus = AppLocalizations.of(context)?.translate('simulationSending') ?? "Sending simulation to cloud...";
    });

    try {
      final response = await apiService.captureDemandText(text);
      setState(() {
        _isLoading = false;
        _recordingStatus = AppLocalizations.of(context)?.translate('tapMicToRecord') ?? "Tap Mic to Record Demand";
        _lastTranscript = text;
        _lastExtractedEvent = response;
      });

      final isHindi = AppLocalizations.of(context)?.locale.languageCode == 'hi';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: const Color(0xFF10B981),
          content: Text("${isHindi ? 'संसाधित वाक्य' : 'Processed'}: \"$text\""),
        ),
      );
      
      if (response['needs_confirmation'] == true) {
        final candidates = List<String>.from(response['candidates'] ?? []);
        _showAliasConfirmationDialog(context, apiService, response['product'], candidates);
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _recordingStatus = "Error: $e";
      });
    }
  }

  void _showAliasConfirmationDialog(BuildContext context, ApiService apiService, String rawProduct, List<String> candidates) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        final loc = AppLocalizations.of(context);
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom + 20,
            top: 20,
            left: 16,
            right: 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                loc?.translate("verifyProduct") ?? "Verify Product",
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                loc?.iHeardNotSure(rawProduct) ?? "I heard '$rawProduct', but I'm not sure which product it is. Please select:",
                style: const TextStyle(color: Color(0x99FFFFFF), fontSize: 16),
              ),
              const SizedBox(height: 16),
              ...candidates.map((canonical) => ListTile(
                leading: const Icon(Icons.check_circle_outline, color: Colors.blue),
                title: Text(canonical, style: const TextStyle(fontWeight: FontWeight.bold)),
                onTap: () async {
                  Navigator.pop(context);
                  try {
                    await apiService.confirmProductAlias(canonical, rawProduct);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(loc?.learnedAlias(rawProduct, canonical) ?? "Learned! '$rawProduct' is now '$canonical'")),
                      );
                    }
                  } catch (e) {
                    print("Error: $e");
                  }
                },
              )).toList(),
              const Divider(),
              ListTile(
                leading: const Icon(Icons.cancel_outlined, color: Colors.red),
                title: Text(loc?.translate("noneOfThese") ?? "None of these"),
                onTap: () {
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final apiService = Provider.of<ApiService>(context, listen: false);
    final firestoreService = Provider.of<FirestoreService>(context, listen: false);

    // List of widgets for each tab
    final List<Widget> _pages = [
      _buildVoiceCard(apiService),
      _buildDemandSummaryPanel(firestoreService),
      _buildInsightsPanel(firestoreService),
      _buildRecommendationsPanel(firestoreService, apiService),
    ];

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // HEADER (Persistent)
              _buildHeader(apiService),
              const SizedBox(height: 16),

              // MAIN CONTENT (Switched based on active tab)
              Expanded(
                child: _pages[_currentIndex],
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        backgroundColor: const Color(0xFF161925),
        selectedItemColor: const Color(0xFF10B981),
        unselectedItemColor: const Color(0x61FFFFFF),
        items: [
          BottomNavigationBarItem(
            icon: const Icon(Icons.mic),
            label: AppLocalizations.of(context)?.translate('tabCapture') ?? 'Capture',
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.bar_chart),
            label: AppLocalizations.of(context)?.translate('tabDemand') ?? 'Demand',
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.insights),
            label: AppLocalizations.of(context)?.translate('tabInsights') ?? 'Insights',
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.shopping_cart),
            label: AppLocalizations.of(context)?.translate('tabAdvisor') ?? 'Advisor',
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(ApiService apiService) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6366F1).withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF6366F1).withOpacity(0.5)),
                    ),
                    child: const Icon(Icons.auto_awesome, color: Color(0xFF6366F1), size: 20),
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'SAUDAGAR AI',
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 2.0,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Kirana Intelligence Hub • Shop ${AppConfig.shopId}',
                style: const TextStyle(fontSize: 12, color: Color(0x61FFFFFF)),
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
        Row(
          children: [
            IconButton(
              icon: Icon(
                Provider.of<LocaleProvider>(context).locale.languageCode == 'hi'
                    ? Icons.g_translate
                    : Icons.language,
                color: const Color(0xFF6366F1),
              ),
              onPressed: () {
                Provider.of<LocaleProvider>(context, listen: false).toggleLanguage();
              },
              tooltip: "Toggle Language",
            ),
            ElevatedButton.icon(
              onPressed: () async {
                try {
                  final res = await apiService.forceBIUpdate();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text("Triggered Business Intelligence Agent refresh!"),
                      backgroundColor: Color(0xFF6366F1),
                    ),
                  );
                } catch (e) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text("Error triggering BI: $e"), backgroundColor: Colors.red),
                  );
                }
              },
              icon: const Icon(Icons.refresh, size: 16),
              label: Text(AppLocalizations.of(context)?.translate('refreshInsights') ?? "Refresh Insights"),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF161925),
                foregroundColor: Colors.white,
                side: BorderSide(color: const Color(0xFF6366F1).withOpacity(0.3)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildVoiceCard(ApiService apiService) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF161925),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Color(0x0DFFFFFF)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF6366F1).withOpacity(0.05),
            blurRadius: 20,
            spreadRadius: 2,
          )
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                AppLocalizations.of(context)?.translate('demandCaptureTerminal') ?? 'Demand Capture Terminal',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              if (_isLoading)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF6366F1)),
                )
              else
                const Icon(Icons.online_prediction, color: Color(0xFF10B981), size: 16),
            ],
          ),
          const SizedBox(height: 16),
          
          // PULSING RECORD BUTTON
          GestureDetector(
            onTap: () => _toggleRecording(apiService),
            child: AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                double scale = 1.0 + (_pulseController.value * 0.08);
                return Transform.scale(
                  scale: _isRecording ? scale : 1.0,
                  child: Container(
                    width: 70,
                    height: 70,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: _isRecording
                            ? [const Color(0xFFEF4444), const Color(0xFFF87171)]
                            : [const Color(0xFF6366F1), const Color(0xFF4F46E5)],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: _isRecording
                              ? const Color(0xFFEF4444).withOpacity(0.4)
                              : const Color(0xFF6366F1).withOpacity(0.3),
                          blurRadius: 15,
                          spreadRadius: 2,
                        )
                      ],
                    ),
                    child: Icon(
                      _isRecording ? Icons.stop : Icons.mic,
                      color: Colors.white,
                      size: 32,
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 12),
          Text(
            _recordingStatus,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: _isRecording ? const Color(0xFFEF4444) : Color(0x99FFFFFF),
            ),
          ),
          const Divider(height: 32, color: Color(0x1AFFFFFF)),
          
          // SIMULATOR PANEL
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              AppLocalizations.of(context)?.translate('hinglishSimulator') ?? 'Hinglish Demo Simulator (Tap to trigger pipeline)',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0x61FFFFFF)),
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 38,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: _simulatedPhrases.length,
              itemBuilder: (context, index) {
                final phrase = _simulatedPhrases[index];
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: ActionChip(
                    label: Text(
                      phrase,
                      style: const TextStyle(fontSize: 11, color: Color(0xB3FFFFFF)),
                    ),
                    backgroundColor: const Color(0xFF22263F),
                    side: BorderSide(color: const Color(0xFF6366F1).withOpacity(0.15)),
                    onPressed: _isLoading ? null : () => _simulateTextCapture(apiService, phrase),
                  ),
                );
              },
            ),
          ),
          
          // DISPLAY LAST RECORD
          if (_lastExtractedEvent != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B).withOpacity(0.4),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Color(0x08FFFFFF)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        AppLocalizations.of(context)?.translate('lastExtractedEvent') ?? "Last Extracted Event",
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF6366F1)),
                      ),
                      Text(
                        _lastExtractedEvent!['timestamp'] != null
                            ? _lastExtractedEvent!['timestamp'].toString().substring(11, 16)
                            : '',
                        style: const TextStyle(fontSize: 10, color: Color(0x3DFFFFFF)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    "${AppLocalizations.of(context)?.translate('rawLabel') ?? 'Raw: '}\"${_lastTranscript}\"",
                    style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: Color(0x8AFFFFFF)),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      _buildMiniBadge(
                        AppLocalizations.of(context)?.translate('matchedLabel').replaceAll(": ", "") ?? "Matched", 
                        _lastExtractedEvent!['canonical_product'] ?? 'Unknown', 
                        const Color(0xFF6366F1)
                      ),
                      const SizedBox(width: 8),
                      _buildMiniBadge(
                        AppLocalizations.of(context)?.translate('statusLabel').replaceAll(": ", "") ?? "Status", 
                        _lastExtractedEvent!['available'] == true 
                            ? (AppLocalizations.of(context)?.translate('availableLabel') ?? "Available") 
                            : (AppLocalizations.of(context)?.translate('unavailableLabel') ?? "Unavailable (Stockout)"), 
                        _lastExtractedEvent!['available'] == true ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                      ),
                    ],
                  )
                ],
              ),
            )
          ]
        ],
      ),
    );
  }

  Widget _buildMiniBadge(String title, String val, Color col) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: col.withOpacity(0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: col.withOpacity(0.3)),
      ),
      child: Text(
        "$title: $val",
        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: col),
      ),
    );
  }

  Widget _buildInsightsPanel(FirestoreService firestoreService) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF161925),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Color(0x0DFFFFFF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.query_stats, color: Color(0xFF6366F1), size: 18),
              const SizedBox(width: 8),
              Text(
                AppLocalizations.of(context)?.translate('businessInsights') ?? 'Business Insights',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: StreamBuilder<Map<String, dynamic>>(
              stream: firestoreService.listenToBusinessInsights(),
              builder: (context, snapshot) {
                if (snapshot.hasError) {
                  return Center(child: Text("Error loading insights: ${snapshot.error}", style: const TextStyle(fontSize: 12)));
                }
                if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return Center(
                    child: Text(
                      AppLocalizations.of(context)?.translate('noInsights') ?? "No business insights stored in Firestore yet.\nClick 'Refresh Insights' above to trigger.",
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12, color: Color(0x3DFFFFFF)),
                    ),
                  );
                }

                final data = snapshot.data!;
                final weather = data['weather'] as Map<String, dynamic>? ?? {};
                final trends = data['trends'] as Map<String, dynamic>? ?? {};
                final festivals = data['festivals'] as List<dynamic>? ?? [];

                return ListView(
                  children: [
                    // Weather Card
                    _buildSubCard(
                      icon: Icons.cloud,
                      iconColor: Colors.blueAccent,
                      title: AppLocalizations.of(context)?.translate('weatherForecast') ?? "Local Weather Forecast",
                      subtitle: "${AppLocalizations.of(context)?.translate('cityLabel') ?? 'City: '}${weather['city'] == 'Mumbai' ? (AppLocalizations.of(context)?.translate('mumbai') ?? 'Mumbai') : (weather['city'] ?? 'Mumbai')} • ${weather['temp'] ?? '--'}°C (${weather['condition'] ?? 'Unknown'})",
                      detail: "${AppLocalizations.of(context)?.translate('humidityLabel') ?? 'Humidity: '}${weather['humidity'] ?? '--'}% • ${AppLocalizations.of(context)?.translate('sourceLabel') ?? 'Source: '}${weather['source'] ?? '--'}",
                    ),
                    const SizedBox(height: 8),
                    // Festival Card
                    if (festivals.isNotEmpty) ...[
                      _buildSubCard(
                        icon: Icons.calendar_month,
                        iconColor: Colors.orangeAccent,
                        title: AppLocalizations.of(context)?.translate('festivalAlert') ?? "Festival Demand Alert",
                        subtitle: "${festivals[0]['name']} ${festivals[0]['days_away']} ${AppLocalizations.of(context)?.translate('daysAway') ?? 'days away'}",
                        detail: "${AppLocalizations.of(context)?.translate('gearingUp') ?? 'Gearing up: '}${List<String>.from(festivals[0]['impact_categories'] ?? []).join(', ')}",
                      ),
                      const SizedBox(height: 8),
                    ],
                    // Google Trends Card
                    _buildSubCard(
                      icon: Icons.trending_up,
                      iconColor: const Color(0xFF10B981),
                      title: AppLocalizations.of(context)?.translate('monsoonSpikes') ?? "Monsoon Search Spikes",
                      subtitle: "${AppLocalizations.of(context)?.translate('instantNoodles') ?? 'Instant Noodles'}: ${trends['packaged_foods'] ?? 50}% • ${AppLocalizations.of(context)?.translate('beverages') ?? 'Beverages'}: ${trends['beverages'] ?? 50}%",
                      detail: AppLocalizations.of(context)?.translate('monsoonDetail') ?? "Customers searching hot drinks/foods due to wet weather.",
                    ),
                  ],
                );
              },
            ),
          )
        ],
      ),
    );
  }

  Widget _buildSubCard({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required String detail,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF22263F).withOpacity(0.4),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Color(0x05FFFFFF)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xCCFFFFFF))),
                const SizedBox(height: 4),
                Text(subtitle, style: const TextStyle(fontSize: 11, color: Color(0x8AFFFFFF))),
                const SizedBox(height: 4),
                Text(detail, style: const TextStyle(fontSize: 10, color: Color(0x3DFFFFFF))),
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildDemandSummaryPanel(FirestoreService firestoreService) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF161925),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Color(0x0DFFFFFF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.analytics, color: Color(0xFF10B981), size: 18),
              const SizedBox(width: 8),
              Text(
                AppLocalizations.of(context)?.translate('demandMetricsTitle') ?? 'Demand Intelligence Metrics',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: StreamBuilder<Map<String, dynamic>>(
              stream: firestoreService.listenToDemandSummary(),
              builder: (context, snapshot) {
                if (snapshot.hasError) {
                  return Center(child: Text("Error: ${snapshot.error}", style: const TextStyle(fontSize: 12)));
                }
                if (!snapshot.hasData || snapshot.data!.isEmpty || snapshot.data!['demand_scores'] == null) {
                  return Center(
                    child: Text(
                      AppLocalizations.of(context)?.translate('noDemandEvents') ?? "No demand events analyzed yet.\nUse the simulator or mic to create demand.",
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12, color: Color(0x3DFFFFFF)),
                    ),
                  );
                }

                final data = snapshot.data!;
                final scores = data['demand_scores'] as Map<String, dynamic>? ?? {};
                final unavail = data['unavailable_counts'] as Map<String, dynamic>? ?? {};
                final freq = data['request_frequencies'] as Map<String, dynamic>? ?? {};

                final products = scores.keys.toList();
                // Sort products by score desc
                products.sort((a, b) => (scores[b] as num).compareTo(scores[a] as num));

                return Column(
                  children: [
                    Expanded(
                      child: ListView.builder(
                        itemCount: products.length,
                        itemBuilder: (context, index) {
                          final prod = products[index];
                          final score = (scores[prod] as num).toDouble();
                          final unavailCount = unavail[prod] ?? 0;
                          final totalReq = freq[prod] ?? 0;

                          // Compute color representing demand severity
                          Color barColor = const Color(0xFF6366F1); // Low priority
                          if (score > 6.0) {
                            barColor = const Color(0xFFEF4444); // High critical stockout
                          } else if (score > 2.0) {
                            barColor = const Color(0xFFF59E0B); // Medium
                          }

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      prod,
                                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xB3FFFFFF)),
                                    ),
                                    Text(
                                      "${AppLocalizations.of(context)?.translate('scoreLabel') ?? 'Score: '}${score.toStringAsFixed(1)} (Stockout: $unavailCount / Req: $totalReq)",
                                      style: const TextStyle(fontSize: 11, color: Color(0x61FFFFFF)),
                                    )
                                  ],
                                ),
                                const SizedBox(height: 6),
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(4),
                                  child: LinearProgressIndicator(
                                    value: (score / 15.0).clamp(0.0, 1.0),
                                    backgroundColor: Color(0x08FFFFFF),
                                    valueColor: AlwaysStoppedAnimation<Color>(barColor),
                                    minHeight: 6,
                                  ),
                                )
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                    const Divider(height: 16, color: Color(0x1AFFFFFF)),
                    Row(
                      children: [
                        const Icon(Icons.bolt, color: Color(0xFFF59E0B), size: 14),
                        const SizedBox(width: 4),
                        Text(
                          "${AppLocalizations.of(context)?.translate('trendingProducts') ?? 'Trending Products: '}${List<String>.from(data['trending_products'] ?? []).join(', ')}",
                          style: const TextStyle(fontSize: 11, color: Color(0x8AFFFFFF), fontStyle: FontStyle.italic),
                        ),
                      ],
                    ),
                  ],
                );
              },
            ),
          )
        ],
      ),
    );
  }

  Widget _buildRecommendationsPanel(FirestoreService firestoreService, ApiService apiService) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF161925),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Color(0x0DFFFFFF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.shopping_bag, color: Color(0xFF6366F1), size: 18),
                  const SizedBox(width: 8),
                  Text(
                    AppLocalizations.of(context)?.translate('procurementAdvisor') ?? 'AI Procurement Agent Advisor',
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.share, color: Color(0xFF10B981), size: 18),
                tooltip: AppLocalizations.of(context)?.translate('sharePurchaseList') ?? "Share Purchase List",
                onPressed: () {
                  _shareRecommendations(context, firestoreService);
                },
              ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: StreamBuilder<Map<String, dynamic>>(
              stream: firestoreService.listenToRecommendations(),
              builder: (context, snapshot) {
                if (snapshot.hasError) {
                  return Center(child: Text("Error: ${snapshot.error}", style: const TextStyle(fontSize: 12)));
                }
                if (!snapshot.hasData || snapshot.data!.isEmpty || snapshot.data!['recommendations'] == null) {
                  return Center(
                    child: Text(
                      AppLocalizations.of(context)?.translate('noRecommendations') ?? "No procurement recommendations generated.\nAdd demand out-of-stocks to trigger Procurement reasoning.",
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 12, color: Color(0x3DFFFFFF)),
                    ),
                  );
                }

                final recs = snapshot.data!['recommendations'] as List<dynamic>;

                if (recs.isEmpty) {
                  return Center(
                    child: Text(
                      AppLocalizations.of(context)?.translate('inventoryOptimal') ?? "Inventory levels are optimal.",
                      style: const TextStyle(fontSize: 12, color: Color(0x61FFFFFF)),
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: recs.length,
                  itemBuilder: (context, index) {
                    final rec = recs[index] as Map<String, dynamic>;
                    final product = rec['product'] ?? 'Generic';
                    final action = rec['action'] ?? 'Increase order';
                    final reason = rec['reason'] ?? 'High demand';
                    final priority = rec['priority'] ?? 'MEDIUM';

                    Color priorityColor = const Color(0xFF6366F1);
                    if (priority == "HIGH") {
                      priorityColor = const Color(0xFFEF4444);
                    } else if (priority == "MEDIUM") {
                      priorityColor = const Color(0xFFF59E0B);
                    }

                    bool isChecked = !_unselectedRecommendationProducts.contains(product);

                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF22263F).withOpacity(0.3),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: priorityColor.withOpacity(0.2)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              // Checklist Checkbox
                              Checkbox(
                                value: isChecked,
                                activeColor: const Color(0xFF10B981),
                                checkColor: Colors.black,
                                visualDensity: VisualDensity.compact,
                                onChanged: (val) {
                                  setState(() {
                                    if (val == true) {
                                      _unselectedRecommendationProducts.remove(product);
                                    } else {
                                      _unselectedRecommendationProducts.add(product);
                                    }
                                  });
                                },
                              ),
                              Expanded(
                                child: Text(
                                  product,
                                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: priorityColor.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: priorityColor.withOpacity(0.4)),
                                ),
                                child: Text(
                                  priority,
                                  style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: priorityColor),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              const Icon(Icons.shopping_cart, color: Color(0xFF10B981), size: 14),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  action,
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF10B981)),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            reason,
                            style: const TextStyle(fontSize: 11, color: Color(0x8AFFFFFF)),
                          ),
                          const Divider(height: 16, color: Color(0x1AFFFFFF)),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton(
                                onPressed: () async {
                                  await apiService.submitFeedback(index.toString(), "REJECTED");
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text("Rejected alert for $product"), backgroundColor: Colors.red),
                                  );
                                },
                                style: TextButton.styleFrom(
                                  foregroundColor: const Color(0x4DFFFFFF),
                                  padding: const EdgeInsets.symmetric(horizontal: 10),
                                ),
                                child: Text(AppLocalizations.of(context)?.translate('dismiss') ?? "Dismiss", style: const TextStyle(fontSize: 11)),
                              ),
                              const SizedBox(width: 8),
                              ElevatedButton(
                                onPressed: () async {
                                  await apiService.submitFeedback(index.toString(), "ACCEPTED");
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        AppLocalizations.of(context)?.locale.languageCode == 'hi'
                                          ? "अनुशंसा स्वीकृत: $product का ऑर्डर दिया गया"
                                          : "Accepted recommendation: Order placed for $product"
                                      ),
                                      backgroundColor: const Color(0xFF10B981),
                                    ),
                                  );
                                },
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: priorityColor.withOpacity(0.2),
                                  foregroundColor: Colors.white,
                                  side: BorderSide(color: priorityColor.withOpacity(0.5)),
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                                child: Text(AppLocalizations.of(context)?.translate('acceptOrder') ?? "Accept & Order", style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                              ),
                            ],
                          )
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          )
        ],
      ),
    );
  }

  void _shareRecommendations(BuildContext context, FirestoreService firestoreService) async {
    try {
      final snapshot = await firestoreService.listenToRecommendations().first;
      if (snapshot.isEmpty || snapshot['recommendations'] == null) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)?.translate('noRecommendationsToShare') ?? "No recommendations to share.")));
        return;
      }
      
      final recs = snapshot['recommendations'] as List<dynamic>;
      final selectedRecs = recs.where((r) {
        final rec = r as Map<String, dynamic>;
        final product = rec['product'] ?? 'Generic';
        return !_unselectedRecommendationProducts.contains(product);
      }).toList();

      if (selectedRecs.isEmpty) {
         ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)?.translate('listIsEmpty') ?? "List is empty.")));
         return;
      }

      StringBuffer sb = StringBuffer();
      sb.writeln("🛒 ${AppLocalizations.of(context)?.translate('purchaseList') ?? 'Purchase List'} 🛒\n");
      
      for (var r in selectedRecs) {
        final rec = r as Map<String, dynamic>;
        sb.writeln("☑ ${rec['product']}");
        sb.writeln("  Priority: ${rec['priority']} | Action: ${rec['action']}");
        sb.writeln("  Reason: ${rec['reason']}\n");
      }
      
      sb.writeln(AppLocalizations.of(context)?.translate('generatedBySaudagar') ?? "Generated by Saudagar AI Kirana Intelligence.");
      
      await Share.share(sb.toString());
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error sharing: $e")));
    }
  }
}
