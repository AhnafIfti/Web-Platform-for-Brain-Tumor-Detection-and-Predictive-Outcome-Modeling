$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$logDirectory = Join-Path $projectRoot 'tmp\launcher'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Virtual environment is missing. Follow README installation instructions.' }
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

# Serialize repeated double-clicks; leave unrelated applications untouched.
$launchMutex = New-Object System.Threading.Mutex($false, 'Local\NeuroVisionLauncher9130')
if (-not $launchMutex.WaitOne(0)) { Write-Host 'NeuroVision is already starting.'; exit 0 }
try {
    $processes = @(Get-CimInstance Win32_Process)
    function Start-NeuroService($name, $arguments, $signature, $port) {
        $matching = @($processes | Where-Object {
            $_.Name -eq 'python.exe' -and
            $_.CommandLine -match ('^"?' + [regex]::Escape($pythonExe) + '"?\s') -and
            $_.CommandLine -like "*$signature*"
        })
        $listener = @()
        if ($port) {
            $listener = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
            if ($listener.Count -gt 0) {
                $owned = @($listener | Where-Object { $_.OwningProcess -in $matching.ProcessId })
                if ($owned.Count -ne $listener.Count) { throw "Port $port is occupied by another application. Nothing was stopped." }
                Write-Host "$name is already running."
                return
            }
        }
        if ($matching.Count -gt 0) { Write-Host "$name is already starting or running."; return }
        $child = Start-Process -FilePath $pythonExe -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory "$name.log") -RedirectStandardError (Join-Path $logDirectory "$name-error.log")
        if ($port) {
            $ready = $false
            for ($attempt = 0; $attempt -lt 45; $attempt++) {
                Start-Sleep -Seconds 1
                if ($child.HasExited) { throw "$name exited. See $logDirectory\$name-error.log" }
                if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { $ready = $true; break }
            }
            if (-not $ready) { throw "$name did not become ready. See logs in $logDirectory" }
        }
        Write-Host "$name started."
    }
    Start-NeuroService 'backend' '-u manage.py runserver 127.0.0.1:9131 --noreload' 'manage.py runserver 127.0.0.1:9131 --noreload' 9131
    Start-NeuroService 'frontend' '-u tools/frontend_server.py --port 9130 --backend-port 9131' 'tools/frontend_server.py --port 9130 --backend-port 9131' 9130
    Start-NeuroService 'worker' '-u manage.py run_analysis_worker' 'manage.py run_analysis_worker' 0
    Start-Process 'http://127.0.0.1:9130/'
    Write-Host 'NeuroVision is ready. Background services stay running after this window closes.'
} finally {
    $launchMutex.ReleaseMutex()
    $launchMutex.Dispose()
}
