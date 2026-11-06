# -*- coding: utf-8 -*-
"""生成封面: 实拍帧 + 顶部渐变压暗 + 两行立体标题"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
OUT = WS / "精剪"
FONT = r"C:\Windows\Fonts\STZHONGS.TTF"
W, H = 1080, 1920

LINE1 = "以前正常学的知识"
LINE2 = "为什么现在成了超纲"


def font(sz):
    return ImageFont.truetype(FONT, sz)


def text_mask(text, f, pad=20):
    box = f.getbbox(text)
    w, h = box[2] - box[0], box[3] - box[1]
    m = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    ImageDraw.Draw(m).text((pad - box[0], pad - box[1]), text, font=f, fill=255)
    return m


def gradient(w, h, c1, c2):
    g = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(g)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)],
               fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return g


def draw_3d_title(base, text, f, cx, top, light, dark, depth=14):
    mask = text_mask(text, f)
    w, h = mask.size
    x = cx - w // 2
    # 挤出层: 一层层往右下叠, 形成厚度
    for i in range(depth, 0, -1):
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        layer.paste(dark + (255,), (0, 0), mask)
        base.alpha_composite(layer, (x + i, top + i))
    # 描边
    outline = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    om = mask.filter(ImageFilter.MaxFilter(9))
    outline.paste((10, 14, 24, 255), (0, 0), om)
    base.alpha_composite(outline, (x, top))
    # 面: 用渐变填充
    grad = gradient(w, h, light[0], light[1]).convert("RGBA")
    grad.putalpha(mask)
    base.alpha_composite(grad, (x, top))
    return h


def main():
    frame_path = Path(sys.argv[1])
    frame = Image.open(frame_path).convert("RGBA").resize((W, H), Image.LANCZOS)

    # 顶部渐变压暗, 让标题看得清
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(0, 1000):
        a = int(215 * (1 - y / 1000) ** 1.15)
        od.line([(0, y), (W, y)], fill=(8, 16, 34, a))
    # 底部也压一点, 显得稳
    for y in range(H - 420, H):
        a = int(150 * ((y - (H - 420)) / 420) ** 1.2)
        od.line([(0, y), (W, y)], fill=(8, 16, 34, a))
    frame.alpha_composite(overlay)

    d = ImageDraw.Draw(frame)
    f1 = font(96)
    f2 = font(104)
    draw_3d_title(frame, LINE1, f1, W // 2, 150,
                  ((255, 255, 255), (176, 220, 255)), (28, 74, 150))
    draw_3d_title(frame, LINE2, f2, W // 2, 300,
                  ((255, 244, 190), (255, 176, 40)), (150, 78, 10))

    # 左下角一行小字
    d.text((60, H - 190), "初高断层 · 到底断在哪", font=font(40), fill=(210, 224, 240, 235))
    d.text((60, H - 130), "薛世奇说物理", font=font(34), fill=(150, 170, 195, 220))

    out = OUT / "封面.png"
    frame.convert("RGB").save(out)
    print(f"封面已生成: {out}")


if __name__ == "__main__":
    main()
