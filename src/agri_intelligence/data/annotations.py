"""Pure validation helpers for detection annotation records."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable, Mapping
from .contracts import AuditFinding

@dataclass(frozen=True)
class AnnotationAudit: findings: tuple[AuditFinding, ...]

def audit_detection_records(records: Iterable[Mapping[str, Any]], image_sizes: Mapping[str, tuple[int, int]], classes: set[str]) -> AnnotationAudit:
    findings: list[AuditFinding] = []
    seen: set[str] = set()
    referenced_images: set[str] = set()
    for index, record in enumerate(records):
        ann_id = str(record.get("id", ""))
        image_id = str(record.get("image_id", ""))
        if not ann_id:
            findings.append(AuditFinding("missing_annotation_id", "error", f"record {index} has no id"))
        elif ann_id in seen:
            findings.append(AuditFinding("duplicate_annotation_id", "error", f"duplicate annotation id: {ann_id}"))
        seen.add(ann_id)
        if image_id not in image_sizes:
            findings.append(AuditFinding("annotation_without_image", "error", f"unknown image: {image_id}", ann_id or None))
            continue
        referenced_images.add(image_id)
        bbox = record.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            findings.append(AuditFinding("invalid_bbox", "error", f"annotation {ann_id} must have [x,y,width,height]", ann_id or None))
            continue
        x, y, width, height = bbox
        if width <= 0 or height <= 0:
            findings.append(AuditFinding("non_positive_bbox", "error", f"annotation {ann_id} has non-positive dimensions", ann_id or None))
        image_width, image_height = image_sizes[image_id]
        if x < 0 or y < 0 or x + width > image_width or y + height > image_height:
            findings.append(AuditFinding("bbox_out_of_bounds", "error", f"annotation {ann_id} exceeds image bounds", ann_id or None))
        label = record.get("category")
        if label not in classes:
            findings.append(AuditFinding("unknown_class", "error", f"unknown class: {label}", ann_id or None))
    for image_id in image_sizes:
        if image_id not in referenced_images:
            findings.append(AuditFinding("image_without_annotations", "warning", f"image has no annotations: {image_id}", image_id))
    return AnnotationAudit(tuple(findings))
