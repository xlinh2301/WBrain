# Container deployment

## ONNX profile (recommended for CPU)

Place exported artifacts at:

- `models/yolo.onnx`
- `models/editctc.onnx`

Then run:

```bash
docker compose up --build
```

Open `http://localhost:8000`. The container exposes only CPU providers. The compose file mounts `models/` read-only.

## Native Paddle fallback

To use the supplied checkpoint instead of ONNX, mount the full EditCTC release into `models/editctc` and set `EDITCTC_MODEL_PATH` to the checkpoint prefix and `EDITCTC_CONFIG_PATH` to its YAML. This is slower and increases image size; ONNX is the production target.

On Windows, browser camera access works on `localhost`; remote camera access requires HTTPS because browsers restrict `getUserMedia` on insecure origins.
