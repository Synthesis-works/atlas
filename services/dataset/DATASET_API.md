# Dataset API

## Overview
This API allows for the registration, uploading, validation, and publishing of evaluation datasets.

## Endpoints

### Registries, Sources, and Licenses
- `GET /registries`
- `GET /sources`
- `GET /licenses`

### Dataset Registration
- `GET /datasets`
- `POST /datasets`
  - Registers a new dataset (metadata only, no file).
  - Status: `REGISTERED`

### Dataset Versions & Upload
- `GET /datasets/{id}/versions`
- `POST /datasets/{id}/versions`
  - Uploads a file for a dataset, creating a new `DatasetVersion`.
  - Status transitions to `UPLOADED`.

### Validation
- `POST /datasets/{id}/versions/{version}/validate`
  - Triggers the validation pipeline.
  - Status transitions to `VALIDATING` then `VALID` (or `FAILED`).

### Cleaning
- `POST /datasets/{id}/versions/{version}/clean`
  - Optional. Triggers the cleaning pipeline.
  - Status transitions to `CLEANING` then `READY`.

### Publishing
- `POST /datasets/{id}/versions/{version}/publish`
  - Marks a `VALID` or `READY` dataset version as `PUBLISHED`.

### Download
- `GET /datasets/{id}/versions/{version}/download`
  - Streams the dataset file content.
