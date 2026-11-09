# ADR-0005: Foundation of the Phase 1 data engine

- **Status:** Accepted; hardening amendments applied on `feat/phase-1-data-engine`.
- **Context:** The project needs a reproducible local inventory and dataset contract layer without coupling to a data framework or downloading candidate datasets.
- **Decision:** Use standard-library dataclasses, bounded-memory local inventory, explicit evidence kinds, JSON manifests, annotation validators and conservative exact-hash/group leakage checks. Keep dataset adoption separate from software validation.
- **License rule:** A license identifier alone does not authorize adoption. The current project gate requires a verified license plus explicit review of redistribution rights, commercial-use terms and attribution obligations. This is a conservative engineering gate, not legal advice.
- **Path policy:** Inventory does not follow symlinks. Explicit symlink paths and paths outside the selected root are rejected; recursive discovery skips symlink entries.
- **Annotation policy:** Detection boxes are checked for finite numeric values and image bounds. Supported coordinate modes are explicit; unknown modes fail closed.
- **Split policy:** Asset IDs and split names must be unique; split references must resolve to known assets, and an asset cannot be assigned to multiple splits.
- **Alternatives:** Download MSDD immediately; rejected because the task forbids downloads and the Hugging Face distribution declares `unknown` license. Use framework-specific loaders; deferred to a later phase to minimize dependencies.
- **Risks:** Header inspection does not replace full format validation; exact hashes miss near-duplicates; shared source groups indicate risk but do not establish leakage. Atomic replacement reduces partial-write risk but does not eliminate all filesystem races.
- **Validation:** Synthetic unit tests and local manifest generation; execution evidence must be recorded separately from code review.
- **Reversibility:** High; framework adapters can be added around the contracts without changing the evidence model.
