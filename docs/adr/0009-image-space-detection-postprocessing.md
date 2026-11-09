# ADR-0009 — Image-space detection postprocessing

- **Status:** Proposed implementation in Phase 2.3
- **Date:** 2026-11-09

## Context

Phase 2.1 creates deterministic image tiles and TileRecord windows. Phase 2.2
defines a backend-neutral DetectionPrediction contract, including tile-local
coordinate provenance. Predictions from overlapping tiles may describe the
same physical object and must be reconciled before evaluation or spatial
analysis.

## Decisions

1. Add a dependency-free postprocessing module operating on typed
   DetectionPrediction and TileRecord values.
2. Convert TILE-space XYXY boxes to parent IMAGE coordinates using the exact
   TileRecord offset and retain the originating tile_id as provenance.
3. Reject missing, duplicate, or inconsistent tile provenance and invalid
   geometry. Do not silently clip boxes: upstream coordinate errors must remain
   visible and auditable.
4. Apply deterministic greedy, class-aware non-maximum suppression (NMS).
   Suppression is isolated by image, class, model name/version, and run ID.
   The higher-scoring box wins when IoU is strictly greater than the configured
   threshold; the default threshold is 0.5.
5. Preserve prediction IDs, scores, class IDs, model metadata, run IDs, image
   IDs, and tile IDs. Return immutable tuples and do not mutate inputs.
6. Keep the core free of NumPy, Torch, OpenCV, and other new dependencies.

## Consequences and limitations

- Overlapping tile predictions can be consolidated into image-space results.
- Different classes and independent model runs are never suppressed against
  each other.
- Greedy NMS is a baseline, not a universal solution. Dense seedlings or
  touching plants may require threshold calibration, Soft-NMS, weighted box
  fusion, or instance segmentation after evaluation on licensed real data.
- This stage does not evaluate model quality, infer plant counts, reconstruct
  planting rows, georeference boxes, download datasets/weights, run inference,
  or train a model.
- The fake adapter remains a software fixture only; synthetic tests do not
  constitute agricultural performance evidence.
