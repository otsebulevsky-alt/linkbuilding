$ErrorActionPreference = 'SilentlyContinue'
$candidates = New-Object System.Collections.Generic.List[string]
$roots = @(
    (Join-Path $env:USERPROFILE 'Downloads'),
    (Join-Path $env:USERPROFILE 'Desktop'),
    (Join-Path $env:USERPROFILE 'Documents'),
    (Join-Path $env:USERPROFILE 'OneDrive'),
    (Join-Path $env:USERPROFILE 'OneDrive - Personal'),
    (Join-Path $env:USERPROFILE '.cursor'),
    (Join-Path $env:USERPROFILE 'source'),
    (Join-Path $env:USERPROFILE 'Source'),
    'c:\project'
)
foreach ($root in $roots) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    Get-ChildItem -LiteralPath $root -Filter '*.json' -File -Recurse -Depth 10 | ForEach-Object {
        try {
            if ($_.Length -gt 200000) { return }
            $c = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop
            if ($c -match '"type"\s*:\s*"service_account"' -and $c -match 'private_key') {
                $candidates.Add($_.FullName) | Out-Null
            }
        } catch {}
    }
}
$candidates | Sort-Object -Unique | ForEach-Object { Write-Output $_ }
if ($candidates.Count -eq 0) { Write-Output 'NO_MATCH' }
