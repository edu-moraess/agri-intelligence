# ADR-0007 — Image decoding and deterministic tiling

- **Status:** Proposed implementation in Phase 2.1
- **Date:** 2026-11-09

## Context

The perception contracts now define image frames, tile-local coordinates, and
source provenance. The next increment needs a small image-loading boundary and
a deterministic way to divide large images without introducing a mandatory ML
or image-processing framework into the domain core.

## Decisions

1. Image decoding is isolated in `perception.image_io`. Pillow is an optional
   extra (`pip install .[image]`), imported only when `read_image` is called.
2. The decoder verifies the source, applies EXIF orientation, converts pixels
   explicitly to RGB uint8, and returns immutable `bytes` in `ImageFrame`.
   The SHA-256 is calculated over the original file bytes, not the converted
   pixel buffer.
3. Tiling is implemented with the Python standard library. It accepts only
   uint8 immutable byte buffers with a length matching the frame dimensions.
4. Tiles are emitted in deterministic row-major order. Each tile carries a
   `TileRecord` with its exact parent-image window and stable index.
5. Edge tiles are anchored to the image boundary to guarantee full coverage.
   The final interval can therefore have more overlap than the configured
   minimum. Images smaller than the requested tile produce one native-size tile.
6. Tiling does not modify the source frame, perform georeferencing, infer
   physical dimensions, or deduplicate predictions.

## Consequences

- The core package remains free of mandatory runtime dependencies.
- Consumers that need file decoding install the optional Pillow extra.
- Synthetic byte-buffer tests cover pixel crops, edge coverage, odd dimensions,
  overlap, provenance, invalid configurations, and smaller-than-tile images.
- Real image decoding still requires an environment with the optional Pillow
  dependency; no dataset or model weights are required.
