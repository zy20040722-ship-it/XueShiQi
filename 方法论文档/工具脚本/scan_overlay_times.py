r"""
在一串按秒抽好的帧里, 找出某个"图示"覆层真正出现的时刻。

用法:
  python tools\scan_overlay_times.py <帧目录> <素材.png> [起始秒]
  python tools\scan_overlay_times.py <帧目录> <素材.png> [起始秒] --at <x>,<y>
      给了 --at 就只在那个位置算差值, 快得多(用来把整条片子扫一遍)。
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def luma(arr):
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]


def main():
    frames_dir = Path(sys.argv[1])
    png_path = sys.argv[2]
    args = sys.argv[3:]
    fixed = None
    if "--at" in args:
        i = args.index("--at")
        fixed = tuple(int(v) for v in args[i + 1].split(","))
        args = args[:i] + args[i + 2:]
    start = float(args[0]) if args else 0.0

    png = np.asarray(Image.open(png_path).convert("RGBA"), dtype=np.float32)
    alpha, png_gray = png[..., 3], luma(png)
    ys, xs = np.nonzero(alpha > 250)
    rng = np.random.default_rng(0)
    if len(ys) > 400:
        pick = rng.choice(len(ys), 400, replace=False)
        ys, xs = ys[pick], xs[pick]
    fp = png_gray[ys, xs]
    ph, pw = alpha.shape

    print(f"{Path(png_path).name}: {pw}x{ph}, 指纹 {len(ys)} 像素")
    hits = []
    for i, f in enumerate(sorted(frames_dir.glob("*.png"))):
        frame = luma(np.asarray(Image.open(f).convert("RGB"), dtype=np.float32))
        H, W = frame.shape
        if fixed:
            best = (float(np.abs(frame[fixed[1] + ys, fixed[0] + xs] - fp).mean()),
                    fixed[0], fixed[1])
        else:
            best = (1e9, 0, 0)
            for dy in range(0, H - ph + 1, 4):
                for dx in range(0, W - pw + 1, 4):
                    d = float(np.abs(frame[dy + ys, dx + xs] - fp).mean())
                    if d < best[0]:
                        best = (d, dx, dy)
        t = start + i
        mark = ""
        if best[0] < 8:
            hits.append(t)
            mark = "  <== 命中"
        print(f"  {t:6.1f}s  {best[0]:7.2f}  x={best[1]:4d} y={best[2]:4d}{mark}")
    print(f"命中区间: {hits[0] if hits else '-'} ~ {hits[-1] if hits else '-'}")


if __name__ == "__main__":
    main()
