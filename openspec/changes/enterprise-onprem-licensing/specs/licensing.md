# Licensing

## ADDED Requirements

### Requirement: Signed license
The backend SHALL verify an Ed25519-signed license before enabling licensed functionality.

#### Scenario: Valid license
- **WHEN** the signature, product, schema, dates, and deployment binding are valid
- **THEN** the licensed features become available

#### Scenario: Invalid license
- **WHEN** the license is modified, signed by an unknown key, for another product, or bound to another deployment
- **THEN** startup or the protected operation is rejected without exposing key material

### Requirement: Time-limited usage
The license SHALL support `expires_at` and an explicitly configured expired behavior.

#### Scenario: Expired license
- **WHEN** current trusted UTC time is after the allowed expiry/grace period
- **THEN** the backend enforces the contracted behavior for the deployment

### Requirement: Offline activation
The product SHALL support challenge-file activation without sending a private signing key or master model key to the customer.

#### Scenario: Air-gapped activation
- **WHEN** the operator imports a valid vendor-signed license for the installation challenge
- **THEN** the deployment activates and validates locally

### Requirement: Backend enforcement
License checks SHALL be enforced in backend services and model initialization, not only in the frontend.

#### Scenario: Disabled feature API call
- **WHEN** a client calls an API for a feature not present in the license
- **THEN** the backend rejects the operation even if the client modifies the web UI
