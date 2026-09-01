from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


def _nms(boxes, scores, iou_threshold=0.45):
    if boxes is None or len(boxes) == 0:
        return []
    order = np.argsort(scores)[::-1]
    keep = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(boxes[i][0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i][1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i][2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i][3], boxes[order[1:], 3])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        area_i = (boxes[i][2] - boxes[i][0]) * (boxes[i][3] - boxes[i][1])
        area_j = (boxes[order[1:], 2] - boxes[order[1:], 0]) * (
            boxes[order[1:], 3] - boxes[order[1:], 1]
        )
        iou = inter / np.maximum(area_i + area_j - inter, 1e-6)
        order = order[1:][iou <= iou_threshold]
    return keep


class Detector(Protocol):
    def detect(self, image: np.ndarray) -> list[tuple[list[int], float]]: ...


class Recognizer(Protocol):
    def recognize(self, crop: np.ndarray) -> tuple[str, float]: ...


class EmptyDetector:
    def detect(self, image: np.ndarray) -> list[tuple[list[int], float]]:
        return [([0, 0, image.shape[1], image.shape[0]], 1.0)]


class YoloDetector:
    def __init__(self, model_path: Path, confidence: float):
        self.confidence = confidence
        suffix = model_path.suffix.lower()
        if suffix == ".onnx":
            import onnxruntime as ort

            self.session = ort.InferenceSession(
                str(model_path), providers=["CPUExecutionProvider"]
            )
            self.mode = "onnx"
        else:
            from ultralytics import YOLO

            self.model = YOLO(str(model_path), task="detect")
            self.mode = "ultralytics"

    def detect(self, image: np.ndarray) -> list[tuple[list[int], float]]:
        if self.mode == "ultralytics":
            result = self.model.predict(
                image, conf=self.confidence, device="cpu", verbose=False
            )[0]
            return [
                ([int(v) for v in box.xyxy[0].tolist()], float(box.conf[0]))
                for box in result.boxes
            ]
        input_meta = self.session.get_inputs()[0]
        shape = input_meta.shape
        size = int(shape[-1]) if isinstance(shape[-1], int) else 640
        height, width = image.shape[:2]
        scale = min(size / width, size / height)
        resized = cv2.resize(image, (round(width * scale), round(height * scale)))
        canvas = np.full((size, size, 3), 114, dtype=np.uint8)
        pad_x = (size - resized.shape[1]) // 2
        pad_y = (size - resized.shape[0]) // 2
        canvas[pad_y : pad_y + resized.shape[0], pad_x : pad_x + resized.shape[1]] = (
            resized
        )
        tensor = canvas[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        raw = self.session.run(None, {input_meta.name: tensor})[0]
        predictions = np.asarray(raw)
        if predictions.ndim != 3:
            raise RuntimeError("YOLO ONNX output must be a 3D tensor")
        predictions = (
            predictions[0].T
            if predictions.shape[1] < predictions.shape[2]
            else predictions[0]
        )
        if predictions.shape[1] < 5:
            raise RuntimeError("YOLO ONNX output has no class scores")
        cxcywh = predictions[:, :4]
        # Ultralytics OBB single-class exports are [xywh, confidence, angle].
        # The angle is not needed for the rectangular OCR crop.
        scores = (
            predictions[:, 4]
            if predictions.shape[1] == 6
            else predictions[:, 4:].max(axis=1)
        )
        mask = scores >= self.confidence
        cxcywh, scores = cxcywh[mask], scores[mask]
        if not len(cxcywh):
            return []
        boxes = np.column_stack(
            (
                cxcywh[:, 0] - cxcywh[:, 2] / 2,
                cxcywh[:, 1] - cxcywh[:, 3] / 2,
                cxcywh[:, 0] + cxcywh[:, 2] / 2,
                cxcywh[:, 1] + cxcywh[:, 3] / 2,
            )
        )
        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad_x) / scale
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad_y) / scale
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, width)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, height)
        return [
            (boxes[i].astype(int).tolist(), float(scores[i]))
            for i in _nms(boxes, scores)
        ]


class EmptyRecognizer:
    def recognize(self, crop: np.ndarray) -> tuple[str, float]:
        return "", 0.0


