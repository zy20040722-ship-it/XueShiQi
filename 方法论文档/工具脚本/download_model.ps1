# 从 ModelScope 下载 faster-whisper large-v3-turbo 模型 (CTranslate2 格式)
$ErrorActionPreference = 'Continue'
$repo = 'pengzhendong/faster-whisper-large-v3-turbo'
$base = "https://www.modelscope.cn/api/v1/models/$repo/repo?Revision=master&FilePath="
$dir  = 'D:\Software\asr-models\ct2\large-v3-turbo'
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$files = @('config.json', 'tokenizer.json', 'vocabulary.json', 'preprocessor_config.json', 'model.bin')
foreach ($f in $files) {
    $dst = Join-Path $dir $f
    $ok = $false
    for ($try = 1; $try -le 3 -and -not $ok; $try++) {
        Write-Host "下载 $f (第 $try 次) ..."
        & curl.exe -L --fail --retry 3 -C - --connect-timeout 20 -o $dst "$base$f" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $ok = $true }
    }
    if (Test-Path $dst) {
        Write-Host ("  {0} -> {1} MB" -f $f, [math]::Round((Get-Item $dst).Length / 1MB, 1))
    } else {
        Write-Host "  $f 下载失败"
    }
}
Write-Host 'MODEL_DOWNLOAD_DONE'
