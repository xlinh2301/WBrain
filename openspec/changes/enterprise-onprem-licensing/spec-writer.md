# Enterprise On-Premise Release, Licensing, and Artifact Protection

## SECTION 1: SPEC

### One-line purpose

Customers can install a versioned on-premise WBrain product from an approved release package and use licensed features only within the commercial entitlement period.

### Users and use cases

- As a release engineer, I want to build a customer release from an immutable source version so that every shipped artifact is traceable and reproducible.
- As a customer operator, I want to install the product in an internet-connected or air-gapped environment so that customer data remains inside my infrastructure.
- As a customer operator, I want to activate a deployment with a license file so that the product can run without exposing vendor private keys.
- As a customer administrator, I want to renew or replace an expired license so that service continuity follows the commercial agreement.
- As a vendor, I want to limit features and model access by customer/deployment so that a copied package cannot be reused as another customer deployment.
- As a vendor, I want each version to document its changes and exact artifacts so that support and rollback are predictable.

### Requirements

1. The source of truth for every release SHALL be an immutable version tag in the source repository.
2. A release SHALL be buildable from the tagged source and its declared build inputs without requiring source files from an untracked local directory.
3. Generated customer artifacts SHALL be written under `release/` and SHALL NOT be committed to the source repository.
4. Runtime images SHALL be published with immutable version tags and recorded content digests.
5. A customer release SHALL include installation instructions, image digests, checksums, a software bill of materials, and a customer-specific license artifact.
6. The product SHALL support a license with customer identity, deployment identity, enabled features, model package identity, issue time, expiry time, and optional deployment binding.
7. A license SHALL be cryptographically authentic and tamper-evident.
8. The product SHALL support offline activation for a customer environment that cannot contact vendor services.
9. The product SHALL enforce license state in backend operations and model initialization, not only in the user interface.
10. The product SHALL provide an explicit behavior for valid, grace-period, expired, revoked, invalid, and wrong-deployment states.
11. Proprietary model and native-library artifacts SHALL be encrypted before customer distribution.
12. A copied encrypted artifact SHALL NOT initialize on another deployment without the matching license and key material.
13. Release notes SHALL be committed for every version under `release-notes/vX.Y.Z.md`.
14. Production defaults SHALL not contain demo passwords, mock authentication, reusable vendor keys, or unrestricted debug access.
15. The distribution SHALL preserve all applicable upstream and third-party license obligations.
16. Documentation SHALL state that a customer Administrator/root can inspect runtime memory and loaded code; no absolute secrecy claim is allowed.
17. The API and runtime SHALL produce actionable, correlation-friendly diagnostics for debugging and error recovery.
18. Container logs SHALL be persisted to a host-mounted customer log directory with rotation and retention controls.
19. Logs SHALL redact licenses, encryption keys, credentials, tokens, model contents, and sensitive customer image data.

### Edge cases

- **Release directory is accidentally staged:** The build MUST fail or Git MUST ignore the directory so generated customer artifacts are not published as source.
- **Image tag is reused:** The release process MUST reject mutable/reused version tags and record the digest used by the customer package.
- **License file is modified:** Activation MUST fail with an actionable invalid-signature result and MUST NOT reveal key material.
- **License is copied to another host:** Activation MUST fail when deployment binding is enabled and the fingerprint does not match.
- **Customer has no network access:** Offline challenge/license import MUST activate a valid deployment without contacting a vendor endpoint.
- **License expires during operation:** The backend MUST apply the configured contract behavior after the grace period rather than relying on frontend state.
- **System clock moves backwards:** The product MUST detect a material rollback using the last successful validation state and expose a support-recovery path.
- **Encrypted `.so` is unavailable or corrupted:** Model/library initialization MUST stop safely, log a non-secret diagnostic, and leave no plaintext artifact behind after failure.
- **Windows path is supplied:** PowerShell installation MUST accept drive-letter paths without manual slash conversion.
- **Linux path is supplied:** Shell installation MUST accept POSIX paths with the same checksum and artifact identity.
- **Customer requires protection from host administrators:** The deployment MUST recommend vendor-controlled inference or confidential computing instead of claiming encryption alone is sufficient.
- **Upstream license conflicts with commercial terms:** The release MUST preserve upstream Apache 2.0 rights and separate vendor-owned commercial additions.
- **Customer reports an API failure:** The response MUST include a safe error code and correlation/request ID; the detailed server log MUST contain enough non-secret context to reproduce and localize the failure.
- **Container restarts:** Logs MUST remain available through the host-mounted directory and MUST not disappear with the container filesystem.
- **Log disk exhaustion:** Rotation/retention MUST bound disk usage and emit a health/alert diagnostic before service failure.
- **Sensitive data reaches an exception:** Redaction MUST remove secrets and image/model payloads before writing the log record.

