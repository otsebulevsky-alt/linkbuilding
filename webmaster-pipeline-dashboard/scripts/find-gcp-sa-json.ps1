# Find JSON files that look like GCP service account keys (path only, no secrets).
$ErrorActionPreference = 'SilentlyContinue'
$dirs = @(
    [Environment]::GetFolderPath('UserProfile') + '\Downloads',
    [Environment]::GetFolderPath('MyDocuments'),
    [Environment]::GetFolderPath('Desktop'),
    [Environment]::GetFolderPath('UserProfile') + '\.cursor',
    'c:\project\start'
)
$found = New-Object System.Collections.Generic.List[string]
foreach ($d in $dirs) {
    if (-not (Test-Path -LiteralPath $d)) { continue }
    Get-ChildItem -LiteralPath $d -Filter '*.json' -File -Recurse -Depth 8 | ForEach-Object {
        try {
            if ($_.Length -gt 120000) { return }
            $c = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop
            if ($c -match '"type"\s*:\s*"service_account"' -and $c -match 'private_key') {
                $found.Add($_.FullName) | Out-Null
            }
        } catch {}
    }
}
$found | Sort-Object -Unique | ForEach-Object { Write-Output $_ }
if ($found.Count -eq 0) {
    Write-Output 'NO_MATCH'
}
