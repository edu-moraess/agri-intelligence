"""Deterministic JSON serialization with atomic manifest replacement."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any

from .contracts import DatasetManifest


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def manifest_to_dict(manifest: DatasetManifest) -> dict[str, Any]:
    return _jsonable(manifest)


def write_manifest(manifest: DatasetManifest, path: Path) -> None:
    destination = Path(path)
    if not destination.parent.exists() or not destination.parent.is_dir():
        raise FileNotFoundError(f"manifest output directory does not exist: {destination.parent}")
    if destination.exists() and destination.is_dir():
        raise IsADirectoryError(f"manifest output path is a directory: {destination}")
    payload = json.dumps(
        manifest_to_dict(manifest), indent=2, ensure_ascii=False, allow_nan=False
    ) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            prefix=f".{destination.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
