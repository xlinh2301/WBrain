# On-Premise Deployment

## ADDED Requirements

### Requirement: Offline-capable release

The product SHALL be installable in a customer network without runtime access to public registries or vendor services after images, dependencies, and license artifacts are imported.

#### Scenario: Air-gapped installation

- **WHEN** the operator imports signed images, checksums, configuration, and a valid license
- **THEN** the installer starts the stack without pulling from the Internet

### Requirement: Cross-platform installer paths

The installer SHALL accept Windows drive paths and POSIX paths without changing model identity or license behavior.

#### Scenario: Windows model path

- **WHEN** an operator configures a model path such as `E:\\models\\wbrain\\model.onnx` through PowerShell
- **THEN** the installer validates and mounts the resolved path without requiring manual slash conversion

#### Scenario: Linux model path

- **WHEN** an operator configures a model path such as `/opt/models/wbrain/model.onnx`
- **THEN** the installer validates and mounts the resolved path using the same artifact checks

### Requirement: Secure production defaults

The release SHALL reject demo credentials and SHALL expose only the reverse proxy externally by default.

#### Scenario: Production validation

- **WHEN** the operator uses a default password, enables mock auth, or exposes database/cache ports
- **THEN** validation fails with an actionable error before startup

### Requirement: Artifact integrity

The release SHALL include image digests, signatures, an SBOM, and model manifest checksums.

#### Scenario: Tampered artifact

- **WHEN** an image or model checksum/signature does not match the manifest
- **THEN** installation or model initialization stops
