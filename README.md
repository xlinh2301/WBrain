<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-CPU%20ready-2496ED.svg)](https://www.docker.com/)

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <h1 align="center">WBrain</h1>
  <p align="center">
    CPU-first water-meter detection and OCR API
    <br />
    <a href="https://github.com/xlinh2301/WBrain"><strong>Explore the repository »</strong></a>
    <br />
    <br />
    <a href="https://github.com/xlinh2301/WBrain/issues">Report Bug</a>
    ·
    <a href="https://github.com/xlinh2301/WBrain/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li><a href="#getting-started">Getting Started</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#on-premise-deployment">On-Premise Deployment</a></li>
    <li><a href="#debugging-and-customer-support">Debugging and Customer Support</a></li>
    <li><a href="#security-model">Security Model</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

## About The Project

WBrain reads water-meter images through the following pipeline:

```text
Original meter image
        ↓
YOLO11m OBB detector
        ↓
Meter/display crop
        ↓
EditCTC OCR
        ↓
FastAPI response and web visualization
```

The current runtime profile is CPU-first and is intended for local development,
Docker deployment, and future customer on-premise releases. The API accepts an
image upload, detects relevant regions, recognizes text, and returns bounding
boxes, confidence scores, OCR text, processing time, and a request ID.

The repository also contains the OpenSpec documentation for versioned release
management, customer licensing, artifact protection, and operational recovery.
See [`openspec/`](openspec/) for the implementation plan and acceptance criteria.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Built With

- [![Python][Python-shield]][Python-url]
- [![FastAPI][FastAPI-shield]][FastAPI-url]
- [![ONNX Runtime][ONNX-shield]][ONNX-url]
- [![OpenCV][OpenCV-shield]][OpenCV-url]
- [![PaddlePaddle][Paddle-shield]][Paddle-url]
- [![Docker][Docker-shield]][Docker-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Prerequisites

For local development:

- Python 3.11 or newer
- pip
- A YOLO detector model and an EditCTC OCR model

For Docker deployment:

- Docker Desktop or Docker Engine with Compose v2
- Permission to mount the directory containing the model files
- CPU support; GPU/TensorRT is not required for the current profile

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/xlinh2301/WBrain.git
   cd WBrain
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   Linux/macOS:

   ```bash
   source .venv/bin/activate
   ```

3. Install runtime dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   Install test dependencies when developing:

   ```bash
   pip install -r requirements-dev.txt
   ```

4. Configure model paths in `.env` or through environment variables:

   ```dotenv
   DEVICE=cpu
   YOLO_MODEL_PATH=/path/to/best.onnx
   EDITCTC_MODEL_PATH=/path/to/best_accuracy
   EDITCTC_CONFIG_PATH=/path/to/config.yml
   EDITCTC_DICT_PATH=/path/to/ppocrv6_dict.txt
   EDITCTC_CODE_DIR=/path/to/editctc/code
   ```

5. Start the API:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

Open <http://127.0.0.1:8000> for the web demo or
<http://127.0.0.1:8000/docs> for the OpenAPI documentation.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

### Web demo

Open <http://127.0.0.1:8000> and either upload an image or use the camera
capture control. The result canvas displays the detected bounding boxes, OCR
text, and detector confidence.

### API

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Recognize an image:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recognize \
  -F "file=@./meter.jpg"
```

Example successful response:

```json
{
  "request_id": "4a65f9a0-3fb3-4c4e-b9b7-6d7a5e7c1f32",
  "processing_ms": 644.46,
  "crops": [
    {
      "box": [120, 80, 640, 260],
      "confidence": 0.93,
      "text": "012345",
      "text_confidence": 0.91
    }
  ],
  "warning": null
}
```

Every response includes `X-Request-ID`. A client may provide its own
`X-Request-ID` to correlate a support case across requests.

### Run tests

```bash
pytest
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## On-Premise Deployment

The default Compose file mounts models read-only from the host and keeps model
binaries outside the generic runtime image:

```bash
docker compose up --build -d
```

The service is available at <http://127.0.0.1:8000>. Update the host model paths
in [`docker-compose.yml`](docker-compose.yml) for each deployment. The current
example uses:

- YOLO ONNX: `/models/yolo/train/weights/best.onnx`
- EditCTC checkpoint: `/models/editctc/checkpoint/best_accuracy`
- EditCTC config: `/models/editctc/checkpoint/config.yml`
- EditCTC code and dictionary: `/models/editctc/code`

### Release workflow

The planned customer release workflow is:

```text
Git source
  ↓ immutable tag vX.Y.Z
Dockerfile release build
  ↓
ignored release/ directory
  ├── manifest.json
  ├── checksums.sha256
  ├── sbom.spdx.json
  ├── images/
  └── customer-package/
  ↓
versioned Docker Hub image and customer license
```

Generated customer artifacts belong in `release/` and must not be committed.
Version notes belong in `release-notes/vX.Y.Z.md`.

The license and encrypted-artifact runtime implementation is tracked in
[`openspec/changes/enterprise-onprem-licensing/`](openspec/changes/enterprise-onprem-licensing/).
Do not distribute production customer artifacts until the license verification,
key management, artifact encryption, and release verification tasks are complete.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Debugging and Customer Support

Application logs are written as structured JSON to:

```text
/var/log/wbrain/app.log
```

Compose persists this directory to `./logs` by default. Configure a customer-owned
persistent location before deployment:

Linux:

```bash
WBRAIN_LOG_DIR=/srv/wbrain/logs docker compose up -d
```

Windows PowerShell:

```powershell
$env:WBRAIN_LOG_DIR = 'D:\WBrain\logs'
docker compose up -d
```

Logs use rotation and retention limits. Do not send raw images, model files,
license files, keys, or unrestricted environment variables to support.

Generate a redacted diagnostics bundle:

Linux:

```bash
scripts/collect-diagnostics.sh
```

Windows PowerShell:

```powershell
.\scripts\collect-diagnostics.ps1
```

The API returns safe error objects containing an error code, operator-safe
message, and correlation ID. Provide those values and the relevant timestamp
to support.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Security Model

The on-premise protection design is documented in OpenSpec and includes:

- Ed25519-signed customer licenses with expiry and deployment binding.
- AES-256-GCM as the preferred new artifact encryption format.
- Fernet compatibility where required by an existing integration.
- Per-customer and per-deployment key material.
- Read-only model mounts in the current Docker profile.
- No vendor private signing key in the runtime image or Git repository.
- Redacted logs and support diagnostics.

Encryption and obfuscation cannot provide absolute secrecy from a customer
Administrator/root who controls the host, container runtime, or process memory.
For that threat model, use vendor-controlled inference or confidential computing.
This limitation is an explicit product constraint, not a claim that encrypted
`.so` files alone prevent model extraction.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Roadmap

- [ ] Implement Ed25519 license verification and expiry enforcement.
- [ ] Implement offline activation and deployment fingerprint binding.
- [ ] Implement AES-GCM/Fernet artifact packaging and secure key release.
- [ ] Add release build scripts, manifest, checksums, SBOM, and image signing.
- [ ] Validate the detector and OCR against clean original meter images.
- [ ] Add CI quality, security, and release gates.
- [ ] Add Kubernetes/Helm deployment for supported customers.
- [ ] Add production authentication and administrator-only diagnostics access.

See the [open issues](https://github.com/xlinh2301/WBrain/issues) for proposed
features and known issues.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contributing

Contributions are welcome. Before making a significant change:

1. Review [`AGENTS.md`](AGENTS.md) for repository engineering rules.
2. Review the applicable OpenSpec change and acceptance criteria.
3. Add or update tests.
4. Run formatting, tests, and Docker validation where applicable.
5. Keep customer artifacts, model files, licenses, and keys out of Git.

For a standard contribution:

1. Fork the project.
2. Create a feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes.
4. Push the branch and open a pull request.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License

The repository currently does not include a finalized top-level license file.
Licensing is being finalized alongside the on-premise commercial distribution
plan. Before public redistribution, review the applicable licenses for WBrain,
YOLO/Ultralytics, PaddlePaddle, EditCTC, ONNX Runtime, and all third-party
components. Preserve upstream notices and Apache 2.0 rights where applicable.

Commercial customer licensing, expiry, activation, and artifact distribution
requirements are specified in
[`openspec/changes/enterprise-onprem-licensing/`](openspec/changes/enterprise-onprem-licensing/).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contact

- Project: [https://github.com/xlinh2301/WBrain](https://github.com/xlinh2301/WBrain)
- Issues: [https://github.com/xlinh2301/WBrain/issues](https://github.com/xlinh2301/WBrain/issues)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Acknowledgments

- [Best-README-Template](https://github.com/othneildrew/Best-README-Template)
- [FastAPI](https://fastapi.tiangolo.com/)
- [ONNX Runtime](https://onnxruntime.ai/)
- [OpenCV](https://opencv.org/)
- [PaddlePaddle](https://www.paddlepaddle.org.cn/)
- [OpenSpec](https://github.com/Fission-AI/openspec)
- [spec-writer](https://github.com/dannwaneri/spec-writer)
- [agent-skills](https://github.com/addyosmani/agent-skills)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[Python-shield]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[FastAPI-shield]: https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white
[FastAPI-url]: https://fastapi.tiangolo.com/
[ONNX-shield]: https://img.shields.io/badge/ONNX%20Runtime-005CED?style=for-the-badge&logo=onnx&logoColor=white
[ONNX-url]: https://onnxruntime.ai/
[OpenCV-shield]: https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white
[OpenCV-url]: https://opencv.org/
[Paddle-shield]: https://img.shields.io/badge/PaddlePaddle-0081A5?style=for-the-badge&logo=paddlepaddle&logoColor=white
[Paddle-url]: https://www.paddlepaddle.org.cn/
[Docker-shield]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/
