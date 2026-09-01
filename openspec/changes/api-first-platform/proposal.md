# Proposal: API-first WBrain platform

## Why

The current service recognizes one uploaded image but does not persist meter
identity, reading history, review decisions, or model provenance. Customer
integrations therefore cannot retrieve history, validate anomalous readings, or
build a reliable SDK on top of a stable contract.

## Scope

- Add a persistent API data layer with SQLite as the default on-premise store.
- Add meter CRUD and reading-history retrieval.
- Persist image metadata, SHA-256, model version, detections, and readings.
- Add basic anomaly detection and manual-review workflow.
- Add model-version and audit-event APIs.
- Preserve the existing stateless recognition response.
- Document API-first versioning and defer SDK generation until contracts pass.

## Out of scope

- Vector search/RAG.
- Billing integration.
- Multi-tenant SSO/LDAP.
- PostgreSQL deployment implementation (repository boundary is prepared).
- Production customer authentication beyond the configurable API key boundary.
