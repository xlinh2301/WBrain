# Implementation checklist

- [x] Create CPU-only FastAPI service and static web demo
- [x] Add upload and browser camera flows
- [x] Add configurable YOLO/EditCTC adapters
- [x] Add input validation, health endpoint, and API schema
- [x] Document model paths and CPU runtime
- [ ] Export EditCTC Paddle checkpoint (`release_EditCTC/checkpoints/s8192/best_accuracy`) to ONNX and verify input/output names
- [x] Add reproducible YOLO `.pt` → ONNX export script and known output path
- [ ] Run the YOLO export and verify the generated artifact on the target machine
- [ ] Benchmark end-to-end latency on target CPU
- [ ] Add integration tests with a real meter image
- [x] Add Docker/Windows CPU deployment profile
