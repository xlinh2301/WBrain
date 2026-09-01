# API-first platform specification

## Requirements

### Requirement: Meter registry
The API SHALL create, list, and retrieve meters using stable IDs and unique
serial numbers.

#### Scenario: Create a meter
- **WHEN** an authenticated operator submits a serial number and meter metadata
- **THEN** the API returns the meter ID and persisted metadata

#### Scenario: Duplicate serial number
- **WHEN** a serial number already exists
- **THEN** the API returns a safe conflict error without creating a duplicate

### Requirement: Persistent recognition
The recognition API SHALL optionally associate a request with a meter and persist
image metadata, detections, OCR text, model version, processing time, and result
status.

#### Scenario: Recognize for a registered meter
- **WHEN** a valid image is submitted with `meter_id`
- **THEN** the response is returned immediately and a reading record is available
  through the meter history API

#### Scenario: Privacy-preserving default
- **WHEN** image storage is not explicitly enabled
- **THEN** raw image bytes are not persisted; only size, hash, content type, and
  processing metadata are retained

### Requirement: Reading retrieval
The API SHALL retrieve meter readings in reverse chronological order and support
bounded pagination.

#### Scenario: Meter history
- **WHEN** an operator requests a meter's readings
- **THEN** the API returns readings with OCR text, value, confidence, status,
  model version, and timestamps

### Requirement: Reading validation
The backend SHALL mark low-confidence, decreasing, or malformed readings for
manual review instead of silently treating them as valid.

#### Scenario: Anomalous reading
- **WHEN** a reading is lower than the previous numeric reading or confidence is
  below the configured threshold
- **THEN** its status is `review_required` and a review task is created

### Requirement: Manual review
The API SHALL list pending review tasks and allow an operator to approve or
correct a reading with an audit event.

#### Scenario: Correct a reading
- **WHEN** a reviewer submits a corrected value and reason
- **THEN** the reading is updated, the task is closed, and the audit event records
  the before/after values and request ID

### Requirement: Provenance and audit
Every persisted reading SHALL identify the model version and every mutation SHALL
produce a non-secret audit event.

#### Scenario: Support investigation
- **WHEN** support receives a reading ID or request ID
- **THEN** the operator can retrieve safe provenance and audit metadata without
  exposing keys, license payloads, or raw image bytes

### Requirement: API compatibility
The existing `POST /api/v1/recognize` response SHALL remain backward compatible;
new fields are optional request fields and new resource endpoints are versioned
under `/api/v1`.

### Requirement: SDK readiness
The API SHALL expose an OpenAPI document with stable schemas, error codes, and
request IDs so a typed SDK can be generated in a later change.
