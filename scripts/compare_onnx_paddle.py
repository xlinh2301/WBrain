from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import paddle
import yaml

repo = Path(sys.argv[1])
workdir = Path(sys.argv[2])
code_dir = workdir / "release_EditCTC" / "code"
config_path = workdir / "Checkpoint" / "EditCTC" / "s1024" / "config.yml"
checkpoint = config_path.parent / "best_accuracy"
dictionary_path = code_dir / "ppocr" / "utils" / "dict" / "ppocrv6_dict.txt"
onnx_path = repo / "monolith" / "textrecognition" / "model" / "model.onnx"
images_dir = workdir / "Data" / "Indomain" / "crops" / "test"

sys.path.insert(0, str(code_dir))
from ppocr.modeling.architectures import build_model
from ppocr.postprocess import build_post_process
from ppocr.utils.save_load import load_model

config = yaml.safe_load(config_path.read_text())
config["Global"]["pretrained_model"] = None
config["Global"]["checkpoints"] = str(checkpoint)
config["Global"]["character_dict_path"] = str(dictionary_path)
config["Global"]["use_gpu"] = False
post = build_post_process(config["PostProcess"], config["Global"])
chars = len(post.character)
config["Architecture"]["Head"]["out_channels_list"] = {
    "CTCLabelDecode": chars,
    "NRTRLabelDecode": chars + 3,
}
paddle_model = build_model(config["Architecture"])
load_model(config, paddle_model, model_type=config["Architecture"]["model_type"])
paddle_model.eval()
onnx_model = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
input_name = onnx_model.get_inputs()[0].name


def preprocess(image):
    # Fixed-width equivalent of PaddleOCR RecResizeImg used by the model.
    h, w = image.shape[:2]
    valid_w = min(320, max(1, int(np.ceil(48 * w / float(h)))))
    resized = cv2.resize(image, (valid_w, 48)).astype("float32")
    resized = resized[:, :, ::-1].transpose(2, 0, 1) / 255.0
    resized = (resized - 0.5) / 0.5
    result = np.zeros((3, 48, 320), dtype="float32")
    result[:, :, :valid_w] = resized
    return result


def decode(logits):
    ids = logits.argmax(axis=-1)
    if np.all(logits >= 0) and np.allclose(logits.sum(axis=-1), 1.0, atol=1e-3):
        probs = logits
    else:
        probs = np.exp(logits - logits.max(axis=-1, keepdims=True))
        probs /= probs.sum(axis=-1, keepdims=True)
    text, conf, previous = [], [], -1
    for idx, probability in zip(ids, probs.max(axis=-1)):
        idx = int(idx)
        if idx and idx != previous and idx - 1 < len(post.character):
            text.append(post.character[idx - 1])
            conf.append(float(probability))
        previous = idx
    return "".join(text), float(np.mean(conf)) if conf else 0.0


labels = {}
label_path = images_dir.parent / "test_label.txt"
for line in label_path.read_text(encoding="utf-8").splitlines():
    name, label = line.split("\t", 1)
    labels[name] = label
paths = sorted(
    p for p in images_dir.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
)[:500]
rows = []
for path in paths:
    image = cv2.imread(str(path))
    if image is None:
        continue
    tensor = preprocess(image)
    with paddle.no_grad():
        paddle_out = paddle_model(paddle.to_tensor(tensor[None]))
    paddle_ctc = (
        paddle_out["ctc"].numpy()[0]
        if isinstance(paddle_out, dict)
        else paddle_out.numpy()[0]
    )
    paddle_text, paddle_conf = decode(paddle_ctc)
    onnx_out = onnx_model.run(None, {input_name: tensor[None]})[0][0]
    onnx_text, onnx_conf = decode(onnx_out)
    rows.append(
        {
            "file": path.name,
            "label": labels.get(path.name),
            "paddle": paddle_text,
            "onnx": onnx_text,
            "paddle_conf": paddle_conf,
            "onnx_conf": onnx_conf,
        }
    )

same = sum(row["paddle"] == row["onnx"] for row in rows)
paddle_correct = sum(
    row["label"] is not None and row["paddle"] == row["label"] for row in rows
)
onnx_correct = sum(
    row["label"] is not None and row["onnx"] == row["label"] for row in rows
)
print(
    json.dumps(
        {
            "n": len(rows),
            "preview": rows[:20],
            "label_matches": sum(row["label"] is not None for row in rows),
            "same": same,
            "same_rate": same / len(rows) if rows else 0,
            "paddle_exact": paddle_correct,
            "onnx_exact": onnx_correct,
            "paddle_accuracy": paddle_correct / len(rows) if rows else 0,
            "onnx_accuracy": onnx_correct / len(rows) if rows else 0,
            "avg_conf_delta": float(
                np.mean([abs(r["paddle_conf"] - r["onnx_conf"]) for r in rows])
            )
            if rows
            else 0,
            "diff_examples": [r for r in rows if r["paddle"] != r["onnx"]][:20],
            "label_examples": [r for r in rows if r["label"] is not None][:20],
        },
        ensure_ascii=False,
        indent=2,
    )
)
