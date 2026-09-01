import Busboy from "busboy";
import jpeg from "jpeg-js";
import { PNG } from "pngjs";
import * as ort from "onnxruntime-node";
import { randomUUID } from "node:crypto";

export const config = { api: { bodyParser: false, sizeLimit: "4.5mb" } };

const YOLO = "monolith/textdetection/model/model.onnx";
const OCR = "monolith/textrecognition/model/model.onnx";
const DICTIONARY = "monolith/textrecognition/model/dictionary.txt";
let detectorPromise;
let recognizerPromise;
let dictionaryPromise;

function requestId(req) {
  return req.headers["x-request-id"] || randomUUID();
}

function send(res, status, body, id) {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("X-Request-ID", id);
  return res.status(status).json(body);
}

function readMultipart(req) {
  return new Promise((resolve, reject) => {
    const contentType = req.headers["content-type"] || "";
    if (!contentType.startsWith("multipart/form-data"))
      return reject(new Error("multipart/form-data is required"));
    const parser = Busboy({
      headers: req.headers,
      limits: { files: 1, fileSize: 4 * 1024 * 1024 },
    });
    const chunks = [];
    let fileSeen = false;
    parser.on("file", (_name, file) => {
      fileSeen = true;
      file.on("data", (chunk) => chunks.push(chunk));
      file.on("limit", () => reject(new Error("image exceeds 4 MB")));
    });
    parser.on("finish", () =>
      fileSeen
        ? resolve(Buffer.concat(chunks))
        : reject(new Error("image file is required")),
    );
    parser.on("error", reject);
    req.pipe(parser);
  });
}

function decodeImage(buffer) {
  if (buffer[0] === 0xff && buffer[1] === 0xd8) {
    const decoded = jpeg.decode(buffer, { useTArray: true });
    return { data: decoded.data, width: decoded.width, height: decoded.height };
  }
  if (buffer[0] === 0x89 && buffer.toString("ascii", 1, 4) === "PNG") {
    const decoded = PNG.sync.read(buffer);
    return { data: decoded.data, width: decoded.width, height: decoded.height };
  }
  throw new Error("only JPEG and PNG images are supported");
}

function letterbox(image, size = 640) {
  const scale = Math.min(size / image.width, size / image.height);
  const width = Math.max(1, Math.round(image.width * scale));
  const height = Math.max(1, Math.round(image.height * scale));
  const canvas = new Uint8Array(size * size * 3).fill(114);
  const sx = image.width / width;
  const sy = image.height / height;
  const padX = Math.floor((size - width) / 2);
  const padY = Math.floor((size - height) / 2);
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const source =
        (Math.floor(y * sy) * image.width + Math.floor(x * sx)) * 4;
      const target = (padY + y) * size * 3 + (padX + x) * 3;
      canvas[target] = image.data[source];
      canvas[target + 1] = image.data[source + 1];
      canvas[target + 2] = image.data[source + 2];
    }
  const tensor = new Float32Array(3 * size * size);
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) {
      const source = (y * size + x) * 3;
      tensor[y * size + x] = canvas[source] / 255;
      tensor[size * size + y * size + x] = canvas[source + 1] / 255;
      tensor[2 * size * size + y * size + x] = canvas[source + 2] / 255;
    }
  return { tensor, scale, padX, padY };
}

function nms(boxes, scores, threshold = 0.45) {
  const order = scores.map((_, i) => i).sort((a, b) => scores[b] - scores[a]);
  const keep = [];
  while (order.length) {
    const current = order.shift();
    keep.push(current);
    for (let i = order.length - 1; i >= 0; i--) {
      const other = order[i];
      const x1 = Math.max(boxes[current][0], boxes[other][0]);
      const y1 = Math.max(boxes[current][1], boxes[other][1]);
      const x2 = Math.min(boxes[current][2], boxes[other][2]);
      const y2 = Math.min(boxes[current][3], boxes[other][3]);
      const intersection = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
      const areaA =
        Math.max(0, boxes[current][2] - boxes[current][0]) *
        Math.max(0, boxes[current][3] - boxes[current][1]);
      const areaB =
        Math.max(0, boxes[other][2] - boxes[other][0]) *
        Math.max(0, boxes[other][3] - boxes[other][1]);
      if (
        intersection / Math.max(areaA + areaB - intersection, 1e-6) >
        threshold
      )
        order.splice(i, 1);
    }
  }
  return keep;
}

async function load() {
  detectorPromise ||= ort.InferenceSession.create(`${process.cwd()}/${YOLO}`, {
    executionProviders: ["cpu"],
  });
  recognizerPromise ||= ort.InferenceSession.create(`${process.cwd()}/${OCR}`, {
    executionProviders: ["cpu"],
  });
  dictionaryPromise ||= import("node:fs/promises")
    .then((fs) => fs.readFile(`${process.cwd()}/${DICTIONARY}`, "utf8"))
    .then((text) => text.split(/\r?\n/).filter(Boolean));
  return Promise.all([detectorPromise, recognizerPromise, dictionaryPromise]);
}

