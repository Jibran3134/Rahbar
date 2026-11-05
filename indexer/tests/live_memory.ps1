# Explicit Windows native full-indexer measurement; not a container/cgroup peak.
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:CORPUS_DIR = Join-Path $repoRoot 'corpus\raw'
$env:CHROMA_HOST = '127.0.0.1'
$env:CHROMA_PORT = '8001'
$env:CHROMA_COLLECTION = 'rahbar_memory_audit'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'
$env:TESSERACT_CMD = Join-Path $repoRoot '.venv\tesseract-5.5.3\tesseract.exe'
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$outPath = Join-Path $repoRoot 'docs\evidence\app\sprints\S19-memory-stdout.txt'
$errPath = Join-Path $repoRoot 'docs\evidence\app\sprints\S19-memory-stderr.txt'
$process = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'pipeline.run') -WorkingDirectory (Join-Path $repoRoot 'indexer') -WindowStyle Hidden -RedirectStandardOutput $outPath -RedirectStandardError $errPath -PassThru
$null = $process.Handle
$peakBytes = 0L
$launcherPeak = 0L
$startTime = Get-Date
while (-not $process.HasExited) {
    $process.Refresh()
    if ($process.PeakWorkingSet64 -gt $launcherPeak) { $launcherPeak = $process.PeakWorkingSet64 }
    # Windows venv python.exe is a launcher: measure its actual interpreter child.
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($process.Id)" | Where-Object { $_.Name -eq 'python.exe' }
    foreach ($child in $children) {
        $interpreter = Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
        if ($interpreter -and $interpreter.PeakWorkingSet64 -gt $peakBytes) { $peakBytes = $interpreter.PeakWorkingSet64 }
    }
    Start-Sleep -Milliseconds 500
}
$process.WaitForExit()
$code = $process.ExitCode
if ($null -eq $code) { throw 'Native exit code unavailable; memory gate not verified' }
$report = @{
    passed = ($code -eq 0 -and $peakBytes -gt 0)
    native_exit = $code
    python_peak_working_set_bytes = $peakBytes
    launcher_peak_bytes = $launcherPeak
    seconds = ((Get-Date) - $startTime).TotalSeconds
    scope = 'Windows actual interpreter child OS peak sampled every 500ms; venv launcher reported separately; OCR children excluded; not a pod/cgroup peak or limit margin'
    collection = 'rahbar_memory_audit'
}
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repoRoot 'docs\evidence\app\sprints\S19-memory.json') -Encoding utf8
$report | ConvertTo-Json
if ($code -ne 0) { throw "Native full indexer failed: $code" }
