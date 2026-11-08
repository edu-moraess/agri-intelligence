# ADR-0004: Phase 0 validation gates

- Status: Accepted
- Context: The initial validator declared a required secret scan that it did not execute and did not compile Python sources.
- Decision: Implement explicit package import, in-memory Python compilation, unit/structural tests, conservative credential-pattern scanning and prohibited-artifact scanning. A skipped required check is a gate failure.
- Consequences: The report records each executed check and does not expose matched credential values. Pattern-based scanning can produce false positives/negatives and is not represented as a dedicated secret-scanning service.
