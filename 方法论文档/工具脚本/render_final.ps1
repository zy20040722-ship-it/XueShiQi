<#
重烧成片: 底片 + 字幕 + 两张图示, 字体用 SOP 指定的金陵体 / 丽金黑。

  底片   分析\IMG_3922\粗剪_v2.mp4
  字幕   精剪\成片字幕.ass        (正文=方正粗金陵简体, 花字=华康俪金黑W8)
  覆层   精剪\图示\*.png          落点 x=90 y=250 (从上一版成片实测得到)
  时段   斜面 87.0-90.7s, 船球 94.9-98.2s
  音频   与底片完全一致(不额外增益)

为避免中文路径在 ffmpeg 滤镜里被转义搞坏, 需要的文件先拷进 ASCII 目录 _render_tmp\。

用法: powershell -ExecutionPolicy Bypass -File tools\render_final.ps1 [-Out <输出文件>]
#>
param(
    [string]$Out = ""
)
$ErrorActionPreference = "Stop"

$ws  = "D:\Users\15241\Desktop\薛世奇视频剪辑流水线"
$ff  = "D:\Software\ffmpeg\bin\ffmpeg.exe"
$src = Join-Path $ws "分析\IMG_3922\粗剪_v2.mp4"
if (-not $Out) { $Out = Join-Path $ws "精剪\成片_薛世奇说物理_字体版.mp4" }

$tmp = Join-Path $ws "_render_tmp"
New-Item -ItemType Directory -Force -Path (Join-Path $tmp "fonts") | Out-Null
Copy-Item -LiteralPath (Join-Path $ws "精剪\成片字幕.ass") -Destination (Join-Path $tmp "sub.ass") -Force
Copy-Item -LiteralPath (Join-Path $ws "精剪\图示\斜面受力分析.png") -Destination (Join-Path $tmp "d1.png") -Force
Copy-Item -LiteralPath (Join-Path $ws "精剪\图示\船球模型.png") -Destination (Join-Path $tmp "d2.png") -Force
Copy-Item -LiteralPath (Join-Path $ws "精剪\图示\传送带受力分析.png") -Destination (Join-Path $tmp "d3.png") -Force
Copy-Item -LiteralPath (Join-Path $ws "精剪\图示\传动模型.png") -Destination (Join-Path $tmp "d4.png") -Force
Copy-Item -Path (Join-Path $ws "方法论文档\字体源文件\*.ttf") -Destination (Join-Path $tmp "fonts") -Force
Copy-Item -Path (Join-Path $ws "方法论文档\字体源文件\*.TTF") -Destination (Join-Path $tmp "fonts") -Force

# 顺序: 先叠两张图示, 最后烧字幕 —— 这样顶部主标题和字幕永远压在图示上面,
# 图示那 6 秒里标题也不会被盖掉(主标题要求全程可见)。
# 图示落点从 y=250 下移到 y=440: 给顶部两行主标题让位, 又刚好压在头顶上方。
# 四张图示按薛老师点名的顺序连着出现: 斜面 -> 传送带 -> 传动模型 -> 船球
# 音频: SOP 要求原素材 +6.8dB。底片峰值已经到 -0.7dBFS, 直接加会削顶,
#       所以加完过一道限幅器(limit=0.97, 只压爆点, 不做响度归一)。
# 输入顺序: 0=底片, 1=斜面, 2=船球, 3=传送带, 4=传动模型
$filter = @(
    "[0:v][1:v]overlay=90:440:enable='between(t,87.0,89.5)'[v1]"
    "[v1][3:v]overlay=90:440:enable='between(t,89.6,92.0)'[v2]"
    "[v2][4:v]overlay=90:440:enable='between(t,92.1,94.8)'[v3]"
    "[v3][2:v]overlay=90:440:enable='between(t,94.9,98.2)'[v4]"
    "[v4]subtitles=sub.ass:fontsdir=fonts[vout]"
    "[0:a]volume=6.8dB,alimiter=limit=0.97:attack=5:release=50:level=disabled[aout]"
) -join ";`n"
Set-Content -LiteralPath (Join-Path $tmp "filter.txt") -Value $filter -Encoding ascii

Write-Host "底片: $src"
Write-Host "输出: $Out"
Push-Location $tmp
try {
    $t0 = Get-Date
    & $ff -hide_banner -y `
        -i $src -i d1.png -i d2.png -i d3.png -i d4.png `
        -filter_complex_script filter.txt `
        -map "[vout]" -map "[aout]" `
        -c:v h264_nvenc -preset p5 -rc vbr -cq 21 -b:v 0 -maxrate 20M -bufsize 30M `
        -profile:v high -pix_fmt yuv420p -r 60 `
        -c:a aac -b:a 192k -ar 48000 -ac 2 `
        -movflags +faststart `
        $Out
    if ($LASTEXITCODE -ne 0) { throw "ffmpeg 退出码 $LASTEXITCODE" }
    Write-Host ("渲染完成, 用时 {0} 秒" -f [math]::Round(((Get-Date) - $t0).TotalSeconds, 1))
} finally {
    Pop-Location
}