### Acceptance criteria

```text
Given a clean checkout of a release tag
When the release build is executed
Then the generated release manifest identifies the source tag, image digests, model IDs, checksums, and version
```

```text
Given a generated release directory
When Git status and the release package are inspected
Then release artifacts are not tracked and the package contains no vendor private key
```

```text
Given a valid customer license
When the deployment starts with matching artifacts and deployment identity
Then the licensed backend features and model initialization are enabled
```

```text
Given a modified or incorrectly signed license
When the deployment starts or a protected API is called
Then the operation is rejected with an invalid-license state
```

```text
Given an expired license after its configured grace period
When a protected API or model initialization is requested
Then the configured expired behavior is enforced by the backend
```

```text
Given an air-gapped host and a valid offline activation file
When the operator imports the file
Then the deployment activates without an outbound network request
```

```text
Given an encrypted model copied to a second deployment
When the second deployment attempts model initialization without its matching key/license
Then model initialization fails
```

```text
Given a customer release version `v1.2.3`
When a reviewer checks the repository
Then `release-notes/v1.2.3.md` documents changes, runtime/model versions, security changes, migrations, and known limitations
```

```text
Given a Windows PowerShell installation path and a Linux installation path
When each installer validates the same release manifest
Then both installers produce the same artifact identity and checksum result
```

```text
Given a request that fails inside the API
When the customer receives the error response
Then it contains a safe error code and correlation ID, while the mounted log contains a matching non-secret structured event
```

```text
Given a running container that is restarted
When an operator inspects the configured host log directory
Then logs from before the restart remain available and rotated files stay within the configured retention limit
```

## SECTION 2: PLAN

### Stack and architecture

- Source repository: Git with immutable semantic tags.
- Build: Dockerfile release build using Docker BuildKit; customer output is generated locally.
- Runtime: Docker Compose first, optional Kubernetes/Helm later.
- API: current FastAPI CPU OCR service; SkillHub-derived components remain separately versioned when integrated.
- Inference: YOLO11m OBB ONNX with ONNX Runtime CPU and EditCTC `s1024` Paddle CPU fallback.
- Licensing: a vendor-owned license service/signing workstation issues signed licenses; runtime embeds only the verification public key.
- License signature: Ed25519 over canonical JSON.
- Artifact encryption: AES-256-GCM is preferred for model packages; Fernet MAY be used where compatibility requires it. Encryption keys are per customer/deployment/package and are never stored in Git or generic images.
- Offline key storage: wrap the package key for the deployment TPM/customer public key; define rehost/recovery policy before implementation.
- Native library loader: decrypt `.so` only after license validation, load from a protected temporary or memory-backed location where supported, and clean up plaintext files.
- Distribution: publish generic versioned images to Docker Hub; distribute customer-specific license/key material through a private release package or private repository.

### Data model changes

- `License`: license ID, product, schema version, customer ID, deployment ID, issue time, expiry time, grace time, state, enabled features, max instances, model package ID, fingerprint, signature.
- `ActivationChallenge`: challenge ID, nonce, product/version, deployment fingerprint, created time, consumed time.
- `ArtifactManifest`: version, source commit/tag, image name/digest, artifact ID, algorithm, checksum, size, runtime contract.
- `LicenseAuditEvent`: event ID, deployment ID, license ID, event type, timestamp, result, non-secret diagnostic.
- `release-notes/vX.Y.Z.md`: committed version documentation; `release/manifest.json` is generated and ignored.
- `ApiErrorEvent`: request ID, error code, operation, service/version, timestamp, duration, sanitized cause category, and optional stack trace controlled by environment.
- `LogPolicy`: host directory, max file size, max retained files/age, redaction mode, and customer support bundle policy.

### API contracts

- `POST /api/v1/license/activate`
  - Input: signed license package and deployment challenge metadata.
  - Output: activation state, expiry, enabled feature IDs.
  - Errors: invalid signature, expired, wrong deployment, unsupported schema.
- `GET /api/v1/license/status`
  - Output: non-sensitive state, expiry, grace period, enabled features, product version.
- `POST /api/v1/license/challenge`
  - Output: offline activation challenge with nonce and normalized fingerprint.
- `POST /api/v1/license/renew`
  - Input: replacement signed license.
  - Output: new state and expiry.
- Protected OCR/model endpoints
  - Must reject requests when `ocr_model` is absent, expired, invalid, or not bound to the deployment.
- `scripts/build-release.ps1` and `scripts/build-release.sh`
  - Input: source version, customer ID, license input, model package input.
  - Output: ignored `release/` directory with manifest, checksums, image references, and customer package.
