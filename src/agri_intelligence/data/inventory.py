"""Local, bounded inventory of files; never loads image payloads wholesale."""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path
from typing import Iterable
from .contracts import DatasetAsset, EvidenceKind

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()

def _image_dimensions(path: Path) -> tuple[int | None, int | None, int | None, str | None]:
    suffix = path.suffix.lower()
    try:
        with path.open("rb") as handle:
            header = handle.read(32)
            if suffix == ".png" and header[:8] == b"\x89PNG\r\n\x1a\n":
                width, height = struct.unpack(">II", header[16:24])
                channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(header[25], None)
                return width, height, channels, "png"
            if suffix in {".jpg", ".jpeg"} and header[:2] == b"\xff\xd8":
                handle.seek(2)
                while True:
                    marker = handle.read(2)
                    if len(marker) != 2 or marker[0] != 0xff:
                        break
                    while marker[1] == 0xff:
                        marker = bytes((marker[0],)) + handle.read(1)
                    if marker[1] in {0xd8, 0xd9}:
                        continue
                    length_bytes = handle.read(2)
                    if len(length_bytes) != 2:
                        break
                    length = struct.unpack(">H", length_bytes)[0]
                    if 0xc0 <= marker[1] <= 0xc3 or 0xc5 <= marker[1] <= 0xc7 or 0xc9 <= marker[1] <= 0xcb or 0xcd <= marker[1] <= 0xcf:
                        precision, height, width, channels = struct.unpack(">BHHB", handle.read(6))
                        return width, height, channels, "jpeg"
                    handle.seek(length - 2, 1)
    except (OSError, struct.error):
        pass
    return None, None, None, None

def inventory_paths(root: Path, paths: Iterable[Path] | None = None) -> tuple[DatasetAsset, ...]:
    root = root.resolve()
    candidates = sorted(paths if paths is not None else (p for p in root.rglob("*") if p.is_file()))
    assets = []
    for path in candidates:
        path = path.resolve()
        path.relative_to(root)
        width, height, channels, image_format = _image_dimensions(path)
        assets.append(DatasetAsset(asset_id=path.relative_to(root).as_posix(), path=path.relative_to(root).as_posix(), size_bytes=path.stat().st_size, sha256=sha256_file(path), format=image_format or path.suffix.lower().lstrip("."), width=width, height=height, channels=channels, evidence={"size_bytes": EvidenceKind.OBSERVED, "sha256": EvidenceKind.CALCULATED, "dimensions": EvidenceKind.OBSERVED if width else EvidenceKind.MISSING}))
    return tuple(assets)
