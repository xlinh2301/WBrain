#!/usr/bin/env sh
set -eu

OUTPUT_DIR="${1:-diagnostics}"
mkdir -p "$OUTPUT_DIR"
DATE="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE="$OUTPUT_DIR/wbrain-diagnostics-$DATE"
mkdir -p "$BUNDLE"

printf '{"generated_at":"%s"}\n' "$DATE" > "$BUNDLE/metadata.json"
if command -v docker >/dev/null 2>&1; then
  docker compose ps > "$BUNDLE/compose-status.txt" 2>&1 || true
  docker compose logs --no-color --tail=500 wbrain 2>/dev/null \
    | sed -E 's/(fernet|license|token|secret|password|api[_-]?key|authorization)[[:space:]:=]+[^,[:space:];]+/\1=***REDACTED***/Ig' \
    > "$BUNDLE/recent-logs.txt" || true
  docker compose exec -T wbrain python -c \
    'import json,urllib.request; print(json.dumps(json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health"))))' \
    > "$BUNDLE/health.json" 2>/dev/null || true
fi

tar -czf "$OUTPUT_DIR/wbrain-diagnostics-$DATE.tar.gz" -C "$OUTPUT_DIR" "wbrain-diagnostics-$DATE"
rm -rf "$BUNDLE"
printf '%s\n' "$OUTPUT_DIR/wbrain-diagnostics-$DATE.tar.gz"
