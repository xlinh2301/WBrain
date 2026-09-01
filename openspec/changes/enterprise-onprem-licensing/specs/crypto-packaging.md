# Cryptographic Packaging

## ADDED Requirements

### Requirement: Fernet artifact encryption
Proprietary models and native `.so` artifacts SHALL be encrypted at rest using Fernet with a unique key per customer/deployment/package.

#### Scenario: Package creation
- **WHEN** the release tool packages a model or `.so`
- **THEN** it writes an encrypted artifact, records its SHA-256 and package ID in the manifest, and does not write the plaintext artifact to `release/`

#### Scenario: Package verification
- **WHEN** the runtime receives a license and encrypted artifact
- **THEN** it verifies the license, unwraps or obtains the Fernet key, decrypts the artifact, and verifies the plaintext checksum before loading

### Requirement: Key separation
Fernet keys SHALL NOT be stored in Git, generic Docker images, Dockerfile arguments, public Docker Hub metadata, or customer logs.

#### Scenario: Generic image inspection
- **WHEN** an operator inspects a generic runtime image
- **THEN** no reusable customer Fernet key, license signing private key, or plaintext proprietary model is present

### Requirement: Native library loading
The runtime SHALL load encrypted `.so` artifacts only through a controlled loader that limits permissions, removes temporary plaintext files after loading where supported, and records failures without logging key material.

#### Scenario: Linux native library
- **WHEN** a valid license enables a native `.so`
- **THEN** the loader decrypts it into a protected temporary location or memory-backed file, loads it, and cleans up the decrypted artifact after initialization

### Requirement: Cryptographic limitation disclosure
Documentation SHALL state that Fernet protects artifacts at rest but cannot prevent a privileged customer administrator from inspecting decrypted memory, loaded native libraries, or patched runtime code.

#### Scenario: High-value model
- **WHEN** the customer requires protection against host administrators
- **THEN** the deployment uses vendor-controlled inference or approved confidential computing rather than relying only on Fernet encryption
