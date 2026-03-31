# Run Streamlit from this folder (fixes "File does not exist: app.py" when cwd is repo root).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host "cwd: $(Get-Location)"

$preferred = 8503
$port = $preferred
try {
    $inUse = Get-NetTCPConnection -LocalPort $preferred -State Listen -ErrorAction SilentlyContinue
} catch {
    $inUse = $null
}
if ($inUse) {
    Write-Host "Port $preferred is in use (often another Streamlit). Trying 8504..."
    $port = 8504
}

Write-Host "Streamlit URL: http://127.0.0.1:$port"
py -m streamlit run app.py --server.port $port --server.address 127.0.0.1
