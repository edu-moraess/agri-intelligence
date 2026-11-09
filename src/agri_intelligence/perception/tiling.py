"""Deterministic, dependency-free tiling for immutable uint8 pixel buffers."""
from __future__ import annotations

from collections.abc import Iterator

from .contracts import ImageFrame, TileRecord


def _tile_starts(length: int, tile_size: int, overlap: int) -> tuple[int, ...]:
    effective = min(length, tile_size)
    if effective == length:
        return (0,)
    stride = tile_size - overlap
    starts = list(range(0, length - tile_size + 1, stride))
    final_start = length - tile_size
    if not starts or starts[-1] != final_start:
        starts.append(final_start)
    return tuple(starts)


def _crop_bytes(frame: ImageFrame, x: int, y: int, width: int, height: int) -> bytes:
    if frame.dtype != "uint8" or not isinstance(frame.pixels, bytes):
        raise ValueError("tiling requires an immutable bytes payload with dtype='uint8'")
    expected = frame.width * frame.height * frame.channels
    if len(frame.pixels) != expected:
        raise ValueError("pixel buffer length does not match frame dimensions")
    row_bytes = width * frame.channels
    source_stride = frame.width * frame.channels
    chunks = []
    for row in range(y, y + height):
        start = row * source_stride + x * frame.channels
        chunks.append(frame.pixels[start : start + row_bytes])
    return b"".join(chunks)


def generate_tiles(
    frame: ImageFrame,
    *,
    tile_width: int,
    tile_height: int,
    overlap: int = 0,
) -> tuple[tuple[ImageFrame, TileRecord], ...]:
    """Return row-major tiles and parent-image windows, with complete edge coverage.

    The final tile on each axis is anchored to the image edge. This may create
    more overlap than requested in the final interval, but never leaves a gap.
    Images smaller than the requested tile produce one tile of native size.
    """
    for name, value in (("tile_width", tile_width), ("tile_height", tile_height)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if isinstance(overlap, bool) or not isinstance(overlap, int) or overlap < 0:
        raise ValueError("overlap must be a non-negative integer")
    if overlap >= min(tile_width, tile_height):
        raise ValueError("overlap must be smaller than both tile dimensions")
    if frame.tile_id is not None:
        raise ValueError("nested tiling is not supported; provide a parent image frame")

    xs = _tile_starts(frame.width, tile_width, overlap)
    ys = _tile_starts(frame.height, tile_height, overlap)
    output: list[tuple[ImageFrame, TileRecord]] = []
    index = 0
    for y in ys:
        for x in xs:
            width = min(tile_width, frame.width - x)
            height = min(tile_height, frame.height - y)
            tile_id = f"{frame.image_id}::tile:{index:06d}"
            record = TileRecord(
                tile_id=tile_id,
                image_id=frame.image_id,
                x=x,
                y=y,
                width=width,
                height=height,
                image_width=frame.width,
                image_height=frame.height,
                tile_index=index,
            )
            tile_frame = ImageFrame(
                image_id=frame.image_id,
                width=width,
                height=height,
                channels=frame.channels,
                dtype=frame.dtype,
                color_space=frame.color_space,
                source_sha256=frame.source_sha256,
                pixels=_crop_bytes(frame, x, y, width, height),
                tile_id=tile_id,
            )
            output.append((tile_frame, record))
            index += 1
    return tuple(output)
