# -*- coding: utf-8 -*-
"""
按新模板生成封面: 深色底 + 两行渐变立体标题
  第一行 蓝色渐变(亮蓝->深蓝)  第二行 金色渐变(淡金->橙金)
  两行都带白色描边 + 深色立体挤出 + 轻微右倾
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
OUT = WS / "精剪"

W, H = 1080, 1920
LINE1 = "以前正常学的知识"
LINE2 = "为什么现在成了超纲"

# 字体: SOP 指定标题用「丽金黑」(华康俪金黑W8), 优先用它;
# 找不到再退回思源黑体重字重 / 微软雅黑粗体 / 华文中宋
FONT_CANDIDATES = [
    (str(WS / "方法论文档" / "字体源文件" / "DFPLiJinHeiW8-GB.TTF"), [None]),
    (r"C:\Windows\Fonts\NotoSansSC-VF.ttf", ["Black", "ExtraBold", "Bold"]),
    (r"C:\Windows\Fonts\Source Han Serif SC Heavy (TrueType).ttf", [None]),
    (r"C:\Windows\Fonts\msyhbd.ttc", [None]),
    (r"C:\Windows\Fonts\STZHONGS.TTF", [None]),
]


def load_font(size):
    for path, weights in FONT_CANDIDATES:
        p = Path(path)
        if not p.exists():
            continue
        try:
            f = ImageFont.truetype(str(p), size)
        except Exception:
            continue
        for wname in weights:
            if not wname:
                return f, p.name
            try:
                f.set_variation_by_name(wname)
                return f, f"{p.name} [{wname}]"
            except Exception:
                continue
        return f, p.name
    raise SystemExit("找不到可用字体")


def vgrad(w, h, top, bottom):
    g = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(g)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line([(0, y), (w, y)],
               fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g


def make_line(text, font, cy, top_rgb, bot_rgb, outline_rgb, extrude_rgb, depth, shear=0.16, outline_w=9):
    """返回一张 RGBA 文字图, 已带描边 + 立体 + 倾斜"""
    box = font.getbbox(text)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad = outline_w + depth + 24
    cw, ch = tw + pad * 2, th + pad * 2

    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).text((pad - box[0], pad - box[1]), text, font=font, fill=255)

    # 外描边(白)
    stroke = mask.filter(ImageFilter.MaxFilter(outline_w * 2 + 1))
    stroke_img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    stroke_img.paste(outline_rgb + (255,), (0, 0), stroke)

    # 立体挤出(深色, 往右下叠)
    extr = Image.new("RGBA", (cw + depth, ch + depth), (0, 0, 0, 0))
    for i in range(depth, 0, -1):
        layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        layer.paste(extrude_rgb + (255,), (0, 0), stroke)
        extr.alpha_composite(layer, (i, i))

    # 面: 竖向渐变
    face = vgrad(cw, ch, top_rgb, bot_rgb).convert("RGBA")
    face.putalpha(mask)

    base = Image.new("RGBA", (cw + depth, ch + depth), (0, 0, 0, 0))
    base.alpha_composite(extr)
    base.alpha_composite(stroke_img)
    base.alpha_composite(face)

    # 轻微右倾
    if shear:
        new_w = int(base.width + abs(shear) * base.height)
        base = base.transform((new_w, base.height), Image.AFFINE,
                              (1, shear, -shear * base.height, 0, 1, 0), resample=Image.BICUBIC)
    return base


def main():
    frame_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else (OUT / "封面.png")
    # 第三个参数给 light 时只压暗上半部分 —— 棚拍人像那种本身就干净的底片用这个
    mode = sys.argv[3] if len(sys.argv) > 3 else "strong"
    frame = Image.open(frame_path).convert("RGBA").resize((W, H), Image.LANCZOS)

    # 压暗成模板那种深色底: 上半部浓、下半部轻(light 模式下只压顶部标题区)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(H):
        if mode == "light":
            a = int(205 * max(0.0, 1 - y / 720.0) ** 0.85)
        else:
            a = int(215 * max(0.0, 1 - (y / H) * 1.35) ** 0.9) + 70
        d.line([(0, y), (W, y)], fill=(10, 14, 22, min(230, a)))
    frame.alpha_composite(ov)

    f1, used = load_font(112)
    f2, _ = load_font(92)
    print(f"标题字体: {used}")

    L1 = make_line(LINE1, f1, 0,
                   (235, 246, 255), (36, 110, 224),      # 蓝: 亮->深
                   (255, 255, 255), (12, 40, 92), 12)
    frame.alpha_composite(L1, ((W - L1.width) // 2, 120))

    L2 = make_line(LINE2, f2, 0,
                   (255, 250, 214), (240, 158, 0),       # 金: 淡金->橙金
                   (255, 255, 255), (120, 62, 0), 10)
    frame.alpha_composite(L2, ((W - L2.width) // 2, 120 + L1.height - 26))

    frame.convert("RGB").save(out_path)
    print(f"封面已生成: {out_path}")


if __name__ == "__main__":
    main()
