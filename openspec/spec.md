# Specification

## Functional requirements
- Accept JPEG/PNG/WebP image uploads at `POST /api/v1/recognize`.
- Reject non-images with 415, malformed images with 400, and payloads over the configured limit with 413.
- Detect one or more reading regions and return `box`, detector confidence, OCR text, and OCR confidence.
- Serve a camera-capable web demo at `/`.
- Expose `/api/v1/health` and generated OpenAPI docs.
- Use CPU execution providers only.

## Quality requirements
- Model files and paths are configuration, never hardcoded into application logic.
- Model loading happens once at startup.
- Unconfigured models produce an explicit health/API warning and a deterministic full-image fallback.
- Unknown ONNX detector layouts fail loudly with an actionable error.

## API contract
`RecognitionResponse = {request_id, processing_ms, crops[], warning?}`.
Each crop is `{box:[x1,y1,x2,y2], confidence, text, text_confidence}`.
