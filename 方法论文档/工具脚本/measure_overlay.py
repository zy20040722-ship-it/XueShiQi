# -*- coding: utf-8 -*-
r"""
量出成片画面里"图示"覆层的落点。
方法: 拿素材 PNG 里完全不透明的像素当指纹, 在画面里滑窗找差值最小的位置。

用法: python tools\measure_overlay.py <画面截图.png> <素材.png>
"""
import sys

import numpy as np
from PIL import Image


def luma(arr):
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]


def score(frame, ys, xs, fp, dy, dx):
    return float(np.abs(frame[dy + ys, dx + xs] - fp).mean())


def main():
    frame_path, png_path = sys.argv[1], sys.argv[2]
    frame = luma(np.asarray(Image.open(frame_path).convert("RGB"), dtype=np.float32))
    png = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.float32)
    alpha, png_gray = png[..., 3], luma(png)
    H, W = frame.shape[:2]
    ph, pw = alpha.shape

    ys, xs = np.nonzero(alpha > 250)
    if len(ys) == 0:
        raise SystemExit("素材没有不透明像素")
    rng = np.random.default_rng(0)
    if len(ys) > 400:
        pick = rng.choice(len(ys), 400, replace=False)
        ys, xs = ys[pick], xs[pick]
    fp = png_gray[ys, xs]
    print(f"指纹像素 {len(ys)} 个; 画面 {W}x{H}; 素材 {pw}x{ph}")

    best = (1e9, 0, 0)
    for dy in range(0, H - ph + 1, 4):
        for dx in range(0, W - pw + 1, 4):
            d = score(frame, ys, xs, fp, dy, dx)
            if d < best[0]:
                best = (d, dx, dy)

    _, bx, by = best
    for dy in range(max(0, by - 5), min(H - ph, by + 5) + 1):
        for dx in range(max(0, bx - 5), min(W - pw, bx + 5) + 1):
            d = score(frame, ys, xs, fp, dy, dx)
            if d < best[0]:
                best = (d, dx, dy)

    d, x, y = best
    print(f"最佳匹配: 平均差值 {d:.2f}")
    print(f"落点 x={x} y={y}   右边距 {W - pw - x}   下边距 {H - ph - y}")


if __name__ == "__main__":
    main()
