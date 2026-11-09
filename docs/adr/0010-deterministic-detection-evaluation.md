# ADR-0010: Deterministic image-space detection evaluation

- **Status:** Accepted
- **Date:** 2026-11-09
- **Context:** Phase 2.4 — Evaluation Framework

## Context

The perception pipeline now produces typed image-space predictions and deterministic postprocessed boxes. Evaluation must compare these predictions with audited reference annotations without coupling the core to a dataset format, detector backend, or ML framework. Ground truth and predictions are different evidence types and must not be conflated.

## Decisions

1. **Separate ground truth.** `GroundTruthBox` is an immutable value containing annotation ID, image ID, class ID, and an IMAGE-space `BoundingBox2D`. TILE-space ground truth is rejected at the evaluator boundary.
2. **One-to-one matching.** Predictions are processed in descending confidence order. Matching is scoped to image and class. Each prediction can match at most one unmatched ground-truth box, and each ground-truth box can be claimed at most once. The best available IoU is selected; a match is accepted when IoU is greater than or equal to the configured threshold.
3. **Explicit protocol identifiers.** The configuration records the supported matching policy (`greedy_score`) and AP method (`interpolated_101_point`); unsupported alternatives are rejected instead of silently changing semantics. The default IoU set is 0.50 through 0.95 in 0.05 increments, with 0.50 as the operating point.\n4. **Stable ties.** Equal-score predictions are ordered by image ID and prediction ID. Ground-truth candidates with equal IoU are resolved by annotation ID. This makes results deterministic.
5. **Operating-point metrics.** TP/FP/FN, precision, and recall use the configured confidence threshold and operating IoU threshold. Precision is undefined (`None`) when there are no selected predictions; recall is undefined when there is no ground-truth support.
6. **Ranked AP.** Average precision uses all predictions, ordered by confidence, independently of the operating confidence threshold. AP is the 101-point interpolated mean of maximum precision at recall levels 0.00 through 1.00, inclusive.
7. **Aggregation.** Per-class AP is undefined for classes with zero ground-truth support. mAP averages only classes with positive ground-truth support. If no class has support, mAP is undefined (`None`), not zero.
8. **No external dependency.** Geometry, matching, and metric calculations use the standard library and existing perception contracts only.

## Consequences

- Results are reproducible for identical input values and configuration.
- The evaluator is a software contract, not proof of model or agronomic performance.
- Dataset splits, acquisition-group leakage, license approval, and annotation audit remain prerequisites for a real benchmark.
- AP interpolation and tie-breaking are part of the recorded protocol and must not change silently.
