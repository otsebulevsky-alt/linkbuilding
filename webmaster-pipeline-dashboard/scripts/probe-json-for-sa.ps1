param([Parameter(Mandatory = $true)][string]$Path)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Path)) { Write-Output 'MISSING'; exit 1 }
$bytes = [System.IO.File]::ReadAllBytes($Path)
if ($bytes.Length -gt 200000) { Write-Output 'TOO_LARGE'; exit 0 }
$text = [System.Text.Encoding]::UTF8.GetString($bytes)
if ($text -match 'service_account' -and $text -match 'private_key') { Write-Output 'LOOKS_LIKE_SA' } else { Write-Output 'NOT_SA' }
