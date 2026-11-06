# -*- coding: utf-8 -*-
r"""
从"参考片"里读出顶部金色副标题: 金色文字出现的时段 + 每段长什么样。

做法: 按秒抽帧 -> 裁出副标题那条横带 -> 用金色像素生成指纹 -> 相邻帧相同时段合并,
      每段挑一帧拼成对比图, 人工核对文字。

用法: python tools\read_ref_subtitles.py <参考视频> [输出目录]
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
FFMPEG = r"D:\Software\ffmpeg\bin\ffmpeg.exe"

# 副标题在 1080x1920 画面里的位置(见 references\版式与实现.md: y≈415-510, 留点余量)
BAND_Y, BAND_H = 400, 130
GOLD_MIN_R, GOLD_MIN_G, GOLD_MAX_B = 170, 120, 130


def gold_mask(img):
    a = np.asarray(img.convert("RGB"), dtype=np.int16)
    m = ((a[..., 0] > GOLD_MIN_R) & (a[..., 1] > GOLD_MIN_G) &
         (a[..., 2] < GOLD_MAX_B)).astype(np.uint8)
    small = Image.fromarray(m * 255).resize((54, 7), Image.BILINEAR)
    return (np.asarray(small) > 40).astype(np.uint8)


def main():
    src = sys.argv[1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else (WS / "分析" / "参考副标题")
    out.mkdir(parents=True, exist_ok=True)

    frames = out / "frames"
    frames.mkdir(exist_ok=True)
    for f in frames.glob("*.png"):
        f.unlink()

    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", src,
                    "-vf", f"fps=1,crop=1080:{BAND_H}:0:{BAND_Y}",
                    "-y", str(frames / "%04d.png")], check=True)

    files = sorted(frames.glob("*.png"))
    print(f"抽到 {len(files)} 帧 (每秒 1 帧), 副标题带 y={BAND_Y}..{BAND_Y + BAND_H}")

    groups = []
    prev = None
    for i, f in enumerate(files):
        sig = gold_mask(Image.open(f))
        n = int(sig.sum())
        new = prev is None or n == 0 or prev.sum() == 0 or (sig != prev).sum() > 6
        if new:
            groups.append([i, i, f, n])
        else:
            groups[-1][1] = i
            if n > groups[-1][3]:
                groups[-1][2] = f
                groups[-1][3] = n
        prev = sig

    groups = [g for g in groups if g[3] > 30]
    print(f"金色副标题共 {len(groups)} 段:")
    for a, b, f, n in groups:
        print(f"  {a:4d}s ~ {b:4d}s   代表帧 {f.name}  金色像素 {n}")

    if groups:
        h = BAND_H
        sheet = Image.new("RGB", (1080, h * len(groups)), (0, 0, 0))
        for k, (a, b, f, _n) in enumerate(groups):
            sheet.paste(Image.open(f).convert("RGB"), (0, k * h))
        p = out / "副标题分段对照.png"
        sheet.save(p)
        print(f"对照图: {p}")


if __name__ == "__main__":
    main()
