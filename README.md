# WBrain

CPU-first water-meter reading application: original meter image -> YOLO crop -> EditCTC text recognition.

## Quick start

```bash
python -m venv .venv
.venv\\Scripts\\activate       # Windows
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Set model paths in `.env`. YOLO ONNX is loaded by ONNX Runtime; `.pt` requires the optional `ultralytics` package. EditCTC supports ONNX; the supplied Paddle checkpoint (`release_EditCTC/checkpoints/s8192/best_accuracy`) is supported by the local CPU fallback. The default Docker image is ONNX-only to avoid shipping PyTorch/Paddle payloads.

## Docker CPU

Docker Desktop must have access to the `E:` drive. Export the detector once (outside the runtime image):

```bash
pip install ultralytics
python scripts/export_yolo.py --weights E:\\workspace_research\\workspace5\\workdir_text_det\\outputs\\detect_yolo11m\\train\\weights\\best.pt
```

This creates `best.onnx` beside `best.pt`. Adjust the two host mounts if needed, then run:

```bash
docker compose up --build
```

The service is available at http://127.0.0.1:8000. Model binaries stay on the host and are mounted read-only; they are not included in the image. TensorRT is deliberately not enabled in this profile because it requires a CUDA-capable GPU.

API: `POST /api/v1/recognize` with multipart field `file`; health: `GET /api/v1/health`; OpenAPI: `/docs`.

## Docker CPU

Export or copy models into `models/` and run `docker compose up --build`. See `openspec/container.md` for the ONNX and native Paddle mount layouts.

See `openspec/` for the SDD proposal, specification, and implementation checklist.
