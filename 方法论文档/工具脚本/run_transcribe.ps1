# 一键转写: 把视频或整个文件夹转成带时间戳的文字稿
# 用法:  powershell -ExecutionPolicy Bypass -File run_transcribe.ps1 "D:\路径\素材文件夹"

param(
    [Parameter(Mandatory = $true, Position = 0)][string]$SourcePath,
    [string]$Out = "",
    [switch]$Cpu
)

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:NO_PROXY  = '*'
$env:no_proxy  = '*'
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:HF_HOME   = 'D:\Software\asr-models\hf'

$vpy   = 'D:\Software\asr-env\Scripts\python.exe'
$tools = $PSScriptRoot
$model = 'D:\Software\asr-models\ct2\large-v3-turbo'
$docs  = Join-Path (Split-Path $tools -Parent) '流水线文档'
$hot   = Join-Path $docs '物理术语表.txt'
$corr  = Join-Path $docs '术语纠错表.txt'

if (-not (Test-Path $vpy))   { throw "找不到语音识别环境: $vpy" }
if (-not (Test-Path $model)) { throw "找不到模型: $model" }

$cliArgs = @(
    (Join-Path $tools 'transcribe.py'),
    $SourcePath,
    '--model', $model,
    '--device', $(if ($Cpu) { 'cpu' } else { 'cuda' })
)
if ($Out) { $cliArgs += @('--out', $Out) }
if (Test-Path $hot) { $cliArgs += @('--hotwords', $hot) }
if (Test-Path $corr) { $cliArgs += @('--corrections', $corr) }

Write-Host "开始转写: $SourcePath"
& $vpy @cliArgs
