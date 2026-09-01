# OCR API

## Requirements

### Requirement: Image recognition API
The service SHALL accept JPEG, PNG, and WebP images at `POST /api/v1/recognize`.

#### Scenario: Valid image
- **WHEN** a valid image is submitted as multipart field `file`
- **THEN** the service returns a request ID, processing time, detected boxes, OCR text, and confidence scores

#### Scenario: Invalid input
- **WHEN** the request is not an image, cannot be decoded, or exceeds the configured size limit
- **THEN** the service returns HTTP 415, 400, or 413 respectively

### Requirement: CPU inference
The service SHALL load models once at startup and use CPU execution providers only.

#### Scenario: Healthy deployment
- **WHEN** the service starts with valid YOLO and EditCTC artifacts
- **THEN** `/api/v1/health` returns `status: ok`, `device: cpu`, and no model warning
