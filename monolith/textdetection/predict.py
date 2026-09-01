"""YOLO ONNX text detection predictor."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import yaml

from .utils import OnnxRuntimeBase, nms_xyxy


class TextDetectionPredictor(OnnxRuntimeBase):
    """YOLO detector with model-specific letterbox and box decoding."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        config_path: str | Path | None = None,
    ):
        config_path = Path(
            config_path or Path(__file__).parent / "configs" / "yolo.yaml"
        )
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        model_path = Path(
            model_path or Path(__file__).parent / self.config["model_path"]
        )
        input_config = self.config.get("input", {})
        self.size = int(input_config.get("size", 640))
        postprocess = self.config.get("postprocess", {})
        self.confidence = float(postprocess.get("confidence", 0.35))
        self.iou = float(postprocess.get("iou", 0.45))
        super().__init__(model_path)

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.ndim != 3:
            raise ValueError("text detection expects a BGR image")
        height, width = image.shape[:2]
        scale = min(self.size / width, self.size / height)
        resized = cv2.resize(image, (round(width * scale), round(height * scale)))
        canvas = np.full((self.size, self.size, 3), 114, dtype=np.uint8)
        pad_x = (self.size - resized.shape[1]) // 2
        pad_y = (self.size - resized.shape[0]) // 2
        canvas[pad_y : pad_y + resized.shape[0], pad_x : pad_x + resized.shape[1]] = (
            resized
        )
        self._shape = (width, height, scale, pad_x, pad_y)
        tensor = canvas[:, :, ::-1].transpose(2, 0, 1)
        return (tensor.astype(np.float32) / 255.0)[None, ...]

    def postprocess(self, outputs: list[np.ndarray]) -> list[tuple[list[int], float]]:
        predictions = np.asarray(outputs[0])
        if predictions.ndim != 3:
            raise RuntimeError("YOLO ONNX output must be a 3D tensor")
        predictions = (
            predictions[0].T
            if predictions.shape[1] < predictions.shape[2]
            else predictions[0]
        )
        if predictions.shape[1] < 5:
            raise RuntimeError("YOLO ONNX output has no confidence scores")
        scores = (
            predictions[:, 4]
            if predictions.shape[1] == 6
            else predictions[:, 4:].max(axis=1)
        )
        mask = scores >= self.confidence
        boxes = predictions[mask, :4]
        scores = scores[mask]
        if not len(boxes):
            return []
        width, height, scale, pad_x, pad_y = self._shape
        xyxy = np.column_stack(
            (
                boxes[:, 0] - boxes[:, 2] / 2,
                boxes[:, 1] - boxes[:, 3] / 2,
                boxes[:, 0] + boxes[:, 2] / 2,
                boxes[:, 1] + boxes[:, 3] / 2,
            )
        )
        xyxy[:, [0, 2]] = np.clip((xyxy[:, [0, 2]] - pad_x) / scale, 0, width)
        xyxy[:, [1, 3]] = np.clip((xyxy[:, [1, 3]] - pad_y) / scale, 0, height)
        keep = nms_xyxy(xyxy, scores, self.iou)
        return [
            (xyxy[index].astype(int).tolist(), float(scores[index])) for index in keep
        ]

    def detect(self, image: np.ndarray) -> list[tuple[list[int], float]]:
        return self.predict(image)
