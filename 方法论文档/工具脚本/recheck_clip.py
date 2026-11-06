# -*- coding: utf-8 -*-
"""把一小段音频单独拎出来重新识别, 用不同参数交叉验证
用法: python recheck_clip.py <源视频> <起> <止> [提示词]
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import importlib.util

spec = importlib.util.spec_from_file_location("tr", Path(__file__).parent / "transcribe.py")
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)

FFMPEG = r"D:\Software\ffmpeg\bin\ffmpeg.exe"
MODEL = r"D:\Software\asr-models\ct2\large-v3-turbo"

src, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
prompt = sys.argv[4] if len(sys.argv) > 4 else None

print("CUDA DLL 目录:", tr.CUDA_DLL_DIRS)
with tempfile.TemporaryDirectory() as td:
    wav = Path(td) / "c.wav"
    tr.extract_audio_range(FFMPEG, src, wav, a, b) if hasattr(tr, "extract_audio_range") else subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(a), "-t", str(b - a),
         "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)],
        check=True,
    )
    from faster_whisper import WhisperModel

    model = WhisperModel(MODEL, device="cuda", compute_type="float16")
    variants = [
        {"name": "标准", "kw": {}},
        {"name": "无VAD+不定上下文", "kw": {"vad_filter": False, "condition_on_previous_text": False}},
        {"name": "贪心解码", "kw": {"beam_size": 1, "temperature": 0.0, "vad_filter": False}},
    ]
    for v in variants:
        segs, info = model.transcribe(
            str(wav),
            language="zh",
            word_timestamps=True,
            beam_size=5,
            condition_on_previous_text=False,
            repetition_penalty=1.08,
            no_repeat_ngram_size=3,
            initial_prompt=prompt,
            **v["kw"],
        )
        print(f"\n=== 变体: {v['name']} ===")
        for s in segs:
            print(f"  {s.start:6.2f}-{s.end:6.2f}  {s.text.strip()}")
            words = " ".join(f"{w.word}[{w.start:.2f}]" for w in (s.words or []))
            print(f"      {words}")
