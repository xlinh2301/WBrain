# Monolith model modules

```text
monolith/
├── textdetection/
│   ├── configs/
│   ├── model/model.onnx
│   ├── utils.py
│   └── predict.py
└── textrecognition/
    ├── configs/
    ├── model/model.onnx
    ├── utils.py
    └── predict.py
```

Each module is standalone. `predict.py` inherits the ONNX Runtime base from
its local `utils.py`; only model-specific config, preprocessing and
postprocessing live in the predictor. Model artifacts are deliberately ignored
from Git and are supplied by the release build.
