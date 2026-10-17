param([switch]$Setup, [string]$Python = 'python', [switch]$BackendOnly)
$ErrorActionPreference = 'Stop'
$backend = Join-Path $PSScriptRoot 'backend'
$frontend = Join-Path $PSScriptRoot 'frontend'
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'

function Check-Exit($Action) {
    if ($LASTEXITCODE -ne 0) { throw "$Action failed (exit $LASTEXITCODE)." }
}

if ($Setup) {
    & $Python --version
    Check-Exit 'Python check'
    if (!(Test-Path $venvPython)) {
        & $Python -m venv (Join-Path $backend '.venv')
        Check-Exit 'Virtual environment creation'
    }
    & $venvPython -m pip install -r (Join-Path $backend 'requirements.txt')
    Check-Exit 'Backend dependency installation'
    Push-Location $frontend
    try {
        & npm.cmd ci
        Check-Exit 'Frontend dependency installation'
    } finally { Pop-Location }
}
if (!(Test-Path $venvPython)) { throw 'Run .\Start-TaxPrep.ps1 -Setup first. Requires Python 3.12 and Node.js 20 or newer with npm.' }

# Generate once and reuse: changing DATA_KEY makes saved identifiers unreadable.
$secretFile = Join-Path $backend '.local-secrets.json'
if (!(Test-Path $secretFile)) {
    $secretJson = & $venvPython -c 'import json,secrets; from cryptography.fernet import Fernet; print(json.dumps(dict(DATA_KEY=Fernet.generate_key().decode(),JWT_SECRET=secrets.token_urlsafe(48))))'
    Check-Exit 'Local secret generation'
    [System.IO.File]::WriteAllText($secretFile, ($secretJson -join "`n"))
}
$localSecrets = Get-Content -Raw $secretFile | ConvertFrom-Json
$env:DATA_KEY = $localSecrets.DATA_KEY
$env:JWT_SECRET = $localSecrets.JWT_SECRET
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $backend 'taxprep.db').Replace('\','/')
$env:CORS_ORIGINS = 'http://localhost:3000'
$env:NEXT_PUBLIC_API_URL = 'http://localhost:8000'

if ($BackendOnly) {
    Push-Location $backend
    try { & $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000 }
    finally { Pop-Location }
    exit
}
if (!(Test-Path (Join-Path $frontend 'node_modules'))) { throw 'Frontend dependencies missing. Run with -Setup.' }
$shellPath = (Get-Process -Id $PID).Path
$scriptPath = $PSCommandPath.Replace("'", "''")
$apiProcess = Start-Process -FilePath $shellPath -WindowStyle Hidden -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', "& '$scriptPath' -BackendOnly"
) -PassThru
Write-Host 'Open http://localhost:3000 once Next.js says Ready. Press Ctrl+C to stop.'
Push-Location $frontend
try { & npm.cmd run dev }
finally {
    Pop-Location
    # Stop only the backend process tree started by this launcher.
    & taskkill.exe /PID $apiProcess.Id /T /F 2>$null
}
