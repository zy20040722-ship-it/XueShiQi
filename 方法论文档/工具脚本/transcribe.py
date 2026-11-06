#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
口播视频转写 + 停顿检测
输出: 每个视频一个文件夹, 内含
  transcript.json  逐句 + 逐词时间戳(做粗剪的关键)
  transcript.txt   纯文本
  transcript.srt   字幕
  silences.json    ffmpeg 检测到的停顿段(静音>0.35秒)
用法:
  python transcribe.py <文件或目录> [--out 输出目录] [--model large-v3-turbo]
                       [--device cuda] [--hotwords 热词文件] [--lang zh]
"""

import argparse
import json
import os
import re
import site
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows 控制台默认 GBK, 打印生僻字会直接崩掉整个流程
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def enable_cuda_dlls():
    """Windows 下 CTranslate2 需要 cublas/cudnn 的 DLL, pip 装在了 nvidia/*/bin, 手动加进搜索路径"""
    if os.name != "nt":
        return []
    added = []
    try:
        roots = list(site.getsitepackages())
    except Exception:
        roots = []
    for root in roots:
        nv = Path(root) / "nvidia"
        if not nv.is_dir():
            continue
        for sub in nv.iterdir():
            bindir = sub / "bin"
            if bindir.is_dir():
                os.add_dll_directory(str(bindir))
                os.environ["PATH"] = str(bindir) + os.pathsep + os.environ.get("PATH", "")
                added.append(str(bindir))
    return added


CUDA_DLL_DIRS = enable_cuda_dlls()

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".m4v", ".webm", ".ts", ".mpg", ".mpeg"}


def find_ffmpeg():
    for p in (
        r"D:\Software\ffmpeg\bin\ffmpeg.exe",
        "ffmpeg",
    ):
        try:
            subprocess.run([p, "-version"], capture_output=True, check=True)
            return p
        except Exception:
            continue
    raise RuntimeError("找不到 ffmpeg")


def extract_audio(ffmpeg, src: Path, dst: Path):
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dst),
    ]
    subprocess.run(cmd, check=True)


def detect_silence(ffmpeg, src: Path, noise_db="-32dB", min_dur=0.35):
    """返回 [(start, end, 时长)] 的停顿列表"""
    cmd = [
        ffmpeg, "-hide_banner", "-nostats",
        "-i", str(src),
        "-af", f"silencedetect=noise={noise_db}:d={min_dur}",
        "-f", "null", "-",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    text = (r.stderr or "") + (r.stdout or "")
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", text)]
    ends_raw = re.findall(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)", text)
    out = []
    for i, (e, d) in enumerate(ends_raw):
        s = starts[i] if i < len(starts) else float(e) - float(d)
        out.append({"start": round(s, 3), "end": round(float(e), 3), "dur": round(float(d), 3)})
    # 结尾没有 silence_end 的情况
    if len(starts) > len(ends_raw):
        out.append({"start": round(starts[-1], 3), "end": None, "dur": None})
    return out


def fmt_ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def load_corrections(path):
    """读取纠错表, 返回 [(是否正则, 匹配串, 替换串)]"""
    rules = []
    p = Path(path)
    if not p.exists():
        return rules
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=>" not in line:
            continue
        left, right = line.split("=>", 1)
        left, right = left.strip(), right.strip()
        if not left or not right or right == "?":
            continue
        if left.startswith("re:"):
            rules.append((True, left[3:].strip(), right))
        else:
            rules.append((False, left, right))
    return rules


def apply_corrections(text, rules):
    for is_re, pat, rep in rules:
        if is_re:
            text = re.sub(pat, rep, text)
        else:
            text = text.replace(pat, rep)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="视频文件或目录")
    ap.add_argument("--out", default=None, help="输出目录, 默认与输入同级的 转写 文件夹")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--compute-type", default=None)
    ap.add_argument("--hotwords", default=None, help="热词文件, 一行一个物理名词")
    ap.add_argument("--corrections", default=None, help="纠错表文件")
    ap.add_argument("--lang", default="zh")
    args = ap.parse_args()

    src = Path(args.input)
    files = (
        sorted([p for p in src.iterdir() if p.suffix.lower() in VIDEO_EXT])
        if src.is_dir()
        else [src]
    )
    if not files:
        print("没有找到视频文件")
        sys.exit(1)

    outroot = Path(args.out) if args.out else (src if src.is_dir() else src.parent) / "转写"
    outroot.mkdir(parents=True, exist_ok=True)

    hotwords = None
    if args.hotwords and Path(args.hotwords).exists():
        raw = [
            l.strip() for l in Path(args.hotwords).read_text(encoding="utf-8").splitlines() if l.strip()
            and not l.strip().startswith("#")
        ]
        # Whisper 的提示窗口只有 224 个 token, 热词塞太多会挤爆上下文导致解码失败。
        # 按顺序取, 直到累计长度接近上限为止。
        # 中文在 Whisper 分词器里约 1 字 = 1.5~2 token, 解码上下文只有 448 token。
        # 实测超过 ~150 字就会报 "maximum decoding length must be > 0", 故保守取 120 字。
        picked, total = [], 0
        for w in raw:
            if total + len(w) + 1 > 120:
                break
            picked.append(w)
            total += len(w) + 1
        hotwords = " ".join(picked)
        print(f"热词表 {len(raw)} 条, 本次使用前 {len(picked)} 条 (共 {len(hotwords)} 字)")

    ffmpeg = find_ffmpeg()
    print(f"ffmpeg: {ffmpeg}")

    corrections = load_corrections(args.corrections) if args.corrections else []
    if corrections:
        print(f"纠错规则: {len(corrections)} 条")

    from faster_whisper import WhisperModel

    device = args.device
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    compute_type = args.compute_type or ("float16" if device == "cuda" else "int8")
    print(f"模型: {args.model}  设备: {device}  精度: {compute_type}")
    model = WhisperModel(args.model, device=device, compute_type=compute_type)

    for i, f in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {f.name}")
        base = f.stem
        outdir = outroot / base
        outdir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "a.wav"
            extract_audio(ffmpeg, f, wav)
            silences = detect_silence(ffmpeg, f)
            (outdir / "silences.json").write_text(
                json.dumps(silences, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  停顿段: {len(silences)} 处")

            segments, info = model.transcribe(
                str(wav),
                language=args.lang,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
                hotwords=hotwords,
                beam_size=5,
                initial_prompt=None if hotwords else "以下是初中物理教学口播内容，请使用规范简体中文和物理术语。",
                # 抗重复幻觉: 口播里常有长停顿和口头禅, Whisper 容易陷入死循环
                condition_on_previous_text=False,
                repetition_penalty=1.08,
                no_repeat_ngram_size=3,
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                compression_ratio_threshold=2.2,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6,
            )

            segs, words_all, srt_lines = [], [], []
            for k, s in enumerate(segments, 1):
                text_fixed = apply_corrections(s.text.strip(), corrections)
                ws = [
                    {"w": w.word, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)}
                    for w in (s.words or [])
                ]
                segs.append(
                    {
                        "id": k,
                        "start": round(s.start, 3),
                        "end": round(s.end, 3),
                        "text": text_fixed,
                        "text_raw": s.text.strip(),
                        "words": ws,
                    }
                )
                words_all.extend(ws)
                srt_lines.append(
                    f"{k}\n{fmt_ts(s.start)} --> {fmt_ts(s.end)}\n{text_fixed}\n"
                )
                print(f"    {s.start:7.2f}-{s.end:7.2f}  {text_fixed[:60]}")

            data = {
                "file": str(f),
                "name": f.name,
                "language": info.language,
                "duration": round(info.duration, 3),
                "segments": segs,
                "words": words_all,
            }
            (outdir / "transcript.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (outdir / "transcript.txt").write_text(
                "\n".join(s["text"] for s in segs), encoding="utf-8"
            )
            (outdir / "transcript.srt").write_text("\n".join(srt_lines), encoding="utf-8")
            print(f"  完成 -> {outdir}")

    print("\n全部完成")


if __name__ == "__main__":
    main()
