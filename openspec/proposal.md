# Proposal: WBrain Water-Meter OCR API

## Context
The input is a full water-meter image. A YOLO detector must localize the reading window, then EditCTC must recognize its text. The application must run on CPU and support browser upload/camera.

## Decision
Build a small FastAPI service with a browser demo. Model loading is isolated behind detector/recognizer adapters so exported ONNX models use ONNX Runtime, while YOLO `.pt` can use optional Ultralytics. Native Paddle checkpoints are not loaded directly by the web process until an export artifact is produced.

## Non-goals
Training, cloud deployment, authentication, multi-user storage, and GPU/TensorRT runtime are out of scope for the first increment. TensorRT is a future GPU profile, not a CPU runtime.

## Risks
ONNX output tensor layouts vary by export. The current generic YOLO ONNX adapter refuses unsafe unknown layouts rather than returning incorrect crops; export metadata or a known Ultralytics export must be supplied.
