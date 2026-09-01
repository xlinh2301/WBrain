# Model Protection

## ADDED Requirements

### Requirement: Encrypted model package
Proprietary model artifacts SHALL be distributable as encrypted packages with per-deployment keys.

#### Scenario: Valid model
- **WHEN** the license is valid and the model manifest checksum matches
- **THEN** the runtime obtains or unwraps the deployment key and loads the model

#### Scenario: Unauthorized model copy
- **WHEN** an encrypted model package is copied to another deployment without its valid license/key
- **THEN** the model cannot be initialized

### Requirement: Privileged-host limitation
Product documentation and commercial terms SHALL state that a customer Administrator/root can inspect runtime memory and binaries.

#### Scenario: High-confidentiality deployment
- **WHEN** absolute model confidentiality is required
- **THEN** the product SHALL use vendor-controlled inference or an approved confidential-computing design instead of relying only on on-prem encryption
