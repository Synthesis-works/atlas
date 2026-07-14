# Dataset Invariants

1. **Sole Ownership:** The Dataset Service is the single source of truth for dataset metadata, schema, and raw data storage logic.
2. **Downward Data Flow Only:** The Dataset Service never queries or depends on Execution, Evaluation, or Reporting. It is a strict provider.
3. **Immutability of Published Versions:** A dataset version that reaches the `PUBLISHED` state cannot be altered. Changes require a new version number.
4. **Storage Agnosticism:** File movement and persistence are completely mediated by `StorageProvider`.
5. **Versioning Isolation:** The `VersioningService` only manages metadata (checksums, lineage, semantic versions) and never moves or alters the underlying files itself.
6. **Publishing Purity:** `PublishingService` is restricted to state transitions (`READY` -> `PUBLISHED`). It does not validate or clean.
