# -*- coding: utf-8 -*-
"""语音识别环境自检"""
import sys

print("python", sys.version.split()[0])

MODS = ["numpy", "torch", "torchaudio", "ctranslate2", "faster_whisper",
        "funasr", "modelscope", "soundfile", "librosa"]
for m in MODS:
    try:
        mod = __import__(m)
        ver = getattr(mod, "__version__", "")
        print(f"  OK   {m:16} {ver}")
    except Exception as e:
        print(f"  FAIL {m:16} {type(e).__name__}: {str(e)[:100]}")

try:
    import torch
    print("torch CUDA 可用:", torch.cuda.is_available())
except Exception as e:
    print("torch 检查失败:", e)

try:
    import ctranslate2
    print("CTranslate2 CUDA 设备数:", ctranslate2.get_cuda_device_count())
    try:
        print("CTranslate2 CUDA 精度支持:", ctranslate2.get_supported_compute_types("cuda"))
    except Exception as e:
        print("CUDA 精度查询失败:", str(e)[:100])
    print("CTranslate2 CPU 精度支持:", ctranslate2.get_supported_compute_types("cpu"))
except Exception as e:
    print("CTranslate2 检查失败:", e)

# 本地模型是否可用
from pathlib import Path
mdl = Path(r"D:\Software\asr-models\ct2\large-v3-turbo")
need = ["model.bin", "config.json", "tokenizer.json", "vocabulary.json", "preprocessor_config.json"]
missing = [f for f in need if not (mdl / f).exists() or (mdl / f).stat().st_size < 100]
if missing:
    print("本地模型缺失:", missing)
else:
    size = sum((mdl / f).stat().st_size for f in need) / 1024 / 1024
    print(f"本地模型就绪: {mdl}  ({size:.0f} MB)")
