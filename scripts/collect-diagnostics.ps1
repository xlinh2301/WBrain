param(
  [string]$OutputDir = "diagnostics"
)
$ErrorActionPreference = "SilentlyContinue"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$bundle = Join-Path $OutputDir "wbrain-diagnostics-$stamp"
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
@{ generated_at = $stamp } | ConvertTo-Json | Set-Content (Join-Path $bundle "metadata.json")
docker compose ps *> (Join-Path $bundle "compose-status.txt")
$logs = docker compose logs --no-color --tail=500 wbrain 2>$null
$logs -replace '(?i)(fernet|license|token|secret|password|api[_-]?key|authorization)[\s:=]+[^,\s;]+', '$1=***REDACTED***' |
  Set-Content (Join-Path $bundle "recent-logs.txt")
docker compose exec -T wbrain python -c "import json,urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health'))))" *> (Join-Path $bundle "health.json")
$archive = Join-Path $OutputDir "wbrain-diagnostics-$stamp.zip"
Compress-Archive -Path $bundle -DestinationPath $archive -Force
Remove-Item -Recurse -Force $bundle
Write-Output $archive
