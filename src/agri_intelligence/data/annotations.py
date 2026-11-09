"""Pure validation helpers for detection annotation records."""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Any, Iterable, Mapping

from .contracts import AuditFinding


@dataclass(frozen=True)
class AnnotationAudit:
    findings: tuple[AuditFinding, ...]


_COORDINATE_MODES = {
    "absolute_xywh", "normalized_xywh", "absolute_xyxy", "normalized_xyxy"
}


def audit_detection_records(
    records: Iterable[Mapping[str, Any]],
    image_sizes: Mapping[str, tuple[int, int]],
    classes: set[str],
    coordinate_mode: str = "absolute_xywh",
) -> AnnotationAudit:
    findings: list[AuditFinding] = []
    if not isinstance(coordinate_mode, str) or coordinate_mode not in _COORDINATE_MODES:
        return AnnotationAudit((AuditFinding(
            "unsupported_coordinate_mode", "error",
            f"unsupported coordinate mode: {coordinate_mode!r}"
        ),))

    seen: set[str] = set()
    referenced_images: set[str] = set()
    valid_sizes: dict[str, tuple[int, int]] = {}

    for image_id, dimensions in image_sizes.items():
        if (
            not isinstance(image_id, str)
            or not image_id.strip()
            or not isinstance(dimensions, (tuple, list))
            or len(dimensions) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in dimensions)
        ):
            findings.append(AuditFinding(
                "invalid_image_dimensions", "error",
                f"image {image_id!r} has invalid width/height metadata", str(image_id)
            ))
            continue
        valid_sizes[image_id] = (dimensions[0], dimensions[1])

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            findings.append(AuditFinding(
                "invalid_annotation_record", "error",
                f"record {index} is not a mapping"
            ))
            continue

        raw_ann_id = record.get("id")
        ann_id = str(raw_ann_id).strip() if raw_ann_id is not None else ""
        raw_image_id = record.get("image_id")
        image_id = str(raw_image_id).strip() if raw_image_id is not None else ""

        if not ann_id:
            findings.append(AuditFinding("missing_annotation_id", "error", f"record {index} has no id"))
        elif ann_id in seen:
            findings.append(AuditFinding(
                "duplicate_annotation_id", "error", f"duplicate annotation id: {ann_id}", ann_id
            ))
        seen.add(ann_id)

        if image_id not in valid_sizes:
            findings.append(AuditFinding(
                "annotation_without_image", "error", f"unknown or invalid image: {image_id}", ann_id or None
            ))
            continue
        referenced_images.add(image_id)

        bbox = record.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            findings.append(AuditFinding(
                "invalid_bbox", "error",
                f"annotation {ann_id or index} must have four coordinates", ann_id or None
            ))
            continue
        if any(isinstance(v, bool) or not isinstance(v, Real) or not math.isfinite(float(v)) for v in bbox):
            findings.append(AuditFinding(
                "invalid_bbox_values", "error",
                f"annotation {ann_id or index} has non-numeric or non-finite coordinates", ann_id or None
            ))
            continue

        c1, c2, c3, c4 = (float(v) for v in bbox)
        image_width, image_height = valid_sizes[image_id]
        if coordinate_mode == "absolute_xywh":
            x1, y1, x2, y2 = c1, c2, c1 + c3, c2 + c4
        elif coordinate_mode == "normalized_xywh":
            x1, y1 = c1 * image_width, c2 * image_height
            x2, y2 = (c1 + c3) * image_width, (c2 + c4) * image_height
        elif coordinate_mode == "absolute_xyxy":
            x1, y1, x2, y2 = c1, c2, c3, c4
        else:  # normalized_xyxy
            x1, y1 = c1 * image_width, c2 * image_height
            x2, y2 = c3 * image_width, c4 * image_height

        if x2 <= x1 or y2 <= y1:
            findings.append(AuditFinding(
                "non_positive_bbox", "error",
                f"annotation {ann_id or index} has non-positive dimensions", ann_id or None
            ))
            continue
        if x1 < 0 or y1 < 0 or x2 > image_width or y2 > image_height:
            findings.append(AuditFinding(
                "bbox_out_of_bounds", "error",
                f"annotation {ann_id or index} exceeds image bounds", ann_id or None
            ))

        label = record.get("category")
        if not isinstance(label, str) or label not in classes:
            findings.append(AuditFinding(
                "unknown_class", "error", f"unknown class: {label!r}", ann_id or None
            ))

    for image_id in valid_sizes:
        if image_id not in referenced_images:
            findings.append(AuditFinding(
                "image_without_annotations", "warning",
                f"image has no annotations: {image_id}", image_id
            ))
    return AnnotationAudit(tuple(findings))
