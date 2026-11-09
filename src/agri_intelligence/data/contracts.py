"""Framework-independent contracts for dataset provenance and auditability."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

class LicenseStatus(str, Enum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    RESTRICTED = "restricted"
    PENDING_REVIEW = "pending_review"

class AuditState(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"

class EvidenceKind(str, Enum):
    DECLARED = "declared"
    OBSERVED = "observed"
    CALCULATED = "calculated"
    MISSING = "missing"
    INCONSISTENT = "inconsistent"

@dataclass(frozen=True)
class DatasetSource:
    uri: str
    publisher: str | None = None
    access_date: str | None = None
    source_type: str = "unknown"
    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise ValueError("dataset source uri is required")

@dataclass(frozen=True)
class DatasetLicense:
    name: str | None
    status: LicenseStatus
    rights_verified: bool = False
    commercial_use_verified: bool = False
    attribution_required: bool | None = None
    notes: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        if self.status == LicenseStatus.VERIFIED and not self.name:
            raise ValueError("verified license requires a name")
        if self.status != LicenseStatus.VERIFIED and (self.rights_verified or self.commercial_use_verified):
            raise ValueError("unverified license cannot claim verified rights")
    @property
    def adoption_blocked(self) -> bool:
        return self.status != LicenseStatus.VERIFIED

@dataclass(frozen=True)
class DatasetVersion:
    version: str
    revision: str | None = None
    released_at: str | None = None
    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("dataset version is required")

@dataclass(frozen=True)
class AcquisitionMetadata:
    campaigns: tuple[str, ...] = ()
    dates: tuple[str, ...] = ()
    sensors: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    source_videos: tuple[str, ...] = ()
    field_or_parcel_ids: tuple[str, ...] = ()
    declared: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class AnnotationSchema:
    format: str
    task: str
    classes: tuple[str, ...]
    coordinate_mode: str = "absolute_xywh"
    def __post_init__(self) -> None:
        if not self.format.strip() or not self.task.strip() or not self.classes:
            raise ValueError("annotation format, task and classes are required")

@dataclass(frozen=True)
class DatasetSplit:
    name: str
    asset_ids: tuple[str, ...] = ()
    source_groups: tuple[str, ...] = ()
    provenance: str | None = None
    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("split name is required")

@dataclass(frozen=True)
class DatasetAsset:
    asset_id: str
    path: str
    size_bytes: int
    sha256: str | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None
    channels: int | None = None
    temporal_metadata: Mapping[str, Any] = field(default_factory=dict)
    spatial_metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Mapping[str, EvidenceKind] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.asset_id.strip() or not self.path.strip() or self.size_bytes < 0:
            raise ValueError("asset identity, path and non-negative size are required")
        if self.sha256 is not None and (len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256.lower())):
            raise ValueError("sha256 must be a 64-character hexadecimal string")
        if self.width is not None and self.width <= 0 or self.height is not None and self.height <= 0:
            raise ValueError("asset dimensions must be positive")

@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: str
    message: str
    asset_id: str | None = None

@dataclass(frozen=True)
class DatasetAuditResult:
    state: AuditState
    findings: tuple[AuditFinding, ...] = ()
    checks: Mapping[str, str] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        if self.state == AuditState.PASS and any(f.severity == "error" for f in self.findings):
            raise ValueError("PASS cannot contain error findings")

@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    version: DatasetVersion
    source: DatasetSource
    license: DatasetLicense
    assets: tuple[DatasetAsset, ...] = ()
    annotation_schema: AnnotationSchema | None = None
    splits: tuple[DatasetSplit, ...] = ()
    acquisition: AcquisitionMetadata = field(default_factory=AcquisitionMetadata)
    classes: tuple[str, ...] = ()
    spatial_reference: Mapping[str, Any] = field(default_factory=dict)
    audit: DatasetAuditResult | None = None
    limitations: tuple[str, ...] = ()
    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise ValueError("dataset_id is required")
        if self.license.adoption_blocked and self.audit and self.audit.state not in {AuditState.BLOCKED, AuditState.FAIL}:
            raise ValueError("dataset with unverified license cannot have an adoptable audit state")
    @property
    def adoption_state(self) -> AuditState:
        if self.license.adoption_blocked:
            return AuditState.BLOCKED
        return self.audit.state if self.audit else AuditState.PASS_WITH_WARNINGS
