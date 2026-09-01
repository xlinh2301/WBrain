# Proposal: Enterprise On-Premise Packaging and Licensing

## Why

Package the SkillHub-derived platform and WBrain OCR service for customer-controlled on-premise deployment while limiting licensed features and protecting proprietary model artifacts.

## What changes

- Keep the complete source code and Dockerfiles in Git, with tagged semantic versions.
- Build release images from source using a reproducible release Dockerfile.
- Generate customer release artifacts under local `release/`; this folder is ignored and MUST NOT be pushed to Git.
- Publish versioned runtime images to Docker Hub and distribute the customer license through a private release channel.
- Use Fernet to encrypt customer model and native `.so` artifacts at rest; never store the Fernet key in Git or a generic Docker image.
- Add signed customer licenses with online and offline activation.
- Enforce expiry, deployment binding, feature flags, and optional node limits in the backend.
- Maintain committed per-version release notes under `release-notes/`.
- Add production security hardening, audit events, image signing, SBOM, backup, and recovery requirements.
- Preserve Apache 2.0 and third-party obligations from upstream SkillHub.

## What does not change

The existing OCR API contract remains governed by `openspec/specs/ocr-api/spec.md`.

## Security boundary

A customer with Administrator/root access to the host can inspect containers, binaries, memory, and runtime traffic. The design prevents casual copying and unauthorized use; it does not claim impossible absolute secrecy. High-value models require vendor-controlled inference.
