param([string]$Project)
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    Write-Error '请先运行 uv sync --extra dev 或按 README.md 安装依赖。'
    exit 1
}
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($Project) { & $taskPython -m stavellum gui $Project }
    else { & $taskPython -m stavellum gui }
} finally { Pop-Location }
