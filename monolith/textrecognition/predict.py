"""EditCTC ONNX predictor for the monolith module."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import yaml

from .utils import OnnxRuntimeBase


class EditCTCPredictor(OnnxRuntimeBase):
    """EditCTC inference; model-specific config, preprocess and CTC decode only."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        config_path: str | Path | None = None,
    ):
        config_path = Path(
            config_path or Path(__file__).parent / "configs" / "editctc.yaml"
        )
        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        model_path = Path(
            model_path or Path(__file__).parent / self.config["model_path"]
        )
        global_config = self.config.get("Global", {})
        input_config = self.config.get("input", {})
        shape = input_config.get("shape") or global_config.get(
            "d2s_train_image_shape", [3, 48, 320]
        )
        self.channels, self.height, self.width = [int(value) for value in shape]
        dictionary = self.config.get("dictionary") or global_config.get(
            "character_dict_path"
        )
        if dictionary and not Path(dictionary).is_absolute():
            dictionary = str(config_path.parent / dictionary)
        self.dictionary = self._read_dictionary(dictionary)
        super().__init__(model_path)

    @staticmethod
    def _read_dictionary(path: str | None) -> list[str]:
        if not path:
            return list("0123456789")
        candidate = Path(path)
        return (
            [line.rstrip("\n") for line in candidate.open(encoding="utf-8")]
            if candidate.is_file()
            else list("0123456789")
        )

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.ndim != 3:
            raise ValueError("EditCTC expects a BGR image with three channels")
        image_height, image_width = image.shape[:2]
        valid_width = min(
            self.width, max(1, int(np.ceil(self.height * image_width / image_height)))
        )
        resized = cv2.resize(image, (valid_width, self.height)).astype(np.float32)
        resized = resized[:, :, ::-1].transpose(2, 0, 1) / 255.0
        resized = (resized - 0.5) / 0.5
        tensor = np.zeros((self.channels, self.height, self.width), dtype=np.float32)
        tensor[:, :, :valid_width] = resized
        return tensor[None, ...]

    def postprocess(self, outputs: list[np.ndarray]) -> tuple[str, float]:
        logits = np.asarray(outputs[0])[0]
        ids = np.argmax(logits, axis=-1)
        stable = logits - logits.max(axis=-1, keepdims=True)
        probabilities = np.exp(stable)
        probabilities /= probabilities.sum(axis=-1, keepdims=True)
        scores = np.max(probabilities, axis=-1)
        text: list[str] = []
        used_scores: list[float] = []
        previous = -1
        for index, score in zip(ids, scores):
            index = int(index)
            if index != 0 and index != previous and index - 1 < len(self.dictionary):
                text.append(self.dictionary[index - 1])
                used_scores.append(float(score))
            previous = index
        confidence = float(np.mean(used_scores)) if used_scores else 0.0
        return "".join(text), confidence

    def recognize(self, image: np.ndarray) -> tuple[str, float]:
        return self.predict(image)
