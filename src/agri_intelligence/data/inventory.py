"""Local inventory with bounded-memory hashing and explicit symlink policy.

Symlinks are rejected rather than followed. This prevents an inventory root from
silently including content outside the selected dataset directory.
"""
from __future__ import annotations

import hashlib
import os
import struct
from pathlib import Path
from typing import Iterable

from .contracts import DatasetAsset, EvidenceKind


MAX_JPEG_HEADER_BYTES = 1024 * 1024


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _image_dimensions(path: Path) -> tuple[int | None, int | None, int | None, str | None]:
    suffix = path.suffix.lower()
    try:
        with path.open("rb") as handle:
            if suffix == ".png":
                header = handle.read(26)
                if (
                    len(header) >= 26
                    and header[:8] == b"\x89PNG\r\n\x1a\n"
                    and header[12:16] == b"IHDR"
                ):
                    width, height = struct.unpack(">II", header[16:24])
                    color_type = header[25]
                    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
                    if width > 0 and height > 0:
                        return width, height, channels, "png"
                return None, None, None, None

            if suffix not in {".jpg", ".jpeg"}:
                return None, None, None, None
            if handle.read(2) != b"\xff\xd8":
                return None, None, None, None

            while handle.tell() < MAX_JPEG_HEADER_BYTES:
                prefix = handle.read(1)
                if not prefix:
                    break
                if prefix != b"\xff":
                    continue
                marker_byte = handle.read(1)
                while marker_byte == b"\xff" and handle.tell() < MAX_JPEG_HEADER_BYTES:
                    marker_byte = handle.read(1)
                if not marker_byte or handle.tell() >= MAX_JPEG_HEADER_BYTES:
                    break
                marker = marker_byte[0]
                if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                    continue
                # Start of Scan means image payload follows; do not scan compressed data.
                if marker == 0xDA:
                    break
                if handle.tell() + 2 > MAX_JPEG_HEADER_BYTES:
                    break
                length_bytes = handle.read(2)
                if len(length_bytes) != 2:
                    break
                segment_length = struct.unpack(">H", length_bytes)[0]
                if segment_length < 2:
                    break
                if marker in {
                    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
                }:
                    if handle.tell() + 6 > MAX_JPEG_HEADER_BYTES:
                        break
                    frame = handle.read(6)
                    if len(frame) != 6:
                        break
                    _precision, height, width, channels = struct.unpack(">BHHB", frame)
                    if width > 0 and height > 0 and channels > 0:
                        return width, height, channels, "jpeg"
                    break
                next_position = handle.tell() + segment_length - 2
                if next_position > MAX_JPEG_HEADER_BYTES:
                    break
                handle.seek(segment_length - 2, os.SEEK_CUR)
    except (OSError, struct.error, ValueError):
        pass
    return None, None, None, None


def _safe_candidate(root: Path, candidate: Path) -> Path:
    candidate = candidate if candidate.is_absolute() else root / candidate
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside inventory root: {candidate}") from exc

    current = root
    if current.is_symlink():
        raise ValueError(f"inventory root cannot be a symlink: {root}")
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink paths are not inventoried: {current}")

    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"resolved path is outside inventory root: {candidate}") from exc
    if not resolved.is_file():
        raise ValueError(f"inventory candidate is not a regular file: {candidate}")
    return resolved


def inventory_paths(root: Path, paths: Iterable[Path] | None = None) -> tuple[DatasetAsset, ...]:
    root = Path(root).expanduser().absolute()
    if root.is_symlink():
        raise ValueError("inventory root cannot be a symlink")
    if not root.exists():
        raise FileNotFoundError(f"inventory root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"inventory root is not a directory: {root}")
    root = root.resolve(strict=True)

    if paths is None:
        candidates: list[Path] = []
        for current, directories, filenames in os.walk(root, followlinks=False):
            current_path = Path(current)
            directories[:] = sorted(
                name for name in directories if not (current_path / name).is_symlink()
            )
            for filename in sorted(filenames):
                candidate = current_path / filename
                if not candidate.is_symlink() and candidate.is_file():
                    candidates.append(candidate)
    else:
        candidates = [Path(path) for path in paths]

    assets = []
    for candidate in sorted(candidates, key=lambda item: str(item)):
        path = _safe_candidate(root, candidate)
        relative = path.relative_to(root).as_posix()
        width, height, channels, image_format = _image_dimensions(path)
        assets.append(DatasetAsset(
            asset_id=relative,
            path=relative,
            size_bytes=path.stat().st_size,
            sha256=sha256_file(path),
            format=image_format or path.suffix.lower().lstrip("."),
            width=width,
            height=height,
            channels=channels,
            evidence={
                "size_bytes": EvidenceKind.OBSERVED,
                "sha256": EvidenceKind.CALCULATED,
                "dimensions": EvidenceKind.OBSERVED if width else EvidenceKind.MISSING,
            },
        ))
    return tuple(assets)
