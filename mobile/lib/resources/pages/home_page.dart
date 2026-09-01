import 'dart:convert';

import 'package:camera/camera.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:nylo_framework/nylo_framework.dart';

import '/app/controllers/home_controller.dart';

class HomePage extends NyStatefulWidget<HomeController> {
  static RouteView path = ("/home", (_) => HomePage());

  HomePage({super.key}) : super(child: () => _HomePageState());
}

class _HomePageState extends NyPage<HomePage> {
  CameraController? _camera;
  XFile? _image;
  Map<String, dynamic>? _result;
  List<dynamic> _meters = [];
  String? _meterId;
  String? _error;
  bool _busy = false;
  bool _cameraReady = false;

  @override
  get init => () async {
        await _loadMeters();
      };

  @override
  void dispose() {
    _camera?.dispose();
    super.dispose();
  }

  Future<void> _loadMeters() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiClient.baseUrl}/api/v1/meters'),
        headers: ApiClient.headers,
      );
      if (response.statusCode == 200) {
        _meters = jsonDecode(response.body) as List<dynamic>;
        setState(() {});
      }
    } catch (_) {
      // Recognition can still run without a registered meter.
    }
  }

  Future<void> _openBackCamera() async {
    try {
      final cameras = await availableCameras();
      final back = cameras.where((camera) => camera.lensDirection == CameraLensDirection.back).toList();
      if (back.isEmpty) throw Exception('Không tìm thấy camera sau');
      final controller = CameraController(back.first, ResolutionPreset.high, enableAudio: false);
      await controller.initialize();
      await _camera?.dispose();
      _camera = controller;
      _cameraReady = true;
      _error = null;
      setState(() {});
    } catch (error) {
      setState(() => _error = 'Không mở được camera sau: $error');
    }
  }

  Future<void> _capture() async {
    if (_camera == null || !_camera!.value.isInitialized) return;
    try {
      _image = await _camera!.takePicture();
      setState(() {});
      await _recognize(_image!);
    } catch (error) {
      setState(() => _error = 'Không chụp được ảnh: $error');
    }
  }

  Future<void> _pickImage() async {
    final picked = await FilePicker.platform.pickFiles(type: FileType.image, withData: false);
    if (picked?.files.single.path == null) return;
    _image = XFile(picked!.files.single.path!);
    setState(() {});
    await _recognize(_image!);
  }

  Future<void> _recognize(XFile image) async {
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${ApiClient.baseUrl}/api/v1/recognize'),
      )..headers.addAll(ApiClient.headers);
      request.files.add(await http.MultipartFile.fromPath('file', image.path, filename: 'meter.jpg'));
      if (_meterId != null && _meterId!.isNotEmpty) request.fields['meter_id'] = _meterId!;
      final response = await request.send();
      final body = await response.stream.bytesToString();
      final decoded = jsonDecode(body) as Map<String, dynamic>;
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception(decoded['error']?['message'] ?? 'HTTP ${response.statusCode}');
      }
      setState(() => _result = decoded);
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      setState(() => _busy = false);
    }
  }

  @override
  Widget view(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('WBrain Mobile'),
        backgroundColor: Colors.teal.shade700,
        foregroundColor: Colors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Water-meter OCR', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          Text('Camera sau → YOLO → EditCTC OCR', style: TextStyle(color: Colors.grey.shade700)),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _meterId,
            decoration: const InputDecoration(labelText: 'Meter (optional)', border: OutlineInputBorder()),
            items: [
              const DropdownMenuItem(value: '', child: Text('Stateless recognition')),
              ..._meters.map((meter) => DropdownMenuItem(value: meter['id'] as String, child: Text('${meter['serial_number']}'))),
            ],
            onChanged: (value) => setState(() => _meterId = value),
          ),
          const SizedBox(height: 12),
          if (_cameraReady && _camera != null) AspectRatio(aspectRatio: _camera!.value.aspectRatio, child: CameraPreview(_camera!)),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: FilledButton.icon(onPressed: _openBackCamera, icon: const Icon(Icons.camera_rear), label: const Text('Mở camera sau'))),
            const SizedBox(width: 8),
            Expanded(child: FilledButton.icon(onPressed: _cameraReady ? _capture : null, icon: const Icon(Icons.camera), label: const Text('Chụp & OCR'))),
          ]),
          OutlinedButton.icon(onPressed: _busy ? null : _pickImage, icon: const Icon(Icons.photo_library), label: const Text('Chọn ảnh từ máy')),
          if (_image != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text('Ảnh: ${_image!.name}')),
          if (_busy) const Padding(padding: EdgeInsets.all(20), child: Center(child: CircularProgressIndicator())),
          if (_error != null) Card(color: Colors.red.shade50, child: Padding(padding: const EdgeInsets.all(12), child: Text(_error!, style: TextStyle(color: Colors.red.shade900)))),
          if (_result != null) ...[
            const SizedBox(height: 12),
            Text('Kết quả', style: Theme.of(context).textTheme.titleLarge),
            ...((_result!['crops'] as List<dynamic>? ?? []).map((crop) => Card(child: ListTile(title: Text(crop['text']?.toString().isNotEmpty == true ? crop['text'].toString() : '—'), subtitle: Text('Detector ${(crop['confidence'] * 100).toStringAsFixed(1)}% · OCR ${(crop['text_confidence'] * 100).toStringAsFixed(1)}%')))),
            SelectableText(const JsonEncoder.withIndent('  ').convert(_result)),
          ],
        ],
      ),
    );
  }
}

class ApiClient {
  static const baseUrl = String.fromEnvironment('WBRAIN_API_URL', defaultValue: 'http://10.0.2.2:18000');
  static const apiKey = String.fromEnvironment('WBRAIN_API_KEY', defaultValue: '');
  static Map<String, String> get headers => apiKey.isEmpty ? {} : {'X-API-Key': apiKey};
}
