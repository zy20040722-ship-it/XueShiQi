# -*- coding: utf-8 -*-
r"""
把竖版人像底片补成 1080x1920(9:16): 按宽度缩放, 上面的空白用底片自己的背景色延伸。
用法: python tools\prepare_cover_base.py <底片.png> <输出.png>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1080, 1920


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    im = Image.open(src).convert("RGB")
    new_h = round(im.height * W / im.width)
    im2 = im.resize((W, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))

    if new_h <= H:
        top = H - new_h
        # 取底片顶部 8 行的平均色, 往上做一条由深到浅的渐变, 接缝看不出来
        band = im2.crop((0, 0, W, 8)).resize((1, 1), Image.LANCZOS).getpixel((0, 0))
        grad = Image.new("RGB", (W, top))
        d = ImageDraw.Draw(grad)
        for y in range(top):
            t = y / max(1, top - 1)
            d.line([(0, y), (W, y)],
                   fill=tuple(int(band[i] * (0.80 + 0.20 * t)) for i in range(3)))
        canvas.paste(grad, (0, 0))
        canvas.paste(im2, (0, top))
        print(f"顶部延伸 {top}px, 人像落在 y={top}..{H}")
    else:
        canvas.paste(im2.crop((0, (new_h - H) // 2, W, (new_h - H) // 2 + H)), (0, 0))
        print("底片太高, 居中裁切")

    canvas.save(out)
    print(f"已生成 {out}  {canvas.size}")


if __name__ == "__main__":
    main()
