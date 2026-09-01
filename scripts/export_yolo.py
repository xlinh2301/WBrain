"""Export the trained YOLO detector for the ONNX CPU container.

Usage:
  python scripts/export_yolo.py --weights E:\\workspace_research\\workspace5\\workdir_text_det\\outputs\\detect_yolo11m\\train\\weights\\best.pt
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=17)
    args = parser.parse_args()
    if not args.weights.exists():
        raise SystemExit(f"Weights not found: {args.weights}")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Install export dependencies first: pip install ultralytics"
        ) from exc
    model = YOLO(str(args.weights), task="detect")
    output = model.export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=True,
        dynamic=False,
        nms=False,
        device="cpu",
    )
    print(f"Exported: {output}")
    print("Set YOLO_MODEL_PATH to this .onnx file in .env or docker-compose.yml")


if __name__ == "__main__":
    main()