function detect(output, image, prepared, confidence = 0.35) {
  const values = output.data;
  const count = output.dims[2];
  const boxes = [];
  const scores = [];
  for (let i = 0; i < count; i++) {
    const score = values[count * 4 + i];
    if (score < confidence) continue;
    const cx = values[i],
      cy = values[count + i],
      width = values[count * 2 + i],
      height = values[count * 3 + i];
    boxes.push([
      Math.max(
        0,
        Math.min(
          image.width,
          (cx - width / 2 - prepared.padX) / prepared.scale,
        ),
      ),
      Math.max(
        0,
        Math.min(
          image.height,
          (cy - height / 2 - prepared.padY) / prepared.scale,
        ),
      ),
      Math.max(
        0,
        Math.min(
          image.width,
          (cx + width / 2 - prepared.padX) / prepared.scale,
        ),
      ),
      Math.max(
        0,
        Math.min(
          image.height,
          (cy + height / 2 - prepared.padY) / prepared.scale,
        ),
      ),
    ]);
    scores.push(score);
  }
  return nms(boxes, scores).map((index) => ({
    box: boxes[index].map(Math.round),
    confidence: Number(scores[index].toFixed(4)),
  }));
}

function crop(image, box) {
  const [x1, y1, x2, y2] = box;
  const width = Math.max(1, x2 - x1),
    height = Math.max(1, y2 - y1);
  const data = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const source = ((y1 + y) * image.width + x1 + x) * 4;
      const target = (y * width + x) * 4;
      data[target] = image.data[source];
      data[target + 1] = image.data[source + 1];
      data[target + 2] = image.data[source + 2];
      data[target + 3] = 255;
    }
  return { data, width, height };
}

function ocrTensor(image) {
  const width = 320,
    height = 48;
  const tensor = new Float32Array(3 * width * height);
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const source =
        (Math.floor((y * image.height) / height) * image.width +
          Math.floor((x * image.width) / width)) *
        4;
      tensor[y * width + x] = image.data[source] / 255;
      tensor[width * height + y * width + x] = image.data[source + 1] / 255;
      tensor[2 * width * height + y * width + x] = image.data[source + 2] / 255;
    }
  return tensor;
}

function firstTensor(outputs, outputNames, label) {
  const names = outputNames || Object.keys(outputs || {});
  const tensor = Array.isArray(outputs)
    ? outputs[0]
    : names.length
      ? outputs instanceof Map
        ? outputs.get(names[0])
        : outputs[names[0]]
      : null;
  if (!tensor || !tensor.data)
    throw new Error(
      `${label} output unavailable: ${names.join(",") || "no output"}`,
    );
  return tensor;
}

function decodeOcr(output, dictionary) {
  const values = output.data,
    steps = output.dims[1],
    classes = output.dims[2];
  const ids = [];
  let confidence = 0,
    previous = -1;
  for (let step = 0; step < steps; step++) {
    let best = 0,
      bestValue = -Infinity;
    for (let cls = 0; cls < classes; cls++) {
      const value = values[step * classes + cls];
      if (value > bestValue) {
        bestValue = value;
        best = cls;
      }
    }
    const id = best;
    if (id !== 0 && id !== previous && dictionary[id - 1]) {
      ids.push(dictionary[id - 1]);
      confidence += 1 / steps;
    }
    previous = id;
  }
  return { text: ids.join(""), confidence: Number(confidence.toFixed(4)) };
}

export default async function handler(req, res) {
  const id = requestId(req);
  const apiKey = process.env.API_KEY;
  if (apiKey && req.headers["x-api-key"] !== apiKey)
    return send(
      res,
      401,
      {
        error: {
          code: "WBRAIN-AUTH-001",
          message: "authentication required",
          request_id: id,
        },
      },
      id,
    );
  if (req.method !== "POST")
    return send(
      res,
      405,
      {
        error: {
          code: "WBRAIN-HTTP-405",
          message: "POST required",
          request_id: id,
        },
      },
      id,
    );
  try {
    const [detector, recognizer, dictionary] = await load();
    const image = decodeImage(await readMultipart(req));
    const prepared = letterbox(image);
    const detected = await detector.run({
      images: new ort.Tensor("float32", prepared.tensor, [1, 3, 640, 640]),
    });
    const boxes = detect(
      firstTensor(detected, detector.outputNames, "detector"),
      image,
      prepared,
    );
    const crops = [];
    for (const detection of boxes) {
      const result = await recognizer.run({
        x: new ort.Tensor(
          "float32",
          ocrTensor(crop(image, detection.box)),
          [1, 3, 48, 320],
        ),
      });
      const text = decodeOcr(
        firstTensor(result, recognizer.outputNames, "recognizer"),
        dictionary,
      );
      crops.push({
        ...detection,
        text: text.text,
        text_confidence: text.confidence,
      });
    }
    return send(
      res,
      200,
      {
        request_id: id,
        processing_ms: 0,
        crops,
        warning: "Vercel ONNX demo: no persistence",
        reading_id: null,
        reading_status: crops.length ? "accepted" : "review_required",
      },
      id,
    );
  } catch (error) {
    return send(
      res,
      500,
      {
        error: {
          code: "WBRAIN-INFERENCE-500",
          message: error.message,
          request_id: id,
        },
      },
      id,
    );
  }
}
