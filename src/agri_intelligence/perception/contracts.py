"""Minimal prediction contract for future detector/segmenter adapters."""
from dataclasses import dataclass
from typing import Protocol, Sequence
from agri_intelligence.core.contracts import Prediction

@dataclass(frozen=True)
class ImageFrame:
    image_id: str
    width: int
    height: int

class PerceptionModel(Protocol):
    def predict(self, frame: ImageFrame) -> Sequence[Prediction]: ...
