"""Small ONNX Runtime base used by monolith predictors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import onnxruntime as ort


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
