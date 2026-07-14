# Dataset API Contract

## Core Workflows

1. **Registration:** `POST /api/v1/datasets`
   - Creates a metadata record without a file. Returns `DatasetDTO`.
2. **Upload & Versioning:** `POST /api/v1/datasets/{id}/versions`
   - Accepts a multipart file upload.
   - Saves file via `StorageProvider`.
   - Returns version ID. Status -> `UPLOADED`.
3. **Validation:** `POST /api/v1/datasets/{id}/versions/{version_id}/validate`
   - Runs `ValidationRules` on the stored file.
   - Transitions status to `VALIDATING` then `VALID` or `FAILED`.
4. **Publishing:** `POST /api/v1/datasets/{id}/versions/{version_id}/publish`
   - Transitions state to `PUBLISHED`, locking the dataset for downstream use.

All endpoints adhere strictly to the `DATASET_STATE_MACHINE.md` and enforce that Dataset remains the single source of truth for raw datasets.