- `GET /api/v1/support/diagnostics` (admin-only, optional)
  - Output: redacted service/model/license state and recent error summary; never raw logs, keys, image bytes, or credentials.
  - Errors: unauthorized, license-disabled, or diagnostics-disabled.

### Patterns to follow

- Keep transport validation in API handlers and license/business decisions in a dedicated backend service.
- Keep source artifacts, generated release artifacts, and customer secrets in separate locations.
- Use explicit artifact manifests rather than directory globbing for release contents.
- Use immutable tags and digests; never use `latest` in a customer manifest.
- Keep license private-key operations outside the customer runtime.
- Preserve upstream Apache 2.0 notices and record modified files.

### Testing strategy

- Unit tests: canonical license serialization, signature verification, expiry states, feature checks, fingerprint matching, clock rollback detection, Fernet/AES-GCM encrypt/decrypt, checksum verification.
- Integration tests: startup with valid/invalid/expired license, model initialization, protected API rejection, offline import, renewal, audit events.
- Release tests: clean tagged checkout build, ignored `release/`, image digest manifest, no private key/plaintext model, SBOM/checksum generation.
- Platform tests: Windows PowerShell and Linux shell path handling; Docker Compose startup; optional Kubernetes manifest validation.
- Security tests: tampered license, copied license, copied encrypted model, modified image, debug endpoint exposure, default-secret rejection.
- Performance tests: OCR latency and memory before/after artifact encryption; encryption MUST not add work to every inference request.
- Debugging/error-recovery tests: stable error codes, correlation IDs, exception-to-log mapping, redaction, log persistence across restart, rotation, retention, disk-full behavior, and support bundle generation.

### Security and performance constraints

- The runtime MUST execute on CPU in the supported profile.
- Private signing keys and master encryption keys MUST never enter customer images, Git, Dockerfile arguments, logs, or release metadata.
- The backend MUST verify license state before model key release and model initialization.
- Encrypted model decryption SHOULD occur once at startup or controlled reload, not per request.
- License status endpoints MUST not expose raw fingerprints, keys, or customer secrets.
- Customer database/cache ports MUST remain private by default.
- Production containers SHOULD run non-root with read-only filesystems where compatible.
- Image tags MUST be immutable in the release manifest and verified by digest.
- No design claim may promise protection against a privileged customer Administrator/root.

## SECTION 3: TASKS

## Task 1: Normalize release repository layout

**What to build:** Add release Dockerfile conventions, ignored `release/`, committed `release-notes/`, semantic-version rules, and a release manifest schema.

**Files likely affected:** `.gitignore`, `Dockerfile`, `release-notes/`, `scripts/build-release.ps1`, `scripts/build-release.sh`, `docs/`.

**Acceptance criteria:**

1. `release/` is ignored and cannot appear in a clean release commit.
2. A release manifest records source tag, version, image digests, artifact IDs, and checksums.
3. Windows and Linux build commands produce the same manifest schema.

**Dependencies:** none

## Task 2: Implement signed license verification

**What to build:** Add license schema, canonical serialization, Ed25519 verification, expiry states, deployment binding, and non-sensitive status output.

**Files likely affected:** `app/license.py`, `app/config.py`, `app/main.py`, `tests/test_license.py`.

**Acceptance criteria:**

1. Valid licenses pass signature/date/product validation.
2. Modified, expired, wrong-product, and wrong-deployment licenses return distinct rejected states.
3. No private key or raw fingerprint is returned by the API.

**Dependencies:** Task 1

## Task 3: Add backend feature enforcement

**What to build:** Gate model initialization and protected OCR operations with a license guard, including grace/expired behavior and audit-safe diagnostics.

**Files likely affected:** `app/main.py`, `app/pipeline.py`, `app/license.py`, `tests/test_api.py`.

**Acceptance criteria:**

1. OCR returns a protected-feature error when the license is expired or lacks `ocr_model`.
2. Valid license status allows the configured model to initialize.
3. License status is checked in backend code even if the frontend is bypassed.

**Dependencies:** Task 2

## Task 4: Build encrypted artifact packaging

**What to build:** Add an explicit encrypted model/native-library package format, manifest checksum verification, key wrapping interface, and cleanup behavior.

**Files likely affected:** `scripts/package-artifacts.py`, `app/artifacts.py`, `tests/test_artifacts.py`, `openspec/`.

**Acceptance criteria:**

1. Plaintext model input produces an encrypted artifact and manifest without leaving a release plaintext copy.
2. A wrong key or checksum prevents initialization.
3. Encryption keys do not appear in logs, Git, image layers, or generated public metadata.

**Dependencies:** Task 2

## Task 5: Add `.so` protected loader

**What to build:** Load encrypted native libraries only after license validation, using protected temporary or memory-backed loading where supported and cleanup on failure.

**Files likely affected:** `app/native_loader.py`, native runtime package, platform scripts, tests.

