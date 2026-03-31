# Run Streamlit from this folder (fixes "File does not exist: app.py" when cwd is repo root).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host "cwd: $(Get-Location)"
py -m streamlit run app.py
