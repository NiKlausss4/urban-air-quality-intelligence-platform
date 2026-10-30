$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$envFile = Join-Path $projectRoot '.env'
$streamlit = Join-Path $projectRoot '.venv\Scripts\streamlit.exe'

if (-not (Test-Path -LiteralPath $envFile)) { throw 'Missing .env. Copy .env.example to .env and set XKDR_API_KEY.' }
foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $name = $Matches[1]
        $value = $Matches[2].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) { $value = $value.Substring(1, $value.Length - 2) }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}
$env:DATABASE_URL = $env:DATABASE_URL -replace '@postgres:', '@localhost:'
& $streamlit run (Join-Path $projectRoot 'dashboard\app.py')
