param(
    [string[]]$Models = @("gpt-5.1-codex-mini", "gpt-5.1-codex-max"),
    [int]$TimeoutSec = 45,
    [switch]$IncludeClaudeMd,
    [string]$SystemPromptFile,
    [string]$CodexHome
)

$ErrorActionPreference = "Stop"

if ($Models.Count -eq 1 -and $Models[0].Contains(",")) {
    $Models = $Models[0].Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$starlettePath = Join-Path $projectRoot "research\\real_code_starlette.py"
$claudePath = Join-Path $projectRoot "CLAUDE.md"
$outDir = Join-Path $projectRoot "output\\codex_starlette"
$codexCmd = Join-Path $env:APPDATA "npm\\codex.cmd"

if (-not (Test-Path $starlettePath)) {
    throw "Missing target file: $starlettePath"
}
if (-not (Test-Path $codexCmd)) {
    throw "Missing codex command: $codexCmd"
}
if ($SystemPromptFile) {
    if (-not (Test-Path $SystemPromptFile)) {
        throw "System prompt file not found: $SystemPromptFile"
    }
    $SystemPromptFile = (Resolve-Path $SystemPromptFile).Path
}

if (-not $CodexHome) {
    $CodexHome = Join-Path $projectRoot ".tmp_codex_home"
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null

$authSrc = Join-Path $HOME ".codex\\auth.json"
$cfgSrc = Join-Path $HOME ".codex\\config.toml"
$authDst = Join-Path $CodexHome "auth.json"
$cfgDst = Join-Path $CodexHome "config.toml"

if ((Test-Path $authSrc) -and -not (Test-Path $authDst)) {
    Copy-Item $authSrc $authDst -Force
}
if ((Test-Path $cfgSrc) -and -not (Test-Path $cfgDst)) {
    Copy-Item $cfgSrc $cfgDst -Force
}

$starletteCode = Get-Content -Raw -Path $starlettePath
$promptParts = @()

if ($IncludeClaudeMd -and (Test-Path $claudePath)) {
    $claudeText = Get-Content -Raw -Path $claudePath
    $promptParts += "Project guidance (CLAUDE.md):"
    $promptParts += $claudeText
}

$promptParts += (
    @(
        "Task:"
        "Analyze the Starlette routing code below using the same analysis style and core concepts you would apply from CLAUDE.md."
        "Return:"
        "1) A short verdict on whether the concepts transfer well."
        "2) Top 5 concrete issues (or fewer if none), each with severity and exact code location."
        "3) One suggested next experiment to compare model behavior."
        ""
        "Code:"
        '```python'
        $starletteCode
        '```'
    ) -join "`n"
)

$prompt = ($promptParts -join "`n`n")
$promptPath = Join-Path $outDir "prompt_used.md"
Set-Content -Path $promptPath -Value $prompt -Encoding utf8

$env:CODEX_HOME = $CodexHome
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$results = @()

foreach ($model in $Models) {
    $safe = ($model -replace "[^a-zA-Z0-9._-]", "_")
    $stdoutPath = Join-Path $outDir ("{0}_{1}_stdout.jsonl" -f $timestamp, $safe)
    $stderrPath = Join-Path $outDir ("{0}_{1}_stderr.txt" -f $timestamp, $safe)

    Remove-Item $stdoutPath, $stderrPath -ErrorAction SilentlyContinue

    $args = @("exec", "--json", "--ephemeral", "--skip-git-repo-check")
    if ($SystemPromptFile) {
        $args += @("-c", "model_instructions_file=""$SystemPromptFile""")
    }
    $args += @("-m", $model, "-")
    $start = Get-Date
    $proc = Start-Process -FilePath $codexCmd `
        -ArgumentList $args `
        -NoNewWindow `
        -PassThru `
        -RedirectStandardInput $promptPath `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath

    $finished = $proc.WaitForExit($TimeoutSec * 1000)
    if (-not $finished) {
        try {
            $proc.Kill()
        } catch {
            # Ignore race where process exits between WaitForExit and Kill.
        }
    }

    $duration = [math]::Round(((Get-Date) - $start).TotalSeconds, 2)
    $stdoutLines = @()
    $stderrLines = @()
    if (Test-Path $stdoutPath) { $stdoutLines = Get-Content $stdoutPath }
    if (Test-Path $stderrPath) { $stderrLines = Get-Content $stderrPath }

    $results += [pscustomobject]@{
        model = $model
        status = if ($finished) { "EXIT_$($proc.ExitCode)" } else { "TIMEOUT_${TimeoutSec}s" }
        duration_sec = $duration
        system_prompt_file = if ($SystemPromptFile) { $SystemPromptFile } else { "" }
        stdout_path = $stdoutPath
        stderr_path = $stderrPath
        stdout_preview = ($stdoutLines | Select-Object -First 6) -join "`n"
        stderr_preview = ($stderrLines | Select-Object -First 6) -join "`n"
    }
}

$summaryPath = Join-Path $outDir ("{0}_summary.json" -f $timestamp)
$results | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding utf8

$results | Format-Table model, status, duration_sec -AutoSize
Write-Host ""
Write-Host "Prompt:  $promptPath"
Write-Host "Summary: $summaryPath"
