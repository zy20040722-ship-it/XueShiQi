<#
把 字体\ 目录下的两款字体装进"当前用户的字体目录"并注册到 HKCU。
不需要管理员权限, 卸载时删掉 %LOCALAPPDATA%\Microsoft\Windows\Fonts 下对应文件 +
注册表 HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts 下对应项即可。
#>
$ErrorActionPreference = "Stop"

$ws  = "D:\Users\15241\Desktop\薛世奇视频剪辑流水线"
$src = Join-Path $ws "方法论文档\字体源文件"
$dst = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
$key = "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

$map = [ordered]@{
    "FZJinLS-B-GB.ttf"     = "方正粗金陵简体"       # SOP 里的「金陵体」
    "DFPLiJinHeiW8-GB.TTF" = "华康俪金黑W8(P)"       # SOP 里的「丽金黑」
}

New-Item -ItemType Directory -Force -Path $dst | Out-Null
if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }

foreach ($f in $map.Keys) {
    $p = Join-Path $src $f
    if (-not (Test-Path -LiteralPath $p)) { Write-Warning "找不到 $p"; continue }
    $dest = Join-Path $dst $f
    Copy-Item -LiteralPath $p -Destination $dest -Force
    # 用户字体（放在 %LOCALAPPDATA%\Microsoft\Windows\Fonts）注册时值必须是「完整路径」，
    # 只写文件名的话 Windows 找不到文件，字体不会出现在任何软件的字体列表里。
    New-ItemProperty -Path $key -Name "$($map[$f]) (TrueType)" -Value $dest `
        -PropertyType String -Force | Out-Null
    Write-Host "已装入用户字体库: $($map[$f])   <- $f"
}

Write-Host ""
Write-Host "校验：Windows 字体列表现在能不能看到这两款"
Add-Type -AssemblyName System.Drawing
$installed = (New-Object System.Drawing.Text.InstalledFontCollection).Families | ForEach-Object { $_.Name }
foreach ($name in $map.Values) {
    if ($installed -contains $name) { Write-Host "  OK   $name" } else { Write-Warning "  未生效 $name（可能需要注销/重启后生效）" }
}

Write-Host ""
Write-Host "注册表里的相关项:"
Get-ItemProperty -Path $key | Select-Object -Property * |
    ForEach-Object { $_.PSObject.Properties } |
    Where-Object { $_.Name -match "金陵|俪金" } |
    ForEach-Object { Write-Host ("  {0} = {1}" -f $_.Name, $_.Value) }
