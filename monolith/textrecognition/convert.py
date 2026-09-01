"""Export the custom Paddle EditCTC checkpoint to ONNX.

Run this in an environment containing the checkpoint's Paddle code,
PaddlePaddle and paddle2onnx. The source checkpoint is never copied into Git.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument(
        "--ctc-only",
        action="store_true",
        help="export backbone + CTC branch and skip NumPy-based EditRefine",
    )
    return parser.parse_args()


def build_model(
    code_dir: Path,
    config_path: Path,
    checkpoint: Path,
    dictionary: Path,
    ctc_only: bool = False,
):
    import sys

    sys.path.insert(0, str(code_dir))
    import paddle
    import yaml
    from ppocr.modeling.architectures import build_model
    from ppocr.postprocess import build_post_process
    from ppocr.utils.save_load import load_model

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["Global"]["pretrained_model"] = None
    config["Global"]["checkpoints"] = str(checkpoint)
    config["Global"]["character_dict_path"] = str(dictionary)
    config["Global"]["use_gpu"] = False
    post_process = build_post_process(config["PostProcess"], config["Global"])
    char_num = len(post_process.character)
    config["Architecture"]["Head"]["out_channels_list"] = {
        "CTCLabelDecode": char_num,
        "NRTRLabelDecode": char_num + 3,
    }
    model = build_model(config["Architecture"])
    load_model(config, model, model_type=config["Architecture"]["model_type"])
    model.eval()
    if ctc_only:

        class CTCExport(paddle.nn.Layer):
            def __init__(self, source):
                super().__init__()
                self.source = source

            def forward(self, x):
                if self.source.use_transform:
                    x = self.source.transform(x)
                x = self.source.backbone(x)
                if self.source.use_neck:
                    x = self.source.neck(x)
                encoder = self.source.head.ctc_encoder(x)
                # Return logits, not eval-time softmax, for stable ONNX decode.
                return self.source.head.ctc_head.fc(encoder)

        model = CTCExport(model)
    static_model = paddle.jit.to_static(
        model,
        full_graph=True,
        input_spec=[paddle.static.InputSpec([None, 3, 48, 320], "float32")],
    )
    return static_model


def main() -> None:
    args = parse_args()
    for path in (args.code_dir, args.config, args.dictionary):
        if not path.exists():
            raise FileNotFoundError(path)
    checkpoint = args.checkpoint
    if not checkpoint.exists() and Path(f"{checkpoint}.pdparams").exists():
        checkpoint = Path(f"{checkpoint}.pdparams")
    if not checkpoint.exists():
        raise FileNotFoundError(checkpoint)
    if shutil.which("paddle2onnx") is None:
        raise RuntimeError(
            "paddle2onnx CLI is required; install it in the export environment"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    export_dir = args.output.parent / f"_{args.output.stem}_paddle"
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir()
    paddle_prefix = export_dir / "model"
    model = build_model(
        args.code_dir,
        args.config,
        checkpoint,
        args.dictionary,
        ctc_only=args.ctc_only,
    )
    import paddle

    paddle.jit.save(model, str(paddle_prefix))
    model_filename = (
        "model.json" if (export_dir / "model.json").is_file() else "model.pdmodel"
    )
    command = [
        "paddle2onnx",
        "--model_dir",
        str(export_dir),
        "--model_filename",
        model_filename,
        "--params_filename",
        "model.pdiparams",
        "--save_file",
        str(args.output),
        "--opset_version",
        str(args.opset),
        "--enable_onnx_checker",
        "True",
    ]
    subprocess.run(command, check=True)
    if not args.output.is_file() or args.output.stat().st_size == 0:
        raise RuntimeError(
            f"ONNX export did not produce a valid artifact: {args.output}"
        )
    print(f"Exported ONNX: {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
