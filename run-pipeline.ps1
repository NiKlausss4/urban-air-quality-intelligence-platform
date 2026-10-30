$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$envFile = Join-Path $projectRoot '.env'
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $envFile)) { throw 'Missing .env. Copy .env.example to .env and set XKDR_API_KEY.' }
foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $name = $Matches[1]
        $value = $Matches[2].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) { $value = $value.Substring(1, $value.Length - 2) }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}
if (-not $env:XKDR_API_KEY) { throw 'XKDR_API_KEY is empty in .env.' }
if (-not (Test-Path -LiteralPath $python)) { throw 'Python environment missing. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-windows.txt' }

# The Compose hostname only resolves inside its network. Use local PostgreSQL here.
$env:DATABASE_URL = $env:DATABASE_URL -replace '@postgres:', '@localhost:'
$env:PGHOST = 'localhost'
$env:PGUSER = 'airquality'
$env:PGPORT = '5432'
$env:PGDATABASE = 'airquality'
$env:PYTHONPATH = $projectRoot
Push-Location $projectRoot
try {
    & $python -m src.pipeline
    if ($LASTEXITCODE -ne 0) { throw "ETL failed with exit code $LASTEXITCODE" }
    & (Join-Path $projectRoot '.venv\Scripts\dbt.exe') build --project-dir (Join-Path $projectRoot 'dbt') --profiles-dir (Join-Path $projectRoot 'dbt')
    if ($LASTEXITCODE -ne 0) { throw "dbt build failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}
