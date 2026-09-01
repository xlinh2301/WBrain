# Design: Enterprise On-Premise Packaging and Licensing

## Source, build, and distribution flow

```text
Git source + Dockerfiles
        |
        v
Immutable Git tag vX.Y.Z
        |
        v
Release build (Docker BuildKit)
        |
        +--> local release/ (ignored, never pushed to Git)
        |      images, license, manifest, checksums, SBOM
        |
        +--> Docker Hub (versioned images + digests)
        |
        +--> release-notes/vX.Y.Z.md (committed)
```

The Git tag is the source of truth. `release/` is generated output and MUST be ignored by Git. Customer-specific licenses MUST be injected during release/package generation and MUST NOT be baked into a reusable generic image. Docker Hub publication records image digests in the release manifest.

## Architecture

```text
Customer host
  Reverse proxy/Web UI
          |
          v
  Backend API ---- PostgreSQL
       |           Redis
       +----------- Object storage
       |
       +----------- CPU OCR/model runtime

Vendor systems
  License signing service
  Artifact registry
  Image signing/SBOM pipeline
```

## License verification

Use Ed25519 signatures over canonical JSON. The runtime embeds only the vendor public key. The private signing key stays in a vendor-controlled signing service or offline signing workstation.

Required claims:

- `license_id`, `product`, `schema_version`
- `customer_id`, `deployment_id`
- `issued_at`, `expires_at`, optional `grace_until`
- feature list and `max_nodes`
- model package ID/version
- optional normalized deployment fingerprint

The backend exposes a `LicenseGuard` and feature-level authorization. Checks occur at startup, protected requests, model initialization, and scheduled revalidation. Expired behavior is an explicit product decision: hard stop, read-only, feature disablement, or grace period.

## Activation

Online activation sends a nonce and normalized installation fingerprint to the vendor activation API and receives a signed license. Offline activation exports a challenge file, receives a signed license through an approved channel, and imports it locally. No private key or master model key is sent to the customer.

## Artifact encryption and model protection

Use Fernet for at-rest encryption of customer model packages and native `.so` artifacts, with a unique key per customer/deployment/package. Fernet is not a license signature: continue using Ed25519 for license authenticity. The Fernet key MUST be delivered through online key release or wrapped inside an offline customer license; it MUST NOT be in Git, a generic image, Dockerfile arguments, or public image metadata.

An encrypted `.so` cannot be loaded directly by the operating system. The controlled loader decrypts it into a protected temporary location or memory-backed file, loads it, and removes the plaintext artifact where the platform supports safe cleanup. This protects disk copies but not the loaded library or decrypted memory from a privileged host administrator.

Verify model/library ID and SHA-256 before loading. Avoid persistent plaintext model files and clear temporary decrypted artifacts.

This protects files at rest and casual copying. It cannot prevent memory inspection by a privileged host administrator.

## Runtime hardening

- Release compiled artifacts only; do not ship source maps, training code, or signing keys.
- Run non-root, read-only containers where compatible.
- Pin image digests; sign images and publish SBOMs.
- Disable mock auth, default passwords, debug endpoints, and unsafe Actuator exposure.
- Keep PostgreSQL/Redis private; use HTTPS and secure cookies.
- Audit authentication, publish/download, license, activation, and model access events.
- Provide backup/restore and offline update procedures.

## Legal

The upstream SkillHub repository is Apache 2.0. Releases must include the license, notices, modified-file attribution, and third-party licenses. A commercial license can govern vendor-owned additions and usage terms, but cannot remove Apache rights from upstream code.

## Alternatives and trade-offs

- **Plaintext model volume:** easiest, but offers no model confidentiality.
- **Encrypted on-prem model:** protects at-rest artifacts, with runtime memory exposure.
- **Vendor-controlled inference:** strongest model protection, but requires network/service availability and changes the deployment boundary.
- **Hardware fingerprint:** limits casual copying, but needs a VM migration/support policy.
