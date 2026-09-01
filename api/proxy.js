export const config = { api: { bodyParser: false } };

export default async function handler(req, res) {
  const backend = process.env.WBRAIN_BACKEND_URL;
  if (!backend) {
    return res.status(503).json({
      error: {
        code: "WBRAIN-DEPLOY-001",
        message: "inference backend is not configured",
      },
    });
  }

  const query = { ...(req.query || {}) };
  const path = query.path || new URL(req.url, "http://vercel.local").pathname;
  delete query.path;
  const queryString = new URLSearchParams(query).toString();
  const target = `${backend.replace(/\/$/, "")}${path}${queryString ? `?${queryString}` : ""}`;
  const headers = { ...req.headers, host: new URL(backend).host };
  delete headers.connection;
  delete headers["content-length"];
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const response = await fetch(target, {
    method: req.method,
    headers,
    body: ["GET", "HEAD"].includes(req.method)
      ? undefined
      : Buffer.concat(chunks),
  });
  res.status(response.status);
  response.headers.forEach((value, name) => {
    if (!["transfer-encoding", "connection"].includes(name.toLowerCase()))
      res.setHeader(name, value);
  });
  return res.send(Buffer.from(await response.arrayBuffer()));
}
