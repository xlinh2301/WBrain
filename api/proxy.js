import { randomUUID } from "node:crypto";

export const config = { api: { bodyParser: false } };

const memory = {
  meters: [],
  readings: [],
};

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks);
}

function requestId(req) {
  return req.headers["x-request-id"] || randomUUID();
}

function json(res, status, body, id) {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("X-Request-ID", id);
  return res.status(status).json(body);
}

function demoEnabled(backend) {
  return (
    process.env.WBRAIN_DEMO_MODE === "1" ||
    (!backend && process.env.VERCEL === "1")
  );
}

async function demoHandler(req, res, path, id) {
  const key = process.env.API_KEY;
  if (key && req.headers["x-api-key"] !== key)
    return json(
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

  if (path === "/api/v1/health" && req.method === "GET")
    return json(
      res,
      200,
      {
        status: "ok",
        device: "serverless-demo",
        warning:
          "demo backend: OCR is simulated; configure WBRAIN_BACKEND_URL for real inference",
        persistence: false,
        request_id: id,
      },
      id,
    );

  if (path === "/api/v1/meters" && req.method === "GET")
    return json(res, 200, memory.meters, id);

  if (path === "/api/v1/meters" && req.method === "POST") {
    let payload = {};
    try {
      payload = JSON.parse((await readBody(req)).toString("utf8") || "{}");
    } catch {
      return json(
        res,
        400,
        {
          error: {
            code: "WBRAIN-API-400",
            message: "invalid JSON",
            request_id: id,
          },
        },
        id,
      );
    }
    if (!payload.serial_number)
      return json(
        res,
        400,
        {
          error: {
            code: "WBRAIN-API-400",
            message: "serial_number is required",
            request_id: id,
          },
        },
        id,
      );
    const meter = {
      id: randomUUID(),
      serial_number: payload.serial_number,
      name: payload.name || null,
      meter_type: payload.meter_type || "water",
      address: payload.address || null,
      status: "active",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    memory.meters.push(meter);
    return json(res, 201, meter, id);
  }

  if (path === "/api/v1/recognize" && req.method === "POST") {
    const body = await readBody(req);
    if (!body.length)
      return json(
        res,
        400,
        {
          error: {
            code: "WBRAIN-IMAGE-001",
            message: "image file is required",
            request_id: id,
          },
        },
        id,
      );
    const result = {
      request_id: id,
      processing_ms: 8.0,
      crops: [
        {
          box: [0, 0, 1, 1],
          confidence: 0.99,
          text: "12345",
          text_confidence: 0.98,
        },
      ],
      warning: "demo backend: OCR is simulated",
      reading_id: null,
      reading_status: "accepted",
    };
    return json(res, 200, result, id);
  }

  if (
    path === "/api/v1/readings" ||
    path === "/api/v1/reviews" ||
    path === "/api/v1/models" ||
    path === "/api/v1/audit"
  )
    return json(res, 200, path.endsWith("readings") ? memory.readings : [], id);

  return json(
    res,
    404,
    {
      error: {
        code: "WBRAIN-HTTP-404",
        message: "route not found in demo backend",
        request_id: id,
      },
    },
    id,
  );
}

export default async function handler(req, res) {
  const backend = process.env.WBRAIN_BACKEND_URL;
  const query = { ...(req.query || {}) };
  const rawPath = query.path;
  const path = Array.isArray(rawPath)
    ? `/${rawPath.join("/")}`
    : typeof rawPath === "string" && rawPath
      ? rawPath.startsWith("/")
        ? rawPath
        : `/${rawPath}`
      : new URL(req.url, "http://vercel.local").pathname;
  const apiPath = path.startsWith("/v1/") ? `/api${path}` : path;
  delete query.path;
  const id = requestId(req);

  if (!backend) {
    if (demoEnabled(backend)) return demoHandler(req, res, apiPath, id);
    return json(
      res,
      503,
      {
        error: {
          code: "WBRAIN-DEPLOY-001",
          message: "inference backend is not configured",
          request_id: id,
        },
      },
      id,
    );
  }

  const queryString = new URLSearchParams(query).toString();
  const target = `${backend.replace(/\/$/, "")}${apiPath}${queryString ? `?${queryString}` : ""}`;
  const headers = { ...req.headers, host: new URL(backend).host };
  delete headers.connection;
  delete headers["content-length"];
  const body = ["GET", "HEAD"].includes(req.method)
    ? undefined
    : await readBody(req);
  try {
    const response = await fetch(target, { method: req.method, headers, body });
    res.status(response.status);
    response.headers.forEach((value, name) => {
      if (!["transfer-encoding", "connection"].includes(name.toLowerCase()))
        res.setHeader(name, value);
    });
    return res.send(Buffer.from(await response.arrayBuffer()));
  } catch {
    return json(
      res,
      502,
      {
        error: {
          code: "WBRAIN-UPSTREAM-001",
          message: "inference backend unavailable",
          request_id: id,
        },
      },
      id,
    );
  }
}
