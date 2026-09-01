"""Small ONNX Runtime base used by monolith predictors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort


def nms_xyxy(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    order = np.argsort(scores)[::-1]
    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(boxes[current, 0], boxes[rest, 0])
        yy1 = np.maximum(boxes[current, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[current, 2], boxes[rest, 2])
        yy2 = np.minimum(boxes[current, 3], boxes[rest, 3])
        intersection = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        area_current = (boxes[current, 2] - boxes[current, 0]) * (
            boxes[current, 3] - boxes[current, 1]
        )
        area_rest = (boxes[rest, 2] - boxes[rest, 0]) * (
            boxes[rest, 3] - boxes[rest, 1]
        )
        iou = intersection / np.maximum(area_current + area_rest - intersection, 1e-6)
        order = rest[iou <= iou_threshold]
    return keep


class OnnxRuntimeBase(ABC):
    """Template for predictors with model-specific pre/post-processing only."""

    def __init__(self, model_path: str | Path, providers: list[str] | None = None):
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {self.model_path}")
        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=providers or ["CPUExecutionProvider"],
        )
        if not self.session.get_inputs():
            raise RuntimeError(f"ONNX model has no inputs: {self.model_path}")
        self.input_name = self.session.get_inputs()[0].name

    @abstractmethod
    def preprocess(self, image: Any):
        """Convert a project input into the ONNX input tensor."""

    @abstractmethod
    def postprocess(self, outputs: list[Any]):
        """Convert ONNX outputs into the public prediction format."""

    def predict(self, image: Any):
        tensor = self.preprocess(image)
        outputs = self.session.run(None, {self.input_name: tensor})
        return self.postprocess(outputs)
