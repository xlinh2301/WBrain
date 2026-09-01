# Design

## Storage

The first implementation uses a small repository boundary over SQLite so the
single-container on-premise deployment works without an external database.
`DATABASE_PATH` is mounted under `/var/lib/wbrain`. A PostgreSQL repository is a
follow-up implementation, not a contract change.

Raw images are disabled by default. When `STORE_IMAGES=true`, files are written
under `IMAGE_STORAGE_DIR` using generated IDs and never client filenames.

## Resource contract

- `meters`: registered physical meters.
- `meter_images`: hash and processing metadata.
- `readings`: normalized OCR result and validation status.
- `review_tasks`: operator correction workflow.
- `model_versions`: inference provenance.
- `audit_events`: mutation history with request IDs.

## Security and privacy

A configured `API_KEY` is required for `/api/v1` mutations and reads except
health. No API key is shipped by default in development. The API never logs or
returns raw image bytes, license contents, or encryption keys.

This change does not claim protection from a privileged host administrator.

## Compatibility

`POST /api/v1/recognize` keeps its existing response shape. `meter_id` is an
optional multipart field. The database layer is initialized at application
startup and can be disabled for stateless deployments with `PERSISTENCE_ENABLED`.
