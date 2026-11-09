"""Conservative split-leakage checks based on exact hashes and declared groups."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping
from .contracts import AuditFinding

@dataclass(frozen=True)
class LeakageAudit: findings: tuple[AuditFinding, ...]

def audit_split_leakage(assets: Iterable[Mapping[str, str]]) -> LeakageAudit:
    findings: list[AuditFinding] = []
    by_hash: dict[str, set[str]] = {}
    by_group: dict[str, set[str]] = {}
    for asset in assets:
        split = asset.get("split", "")
        digest = asset.get("sha256")
        group = asset.get("source_video") or asset.get("campaign") or asset.get("flight")
        if digest:
            by_hash.setdefault(digest, set()).add(split)
        if group:
            by_group.setdefault(group, set()).add(split)
    for digest, splits in by_hash.items():
        if len(splits) > 1:
            findings.append(AuditFinding("exact_hash_across_splits", "error", f"hash occurs in splits: {sorted(splits)}", digest))
    for group, splits in by_group.items():
        if len(splits) > 1:
            findings.append(AuditFinding("related_group_across_splits", "warning", f"source group occurs in splits: {sorted(splits)}", group))
    return LeakageAudit(tuple(findings))