**Acceptance criteria:**

1. A valid license loads the expected native artifact.
2. Invalid license/key does not load the artifact.
3. Failed loading removes temporary plaintext output and emits only a non-secret diagnostic.

**Dependencies:** Task 4

## Task 6: Create customer release and Docker Hub publication workflow

**What to build:** Build tagged source into versioned images, generate customer package under ignored `release/`, publish approved images, and record digests/checksums/SBOM.

**Files likely affected:** `.github/workflows/`, `scripts/build-release.*`, `scripts/publish-release.*`, `release-notes/`.

**Acceptance criteria:**

1. A tagged build generates a complete customer package without committing `release/`.
2. Docker Hub image tags and digests are recorded in the manifest.
3. The workflow fails when required license, checksum, or SBOM artifacts are missing.

**Dependencies:** Tasks 1 and 4

## Task 7: Harden and validate on-prem deployment

**What to build:** Remove production demo defaults, verify secrets, restrict service exposure, add backup/restore and Windows/Linux installer checks.

**Files likely affected:** `docker-compose.yml`, `.env*`, `scripts/install.*`, `scripts/validate-release.*`, deployment docs.

**Acceptance criteria:**

1. Production validation rejects demo passwords, mock auth, missing license, and missing required secrets.
2. PostgreSQL and Redis are private by default.
3. Windows PowerShell and Linux installation tests pass with equivalent artifacts.

**Dependencies:** Tasks 2 and 6

## Task 8: Add debugging and error recovery observability

**What to build:** Follow `debugging-and-error-recovery` and `observability-and-instrumentation` workflows to add stable API error codes, correlation IDs, structured JSON logs, host-mounted container logs, rotation/retention, redaction, and a safe customer diagnostics bundle.

**Files likely affected:** `app/errors.py`, `app/logging.py`, `app/main.py`, `Dockerfile`, `docker-compose.yml`, `scripts/collect-diagnostics.*`, `tests/test_errors.py`, `tests/test_logging.py`.

**Acceptance criteria:**

1. Every handled API error returns a safe error code and request/correlation ID, and a matching structured log event is written.
2. Container logs persist under the configured host-mounted log directory across container restart and are bounded by rotation/retention settings.
3. Logs and diagnostics contain no credentials, license/encryption keys, tokens, model contents, or raw customer image data.

**Dependencies:** Tasks 2 and 7

## Task 9: Version release notes and customer handoff

**What to build:** Establish the per-version release note template and document upgrade, rollback, license renewal, rehost, and privileged-host limitations.

**Files likely affected:** `release-notes/vX.Y.Z.md`, `INSTALL.md`, `UPGRADE.md`, `SECURITY.md`.

**Acceptance criteria:**

1. Every release tag has a matching committed release note.
2. Customer handoff includes exact image/model/checksum/license references.
3. Renewal, expiry, recovery, and rollback procedures are documented.

**Dependencies:** Task 6

### Review checkpoint

Before implementation, approve the expiry behavior, online/offline policy, TPM/rehost policy, Docker Hub visibility, Fernet versus AES-GCM decision, and whether vendor-controlled inference is required for high-value models.

## Assumptions to review

1. The customer receives runtime images and a private release package, not the complete proprietary source — Impact: HIGH
   Correct this if: the commercial agreement requires source delivery or source escrow.

2. Docker Hub is an approved distribution channel for generic versioned images — Impact: HIGH
   Correct this if: customer policy requires a private registry or offline image tar files only.

3. Customer-specific licenses are distributed separately from reusable generic images — Impact: HIGH
   Correct this if: each customer receives a private image repository/tag.

4. Offline activation is required — Impact: HIGH
   Correct this if: every deployment can maintain a connection to the vendor license service.

5. TPM 2.0 or a customer public key is available for offline key wrapping — Impact: HIGH
   Correct this if: customer hardware is legacy or VM-only.

6. License expiry may disable OCR while leaving administration/read-only functions available — Impact: HIGH
   Correct this if: expired licenses must hard-stop the entire platform.

7. AES-256-GCM is acceptable for new artifacts and Fernet is retained only for compatibility — Impact: MEDIUM
   Correct this if: Fernet is a contractual or interoperability requirement.

8. `.so` artifacts are Linux native libraries; Windows deployments may require an equivalent DLL loader — Impact: MEDIUM
   Correct this if: the product is Linux-only.

9. Docker Compose is the first supported customer deployment and Kubernetes is follow-up — Impact: MEDIUM
   Correct this if: Kubernetes is mandatory from the first release.

10. Upstream SkillHub remains Apache 2.0 and vendor licensing applies only to vendor-owned additions and commercial usage terms — Impact: HIGH
    Correct this if: legal counsel requires a different product separation or licensing structure.
