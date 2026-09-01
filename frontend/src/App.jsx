import { useEffect, useMemo, useRef, useState } from "react";

const api = async (path, options = {}, apiKey = "") => {
  const headers = {
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
    ...(options.headers || {}),
  };
  if (options.body && typeof options.body === "string")
    headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      `${data?.error?.code || response.status} — ${data?.error?.message || "Request failed"}`,
    );
  return data;
};

function Json({ value }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
function Field({ label, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
    </label>
  );
}

export default function App() {
  const [key, setKey] = useState(localStorage.getItem("wbrain_api_key") || "");
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia("(max-width: 720px)").matches,
  );
  const [meters, setMeters] = useState([]);
  const [selectedMeter, setSelectedMeter] = useState("");
  const [serial, setSerial] = useState("");
  const [meterName, setMeterName] = useState("");
  const [address, setAddress] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState(null);
  const [readings, setReadings] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [models, setModels] = useState([]);
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("recognize");
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const canvasRef = useRef(null);

  const selected = useMemo(
    () => meters.find((meter) => meter.id === selectedMeter),
    [meters, selectedMeter],
  );
  const call = async (work) => {
    setBusy(true);
    setError("");
    try {
      return await work();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const notify = (text) => {
    setMessage(text);
    setTimeout(() => setMessage(""), 3000);
  };

  useEffect(() => {
    loadMeters();
  }, []);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 720px)");
    const update = () => setIsMobile(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      setCameraReady(false);
    },
    [],
  );
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function loadMeters() {
    const data = await api("/api/v1/meters", {}, key).catch(() => []);
    setMeters(Array.isArray(data) ? data : []);
  }
  function saveKey(value) {
    setKey(value);
    localStorage.setItem("wbrain_api_key", value);
  }
  async function health() {
    await call(async () => {
      const data = await api("/api/v1/health", {}, key);
      notify(`API OK · ${data.device} · persistence=${data.persistence}`);
    });
  }
  async function createMeter(event) {
    event.preventDefault();
    await call(async () => {
      const data = await api(
        "/api/v1/meters",
        {
          method: "POST",
          body: JSON.stringify({
            serial_number: serial,
            name: meterName || null,
            meter_type: "water",
            address: address || null,
          }),
        },
        key,
      );
      setSerial("");
      setMeterName("");
      setAddress("");
      await loadMeters();
      setSelectedMeter(data.id);
      notify(`Đã tạo ${data.serial_number}`);
    });
  }
  async function recognize(blob = file) {
    if (!blob) return setError("Hãy chọn ảnh trước");
    await call(async () => {
      const form = new FormData();
      form.append("file", blob, "meter.jpg");
      if (selectedMeter) form.append("meter_id", selectedMeter);
      const data = await api(
        "/api/v1/recognize",
        { method: "POST", body: form },
        key,
      );
      setResult(data);
      notify(`Recognition: ${data.reading_status || "stateless"}`);
      if (data.reading_id) {
        await loadReadings();
        await loadReviews();
      }
    });
  }
  async function startCamera() {
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.hidden = false;
      setCameraReady(true);
    } catch (e) {
      setError(`Không mở được camera: ${e.message}`);
    }
  }
  function snap() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        setFile(new File([blob], "camera.jpg", { type: "image/jpeg" }));
        recognize(blob);
      },
      "image/jpeg",
      0.9,
    );
  }
  async function loadReadings() {
    await call(async () => {
      const query = selectedMeter
        ? `?meter_id=${selectedMeter}&limit=100`
        : "?limit=100";
      setReadings(await api(`/api/v1/readings${query}`, {}, key));
    });
  }
  async function loadReviews() {
    await call(async () => {
      setReviews(
        await api("/api/v1/reviews?status=pending&limit=100", {}, key),
      );
    });
  }
  async function review(task) {
    const value = window.prompt(
      "Giá trị hiệu chỉnh (để trống nếu không sửa):",
      task.corrected_value ?? "",
    );
    const status = window.prompt(
      "Trạng thái: approved hoặc rejected",
      "approved",
    );
    if (!status) return;
    await call(async () => {
      await api(
        `/api/v1/reviews/${task.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            status,
            corrected_value: value ? Number(value) : null,
            reviewer: "web-demo",
            note: "Reviewed from Vite demo",
          }),
        },
        key,
      );
      await loadReviews();
      await loadReadings();
      notify("Đã cập nhật review");
    });
  }
  async function loadModels() {
    await call(async () => setModels(await api("/api/v1/models", {}, key)));
  }
  async function addModel(event) {
    event.preventDefault();
    const name = event.currentTarget.name.value;
    const version = event.currentTarget.version.value;
    await call(async () => {
      await api(
        `/api/v1/models?name=${encodeURIComponent(name)}&version=${encodeURIComponent(version)}`,
        { method: "POST" },
        key,
      );
      await loadModels();
      notify("Đã đăng ký model");
    });
  }
  async function loadAudit() {
    await call(async () =>
      setAudit(await api("/api/v1/audit?limit=100", {}, key)),
    );
  }

  const tabs = [
    ["recognize", "Recognition"],
    ["meters", "Meters"],
    ["readings", "Readings"],
    ["reviews", "Review queue"],
    ["admin", "Models & audit"],
  ];
  return (
    <>
      <header>
        <div>
          <div className="eyebrow">ON-PREMISE COMPUTER VISION</div>
          <h1>
            WBrain <span>API Demo</span>
          </h1>
          <p>Water-meter detection, OCR và quản lý reading</p>
        </div>
        <button onClick={health} disabled={busy}>
          Health check
        </button>
      </header>
      <main>
        <section className="connection">
          <Field
            label="X-API-Key (nếu server bật API_KEY)"
            type="password"
            value={key}
            onChange={(e) => saveKey(e.target.value)}
            placeholder="Không lưu key vào source"
          />
          <div className="connection-info">
            {selected ? (
              <>
                Meter đang chọn: <b>{selected.serial_number}</b>
              </>
            ) : (
              "Chưa chọn meter — recognition stateless"
            )}
          </div>
        </section>
        <nav>
          {tabs.map(([id, label]) => (
            <button
              key={id}
              className={tab === id ? "active" : "ghost"}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        {message && <div className="notice">{message}</div>}
        {error && <div className="error">{error}</div>}

        {tab === "recognize" && (
          <section>
            <div className="section-head">
              <div>
                <h2>{isMobile ? "Chụp ảnh meter" : "Upload image"}</h2>
                <p>
                  {isMobile
                    ? "Dùng camera sau để chụp mặt đồng hồ."
                    : "Phiên bản laptop chỉ nhận ảnh upload, không bật camera."}
                </p>
              </div>
              <select
                value={selectedMeter}
                onChange={(e) => setSelectedMeter(e.target.value)}
              >
                <option value="">Không gắn meter</option>
                {meters.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.serial_number} — {m.name || "No name"}
                  </option>
                ))}
              </select>
            </div>
            <div className="upload">
              {isMobile ? (
                <>
                  <button onClick={startCamera}>Mở camera sau</button>
                  <button onClick={snap} disabled={!cameraReady || busy}>
                    Chụp & OCR
                  </button>
                  <label className="drop">
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={(e) => {
                        setFile(e.target.files[0]);
                        recognize(e.target.files[0]);
                      }}
                    />
                    Chọn camera sau
                  </label>
                </>
              ) : (
                <>
                  <label className="drop">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setFile(e.target.files[0])}
                    />
                    {file ? file.name : "Chọn ảnh meter"}
                  </label>
                  <button onClick={() => recognize()} disabled={busy || !file}>
                    Run OCR
                  </button>
                </>
              )}
            </div>
            <video ref={videoRef} autoPlay playsInline hidden={!isMobile} />
            <canvas ref={canvasRef} hidden />
            {preview && (
              <img className="preview" src={preview} alt="Meter preview" />
            )}{" "}
            {result && (
              <div className="result-grid">
                <div>
                  <h3>Response</h3>
                  <Json value={result} />
                </div>
                <div>
                  <h3>Detections</h3>
                  {result.crops?.map((crop, index) => (
                    <article className="crop" key={index}>
                      <b>{crop.text || "—"}</b>
                      <span>box: [{crop.box.join(", ")}]</span>
                      <span>
                        det {(crop.confidence * 100).toFixed(1)}% · OCR{" "}
                        {(crop.text_confidence * 100).toFixed(1)}%
                      </span>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {tab === "meters" && (
          <div className="two-col">
            <section>
              <h2>Create meter</h2>
              <form onSubmit={createMeter}>
                <Field
                  label="Serial number *"
                  value={serial}
                  onChange={(e) => setSerial(e.target.value)}
                  required
                  placeholder="WM-001"
                />
                <Field
                  label="Name"
                  value={meterName}
                  onChange={(e) => setMeterName(e.target.value)}
                  placeholder="Main building"
                />
                <Field
                  label="Address"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
                <button disabled={busy}>Create</button>
              </form>
            </section>
            <section>
              <h2>Registered meters</h2>
              <button className="ghost" onClick={loadMeters}>
                Refresh
              </button>
              <Table
                rows={meters}
                columns={[
                  "serial_number",
                  "name",
                  "meter_type",
                  "address",
                  "id",
                ]}
              />
            </section>
          </div>
        )}
        {tab === "readings" && (
          <section>
            <div className="section-head">
              <h2>Reading history</h2>
              <button onClick={loadReadings}>Refresh</button>
            </div>
            <Table
              rows={readings}
              columns={[
                "created_at",
                "meter_id",
                "raw_text",
                "value",
                "confidence",
                "status",
                "model_version",
                "request_id",
              ]}
            />
          </section>
        )}
        {tab === "reviews" && (
          <section>
            <div className="section-head">
              <h2>Manual review queue</h2>
              <button onClick={loadReviews}>Refresh</button>
            </div>
            <Table
              rows={reviews}
              columns={[
                "id",
                "reading_id",
                "reason",
                "status",
                "corrected_value",
              ]}
              action={review}
            />
          </section>
        )}
        {tab === "admin" && (
          <div className="two-col">
            <section>
              <h2>Model versions</h2>
              <form onSubmit={addModel} className="inline-form">
                <input name="name" placeholder="name" defaultValue="wbrain" />
                <input name="version" placeholder="version" required />
                <button>Add</button>
              </form>
              <button className="ghost" onClick={loadModels}>
                Refresh
              </button>
              <Json value={models} />
            </section>
            <section>
              <h2>Audit events</h2>
              <button onClick={loadAudit}>Refresh</button>
              <Json value={audit} />
            </section>
          </div>
        )}
      </main>
      <footer>
        WBrain · API-first demo · <a href="/docs">OpenAPI docs</a>
      </footer>
    </>
  );
}

function Table({ rows, columns, action }) {
  if (!rows?.length) return <p className="muted">Chưa có dữ liệu.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
            {action && <th>action</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id || row.request_id}>
              {columns.map((c) => (
                <td key={c} className={c === "status" ? row[c] : ""}>
                  {typeof row[c] === "object"
                    ? JSON.stringify(row[c])
                    : (row[c] ?? "—")}
                </td>
              ))}
              {action && (
                <td>
                  <button onClick={() => action(row)}>Review</button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
