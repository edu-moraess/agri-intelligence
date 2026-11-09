"""JSON serialization for reproducible dataset manifests."""
from __future__ import annotations
import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any
from .contracts import DatasetManifest

def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum): return value.value
    if hasattr(value, "__dataclass_fields__"): return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict): return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_jsonable(v) for v in value]
    return value

def manifest_to_dict(manifest: DatasetManifest) -> dict[str, Any]: return _jsonable(manifest)

def write_manifest(manifest: DatasetManifest, path: Path) -> None:
    path.write_text(json.dumps(manifest_to_dict(manifest), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
