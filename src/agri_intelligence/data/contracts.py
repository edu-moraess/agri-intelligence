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
        if not isinstance(self.uri, str) or not self.uri.strip():
            raise ValueError("dataset source uri is required")


@dataclass(frozen=True)
class DatasetLicense:
    name: str | None
    status: LicenseStatus
    rights_verified: bool = False
    commercial_use_verified: bool = False
    attribution_required: bool | None = None
    attribution_verified: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, LicenseStatus):
            raise ValueError("status must be a LicenseStatus")
        if self.status == LicenseStatus.VERIFIED and (not isinstance(self.name, str) or not self.name.strip()):
            raise ValueError("verified license requires a name")
        if self.status != LicenseStatus.VERIFIED and any(
            (self.rights_verified, self.commercial_use_verified, self.attribution_verified)
        ):
            raise ValueError("unverified license cannot claim verified rights or attribution")
        for value in (self.rights_verified, self.commercial_use_verified, self.attribution_verified):
            if not isinstance(value, bool):
                raise ValueError("license verification flags must be booleans")
        if self.attribution_required is not None and not isinstance(self.attribution_required, bool):
            raise ValueError("attribution_required must be bool or None")
        if any(not isinstance(note, str) for note in self.notes):
            raise ValueError("license notes must be strings")

    @property
    def adoption_blocked(self) -> bool:
        # This project may be used commercially. Identification of a license alone
        # is insufficient: redistribution, commercial-use terms and attribution
        # obligations must each have been reviewed explicitly.
        return not (
            self.status == LicenseStatus.VERIFIED
            and self.rights_verified
            and self.commercial_use_verified
            and self.attribution_verified
        )


@dataclass(frozen=True)
class DatasetVersion:
    version: str
    revision: str | None = None
    released_at: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version.strip():
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
        if not isinstance(self.format, str) or not self.format.strip():
            raise ValueError("annotation format is required")
        if not isinstance(self.task, str) or not self.task.strip():
            raise ValueError("annotation task is required")
        if not self.classes or any(not isinstance(item, str) or not item.strip() for item in self.classes):
            raise ValueError("annotation classes must be non-empty strings")
        if len(set(self.classes)) != len(self.classes):
            raise ValueError("annotation classes must be unique")
        if not isinstance(self.coordinate_mode, str) or self.coordinate_mode not in {
            "absolute_xywh", "normalized_xywh", "absolute_xyxy", "normalized_xyxy"
        }:
            raise ValueError("unsupported annotation coordinate_mode")


@dataclass(frozen=True)
class DatasetSplit:
    name: str
    asset_ids: tuple[str, ...] = ()
    source_groups: tuple[str, ...] = ()
    provenance: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("split name is required")
        if any(not isinstance(item, str) or not item.strip() for item in self.asset_ids):
            raise ValueError("split asset_ids must be non-empty strings")
        if len(set(self.asset_ids)) != len(self.asset_ids):
            raise ValueError("split asset_ids must be unique")
        if any(not isinstance(item, str) or not item.strip() for item in self.source_groups):
            raise ValueError("split source_groups must be non-empty strings")


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
        if not isinstance(self.asset_id, str) or not self.asset_id.strip():
            raise ValueError("asset_id is required")
        if not isinstance(self.path, str) or not self.path.strip():
            raise ValueError("asset path is required")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError("asset size_bytes must be a non-negative integer")
        if self.sha256 is not None and (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.sha256.lower())
        ):
            raise ValueError("sha256 must be a 64-character hexadecimal string")
        for name, value in (("width", self.width), ("height", self.height), ("channels", self.channels)):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
            ):
                raise ValueError(f"asset {name} must be a positive integer")


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
        if not isinstance(self.dataset_id, str) or not self.dataset_id.strip():
            raise ValueError("dataset_id is required")
        asset_ids = [asset.asset_id for asset in self.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("manifest asset_ids must be unique")
        asset_paths = [asset.path for asset in self.assets]
        if len(asset_paths) != len(set(asset_paths)):
            raise ValueError("manifest asset paths must be unique")
        split_names = [split.name for split in self.splits]
        if len(split_names) != len(set(split_names)):
            raise ValueError("manifest split names must be unique")
        known_assets = set(asset_ids)
        assigned_assets: set[str] = set()
        for split in self.splits:
            unknown = set(split.asset_ids) - known_assets
            if unknown:
                raise ValueError(f"split {split.name!r} references unknown assets: {sorted(unknown)}")
            overlap = assigned_assets.intersection(split.asset_ids)
            if overlap:
                raise ValueError(f"assets assigned to multiple splits: {sorted(overlap)}")
            assigned_assets.update(split.asset_ids)
        if self.license.adoption_blocked and self.audit and self.audit.state not in {
            AuditState.BLOCKED, AuditState.FAIL
        }:
            raise ValueError("dataset with unverified adoption requirements cannot have an adoptable audit state")

    @property
    def adoption_state(self) -> AuditState:
        if self.license.adoption_blocked:
            return AuditState.BLOCKED
        return self.audit.state if self.audit else AuditState.PASS_WITH_WARNINGS