class PaddleEditCTCRecognizer:
    """CPU fallback for the supplied PaddleOCR-style EditCTC checkpoint."""

    def __init__(
        self,
        code_dir: Path,
        config_path: Path,
        checkpoint_path: Path,
        dictionary_path: Path | None = None,
    ):
        sys.path.insert(0, str(code_dir))
        import paddle
        import yaml
        from ppocr.data import create_operators, transform
        from ppocr.modeling.architectures import build_model
        from ppocr.postprocess import build_post_process
        from ppocr.utils.save_load import load_model

        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["Global"]["pretrained_model"] = None
        config["Global"]["checkpoints"] = str(checkpoint_path)
        if dictionary_path and dictionary_path.exists():
            config["Global"]["character_dict_path"] = str(dictionary_path)
        config["Global"]["use_gpu"] = False
        post_process = build_post_process(config["PostProcess"], config["Global"])
        char_num = len(post_process.character)
        config["Architecture"]["Head"]["out_channels_list"] = {
            "CTCLabelDecode": char_num,
            "NRTRLabelDecode": char_num + 3,
        }
        self.model = build_model(config["Architecture"])
        load_model(config, self.model, model_type=config["Architecture"]["model_type"])
        self.model.eval()
        transforms = []
        for op in config["Eval"]["dataset"]["transforms"]:
            name = next(iter(op))
            if "Label" in name:
                continue
            if name == "RecResizeImg":
                op[name]["infer_mode"] = True
            if name == "KeepKeys":
                op[name]["keep_keys"] = ["image"]
            transforms.append(op)
        config["Global"]["infer_mode"] = True
        self.ops = create_operators(transforms, config["Global"])
        self.transform = transform
        self.post_process = post_process
        self.paddle = paddle

    def recognize(self, crop: np.ndarray) -> tuple[str, float]:
        ok, encoded = cv2.imencode(".jpg", crop)
        if not ok:
            return "", 0.0
        batch = self.transform({"image": encoded.tobytes()}, self.ops)
        with self.paddle.no_grad():
            preds = self.model(self.paddle.to_tensor(np.expand_dims(batch[0], axis=0)))
        result = self.post_process(preds)
        return (
            (result[0][0], float(result[0][1]))
            if result and len(result[0]) >= 2
            else ("", 0.0)
        )


class OnnxRecognizer:
    def __init__(self, model_path: Path, dictionary: Path | None):
        import onnxruntime as ort

        self.session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        self.dictionary = (
            [line.rstrip("\n") for line in dictionary.open(encoding="utf-8")]
            if dictionary and dictionary.exists()
            else list("0123456789")
        )

    def recognize(self, crop: np.ndarray) -> tuple[str, float]:
        # This is the stable preprocessing contract for the EditCTC export.
        image = cv2.resize(crop, (320, 48)).astype(np.float32) / 255.0
        image = image[:, :, ::-1].transpose(2, 0, 1)[None, ...]
        inputs = self.session.get_inputs()
        outputs = self.session.run(None, {inputs[0].name: image})
        logits = outputs[0][0]
        ids = np.argmax(logits, axis=-1)
        probs = np.max(
            np.exp(logits - logits.max(axis=-1, keepdims=True))
            / np.exp(logits - logits.max(axis=-1, keepdims=True)).sum(
                axis=-1, keepdims=True
            ),
            axis=-1,
        )
        text, scores, previous = [], [], -1
        for idx, score in zip(ids, probs):
            if (
                int(idx) != 0
                and int(idx) != previous
                and int(idx) - 1 < len(self.dictionary)
            ):
                text.append(self.dictionary[int(idx) - 1])
                scores.append(float(score))
            previous = int(idx)
        return "".join(text), float(np.mean(scores)) if scores else 0.0


def load_components(settings):
    detector = (
        EmptyDetector()
        if not settings.yolo_model_path or not settings.yolo_model_path.exists()
        else YoloDetector(settings.yolo_model_path, settings.yolo_confidence)
    )
    recognizer = EmptyRecognizer()
    recognizer_warning = None
    checkpoint_path = settings.editctc_model_path
    checkpoint_exists = bool(
        checkpoint_path
        and (
            checkpoint_path.exists()
            or Path(str(checkpoint_path) + ".pdparams").exists()
        )
    )
    if checkpoint_exists:
        if checkpoint_path.suffix.lower() == ".onnx":
            recognizer = OnnxRecognizer(checkpoint_path, settings.editctc_dict_path)
        elif settings.editctc_config_path and settings.editctc_config_path.exists():
            code_dir = (
                settings.editctc_code_dir
                or settings.editctc_config_path.parent.parent.parent / "code"
            )
            try:
                recognizer = PaddleEditCTCRecognizer(
                    code_dir,
                    settings.editctc_config_path,
                    checkpoint_path,
                    settings.editctc_dict_path,
                )
            except Exception as exc:
                recognizer_warning = f"EditCTC Paddle model unavailable: {exc}"
    warnings = []
    if isinstance(detector, EmptyDetector):
        warnings.append("YOLO model not configured; using full-image crop")
    if recognizer_warning:
        warnings.append(recognizer_warning)
    elif isinstance(recognizer, EmptyRecognizer):
        warnings.append(
            "EditCTC model not configured; set EDITCTC_MODEL_PATH to .onnx or a Paddle checkpoint"
        )
    return detector, recognizer, "; ".join(warnings) or None


def run_pipeline(image: np.ndarray, detector: Detector, recognizer: Recognizer):
    started = time.perf_counter()
    results = []
    for box, confidence in detector.detect(image):
        x1, y1, x2, y2 = [max(0, int(v)) for v in box]
        x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
        if x2 <= x1 or y2 <= y1:
            continue
        text, text_confidence = recognizer.recognize(image[y1:y2, x1:x2])
        results.append(([x1, y1, x2, y2], confidence, text, text_confidence))
    return results, (time.perf_counter() - started) * 1000
