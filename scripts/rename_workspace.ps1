# Rename the checkout after editors and other directory holders have closed.
# SPDX-License-Identifier: GPL-3.0-or-later
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$taskSource = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$taskParent = Split-Path -Parent $taskSource
$taskDestination = [System.IO.Path]::GetFullPath((Join-Path $taskParent 'stavellum'))
if ($taskSource -eq $taskDestination) {
    Write-Output "工程目录已是 $taskDestination"
    return
}
if (-not (Test-Path -LiteralPath (Join-Path $taskSource 'src/stavellum/__init__.py'))) {
    throw '未找到 Stavellum 源码，无法确认待移动目录。'
}
if ((Split-Path -Parent $taskDestination) -ne $taskParent) {
    throw '目标目录必须与原工程位于同一父目录。'
}
if (Test-Path -LiteralPath $taskDestination) {
    throw "目标已存在，不会覆盖：$taskDestination"
}
Get-Command uv -ErrorAction Stop | Out-Null
Set-Location -LiteralPath $taskParent
try {
    Move-Item -LiteralPath $taskSource -Destination $taskDestination -ErrorAction Stop
} catch {
    throw "Windows 阻止目录更名。请关闭使用该目录的编辑器、终端和应用后重试。原目录：$taskSource。错误：$($_.Exception.Message)"
}
Set-Location -LiteralPath $taskDestination
# Console launchers and editable installs contain absolute paths; recreate them.
& uv sync --extra dev --locked --reinstall
if ($LASTEXITCODE -ne 0) {
    throw "目录已更名，但依赖重装失败。请在 $taskDestination 运行 uv sync --extra dev --locked --reinstall。"
}
& (Join-Path $taskDestination '.venv/Scripts/python.exe') scripts/build_rhi.py --install
if ($LASTEXITCODE -ne 0) {
    throw '目录已更名，但原生后端重建失败。请按照 README.md 的构建步骤重试。'
}
Write-Output "工程目录更名和运行环境更新完成：$taskDestination"
