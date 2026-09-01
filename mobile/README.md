# WBrain Mobile (Nylo)

Flutter mobile demo built on the Nylo 7.x application skeleton.

## Features

- Uses the rear camera explicitly with `CameraLensDirection.back`.
- Captures a meter image and sends multipart `POST /api/v1/recognize`.
- Selects an optional registered meter ID.
- Shows OCR text, detector/OCR confidence, and the raw JSON response.
- Falls back to selecting an image from the device.
- API key support through a compile-time define.

## Requirements

- Flutter 3.24+ / Dart version compatible with `nylo_framework` 7.x.
- Android Studio or Xcode for device builds.
- A reachable WBrain API backend.

## Run on Android emulator

Start the WBrain Docker API on the host first:

```powershell
cd ..
docker compose up -d
cd mobile
flutter pub get
flutter run --dart-define=WBRAIN_API_URL=http://10.0.2.2:18000
```

`10.0.2.2` maps from the Android emulator to the host machine. A physical
phone must use the host LAN IP, for example:

```bash
flutter run --dart-define=WBRAIN_API_URL=http://192.168.1.10:18000
```

For a remote/Vercel proxy, use HTTPS:

```bash
flutter run \
  --dart-define=WBRAIN_API_URL=https://wbrain-delta.vercel.app \
  --dart-define=WBRAIN_API_KEY=customer-api-key
```

The Vercel proxy requires `WBRAIN_BACKEND_URL` to be configured; otherwise it
returns `WBRAIN-DEPLOY-001` and does not run inference.

## Build

```bash
flutter build apk --release \
  --dart-define=WBRAIN_API_URL=https://your-api.example.com
```

The Android manifest requests camera and internet permissions. iOS includes
camera/photo-library usage descriptions. Local HTTP is enabled only for the
Android development path; production deployments should use HTTPS.

## Nylo source

The application skeleton is based on:

- https://github.com/nylo-core/nylo
- Nylo 7.x
- MIT license for the Nylo framework

Review all generated third-party notices before distributing a commercial app.
