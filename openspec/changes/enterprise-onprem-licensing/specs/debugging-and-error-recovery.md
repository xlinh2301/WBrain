# Debugging and Error Recovery

## ADDED Requirements

### Requirement: Actionable API errors
The API SHALL return a stable, safe error code and correlation/request ID for every handled error.

#### Scenario: Failed recognition
- **WHEN** image decoding, model inference, or a protected operation fails
- **THEN** the response includes a stable error code, request ID, and actionable operator-safe message without stack traces or secrets

### Requirement: Correlated structured logging
The runtime SHALL write a structured JSON event for each handled API error using the same request/correlation ID returned to the client.

#### Scenario: Customer support investigation
- **WHEN** a customer sends an error code and request ID to support
- **THEN** support can locate the matching server event without requiring the customer to provide credentials, model bytes, or raw images

### Requirement: Persistent host-mounted logs
The container deployment SHALL persist application logs to a configured host-mounted directory so logs survive container recreation or restart.

#### Scenario: Container restart
- **WHEN** the API container is restarted after an error
- **THEN** prior log files remain available in the host directory

### Requirement: Bounded log storage
The deployment SHALL enforce log rotation and retention limits by file size, file count, or age.

#### Scenario: Log disk pressure
- **WHEN** logs exceed the configured rotation threshold
- **THEN** older logs are rotated/removed according to policy and disk usage remains bounded

### Requirement: Sensitive-data redaction
Logs and diagnostic bundles SHALL redact credentials, tokens, license payloads, encryption keys, raw image data, model contents, and personal data.

#### Scenario: Exception contains secret material
- **WHEN** an exception or request contains a secret value
- **THEN** the persisted event contains only a redacted placeholder and safe error metadata

### Requirement: Support diagnostics bundle
An administrator-only diagnostics action MAY produce a time-bounded, redacted support bundle containing service versions, health state, configuration names without values, recent error summaries, and log metadata.

#### Scenario: Diagnostics export
- **WHEN** an authorized administrator requests diagnostics
- **THEN** a bundle is generated without secrets, raw customer images, model files, license keys, or unrestricted environment variables

### Requirement: Recovery guidance
The product SHALL document recovery actions for model load failure, license failure, dependency failure, disk-full conditions, container restart, and database/cache unavailability.

#### Scenario: Recoverable service failure
- **WHEN** a documented dependency becomes unavailable
- **THEN** the health endpoint identifies the affected dependency and the operator has a documented restart/restore/recovery procedure
