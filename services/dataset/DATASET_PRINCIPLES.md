# Dataset Principles

1. **Dataset owns dataset truth:** No downstream subsystem can modify a dataset. They strictly consume published versions.
2. **Immutable Snapshots:** Once a Dataset Version is published, it is immutable. Any change (cleaning, re-upload) requires a new version.
3. **Decoupled Lifecycle:** Uploading, validating, cleaning, and publishing are independent operations. A dataset can be uploaded and stored without immediately passing validation or being cleaned.
4. **Abstracted Storage:** The service must never assume local disk availability for long-term storage; it must always use a `StorageProvider`.
5. **Composable Logic:** Validation and Cleaning are not hardcoded monoliths. They rely on `ValidationRule` and `CleaningPipeline` patterns.
6. **Strict State Machine:** Datasets transition through explicitly defined states, preventing invalid operations (e.g. publishing an invalid dataset).
