"""Conservative split-leakage and split-integrity checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .contracts import AuditFinding


@dataclass(frozen=True)
class LeakageAudit:
    findings: tuple[AuditFinding, ...]


def audit_split_leakage(assets: Iterable[Mapping[str, str]]) -> LeakageAudit:
    findings: list[AuditFinding] = []
    by_hash: dict[str, set[str]] = {}
    by_group: dict[str, set[str]] = {}

    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            findings.append(AuditFinding(
                "invalid_split_asset", "error", f"split asset record {index} is not a mapping"
            ))
            continue
        split = asset.get("split")
        if not isinstance(split, str) or not split.strip():
            findings.append(AuditFinding(
                "missing_split_name", "error", f"split asset record {index} has no valid split name"
            ))
            continue
        digest = asset.get("sha256")
        if digest is not None:
            if not isinstance(digest, str) or len(digest) != 64 or any(
                char not in "0123456789abcdef" for char in digest.lower()
            ):
                findings.append(AuditFinding(
                    "invalid_split_hash", "error", f"asset in split {split!r} has an invalid SHA-256"
                ))
            else:
                by_hash.setdefault(digest.lower(), set()).add(split)

        group = asset.get("source_video") or asset.get("campaign") or asset.get("flight")
        if group is not None:
            if not isinstance(group, str) or not group.strip():
                findings.append(AuditFinding(
                    "invalid_source_group", "error", f"asset in split {split!r} has an invalid source group"
                ))
            else:
                by_group.setdefault(group.strip(), set()).add(split)

    for digest, splits in by_hash.items():
        if len(splits) > 1:
            findings.append(AuditFinding(
                "exact_hash_across_splits", "error",
                f"hash occurs in splits: {sorted(splits)}", digest
            ))
    for group, splits in by_group.items():
        if len(splits) > 1:
            findings.append(AuditFinding(
                "related_group_across_splits", "warning",
                f"source group occurs in splits: {sorted(splits)}", group
            ))
    return LeakageAudit(tuple(findings))


def audit_split_integrity(
    assets: Iterable[Mapping[str, str]],
    splits: Iterable[Mapping[str, object]],
) -> LeakageAudit:
    findings: list[AuditFinding] = []
    known_ids: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            findings.append(AuditFinding(
                "invalid_asset_reference", "error", f"asset record {index} is not a mapping"
            ))
            continue
        asset_id = asset.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            findings.append(AuditFinding(
                "missing_asset_id", "error", f"asset record {index} has no valid asset_id"
            ))
        elif asset_id in known_ids:
            findings.append(AuditFinding(
                "duplicate_asset_id", "error", f"duplicate asset_id: {asset_id}", asset_id
            ))
        else:
            known_ids.add(asset_id)

    split_names: set[str] = set()
    assigned: dict[str, str] = {}
    for index, split in enumerate(splits):
        if not isinstance(split, Mapping):
            findings.append(AuditFinding(
                "invalid_split_record", "error", f"split record {index} is not a mapping"
            ))
            continue
        name = split.get("name")
        if not isinstance(name, str) or not name.strip():
            findings.append(AuditFinding(
                "missing_split_name", "error", f"split record {index} has no valid name"
            ))
            continue
        if name in split_names:
            findings.append(AuditFinding(
                "duplicate_split_name", "error", f"duplicate split name: {name}"
            ))
        split_names.add(name)
        asset_ids = split.get("asset_ids", ())
        if not isinstance(asset_ids, (list, tuple, set)):
            findings.append(AuditFinding(
                "invalid_split_asset_ids", "error", f"split {name!r} asset_ids must be a sequence"
            ))
            continue
        for asset_id in asset_ids:
            if not isinstance(asset_id, str) or not asset_id.strip():
                findings.append(AuditFinding(
                    "invalid_split_asset_id", "error", f"split {name!r} contains an invalid asset id"
                ))
            elif asset_id not in known_ids:
                findings.append(AuditFinding(
                    "unknown_split_asset", "error",
                    f"split {name!r} references unknown asset {asset_id}", asset_id
                ))
            elif asset_id in assigned:
                findings.append(AuditFinding(
                    "asset_in_multiple_splits", "error",
                    f"asset {asset_id} appears in {assigned[asset_id]!r} and {name!r}", asset_id
                ))
            else:
                assigned[asset_id] = name
    return LeakageAudit(tuple(findings))
