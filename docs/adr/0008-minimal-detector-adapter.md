# ADR-0008 — Minimal model-independent detector adapter

- **Status:** Proposed implementation in Phase 2.2
- **Date:** 2026-11-09

## Context

Phase 2.1 supplies validated image frames and deterministic tiles. The
perception contracts already define PerceptionModel and DetectionPrediction;
this increment needs an executable backend fixture to exercise that boundary
without coupling the core to a model framework.

## Decisions

1. Keep PerceptionModel.predict(frame, *, run_id) as the backend-neutral
   protocol defined in the perception contracts.
2. Add FakePerceptionModel and FakeDetection in perception.testing. The fake
   backend returns only caller-supplied deterministic fixtures and never
   examines image pixels.
3. Bind each output to the supplied frame's coordinate space, parent image ID,
   optional tile ID, and run ID. Prediction IDs and output ordering are stable.
4. Reuse BoundingBox2D and DetectionPrediction validation; invalid scores,
   non-finite or degenerate boxes, and boxes outside the actual frame fail.
5. Do not add model-framework dependencies, load weights, download assets,
   run inference, train, or claim scientific performance.

## Consequences

- The image/tile → fake detector path can be tested without external packages.
- Tests can verify image and tile provenance independently of a real backend.
- The fake backend is software-test infrastructure only. Its outputs are not
  detections and must never be used as model-quality or agronomic evidence.
- A real backend remains a separately authorized follow-up after data,
  dependency, and weight provenance are approved.
