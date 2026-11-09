# ADR-0005: Foundation of the Phase 1 data engine

- **Status:** Accepted.
- **Context:** The project needs a reproducible local inventory and dataset contract layer without coupling to a data framework or downloading candidate datasets.
- **Decision:** Use standard-library dataclasses, bounded local file inventory, explicit evidence kinds, JSON manifests, annotation validators and conservative exact-hash/group leakage checks. Keep dataset adoption separate from software validation.
- **License rule:** A dataset with `unknown`, `restricted` or `pending_review` license status is `BLOCKED` for adoption. Technical structure cannot override a licensing block.
- **Alternatives:** Download MSDD immediately; rejected because the task forbids downloads and the Hugging Face distribution declares `unknown` license. Use framework-specific loaders; deferred to a later phase to minimize dependencies.
- **Risks:** Header inspection does not replace full format validation; exact hashes miss near-duplicates; shared source groups indicate risk but do not establish leakage. These are recorded as limitations.
- **Validation:** Synthetic unit tests, local manifest generation and no-download source inspection.
- **Reversibility:** High; framework adapters can be added around the contracts without changing the evidence model.
