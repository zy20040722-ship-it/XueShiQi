# 语音识别环境安装脚本
# 目标: D:\Software\asr-env  (虚拟环境)
#       D:\Software\asr-models (模型缓存)
# 组合: faster-whisper (large-v3-turbo) + FunASR (Paraformer)

$ErrorActionPreference = 'Continue'
$env:PYTHONIOENCODING = 'utf-8'
$env:HF_ENDPOINT     = 'https://hf-mirror.com'
$env:HF_HOME         = 'D:\Software\asr-models\hf'
$env:MODELSCOPE_CACHE = 'D:\Software\asr-models\modelscope'
$env:TORCH_HOME      = 'D:\Software\asr-models\torch'

# 关键: 系统里配了 127.0.0.1:7890 的代理, 但代理没开时 pip 会卡死。
# 全部走直连, 国内镜像本身就够快。
$env:NO_PROXY   = '*'
$env:no_proxy   = '*'
$env:HTTP_PROXY = ''
$env:HTTPS_PROXY = ''
$env:http_proxy = ''
$env:https_proxy = ''

$py      = 'C:\Users\15241\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$envDir  = 'D:\Software\asr-env'
$vpy     = "$envDir\Scripts\python.exe"
$Tsinghua = 'https://pypi.tuna.tsinghua.edu.cn/simple'

function Step($n, $msg) { Write-Host "`n[$n] $msg" }

Step '1/5' '创建虚拟环境...'
if (-not (Test-Path $vpy)) {
    & $py -m venv $envDir
    if (-not (Test-Path $vpy)) { Write-Host 'FATAL: venv 创建失败'; exit 1 }
}
Write-Host "venv ok: $vpy"

Step '2/5' '升级 pip / setuptools / wheel...'
& $vpy -m pip install -U pip setuptools wheel -i $Tsinghua --quiet 2>&1 | Select-Object -Last 3

Step '3/5' '安装 faster-whisper (GPU 推理, 不依赖 PyTorch)...'
& $vpy -m pip install "numpy<2" soundfile faster-whisper -i $Tsinghua 2>&1 | Select-Object -Last 5
Write-Host '  补齐 CTranslate2 在 Windows 上需要的 CUDA 运行库...'
& $vpy -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 -i $Tsinghua 2>&1 | Select-Object -Last 3

Step '4/5' '安装 FunASR (PyTorch CPU 版, 体积极小)...'
& $vpy -m pip install torch torchaudio -i $Tsinghua 2>&1 | Select-Object -Last 4
& $vpy -m pip install funasr modelscope -i $Tsinghua 2>&1 | Select-Object -Last 8

Step '5/5' '自检...'
& $vpy -c @"
import torch, sys
print('python', sys.version.split()[0])
print('torch', torch.__version__)
print('cuda_available', torch.cuda.is_available())
if torch.cuda.is_available():
    print('gpu', torch.cuda.get_device_name(0))
try:
    import faster_whisper
    print('faster_whisper', faster_whisper.__version__)
except Exception as e:
    print('faster_whisper FAIL', e)
try:
    import funasr
    print('funasr', getattr(funasr, '__version__', 'ok'))
except Exception as e:
    print('funasr FAIL', e)
"@

Write-Host "`nALL_DONE"
