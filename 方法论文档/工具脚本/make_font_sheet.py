# -*- coding: utf-8 -*-
"""生成字体对比图: 把候选字体渲染同一句话, 纵向拼起来, 顶部放用户给的参考图"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REF = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path(sys.argv[2])
SAMPLE = "甚至好高中的"

FONTDIR = Path(r"C:\Windows\Fonts")
CANDIDATES = [
    ("STZHONGS.TTF",                              "01 华文中宋 STZhongsong"),
    ("NotoSerifSC-VF.ttf",                        "02 思源宋体 Noto Serif SC"),
    ("Source Han Serif SC Heavy (TrueType).ttf",  "03 思源宋体 Heavy"),
    ("STSONG.TTF",                                "04 华文宋体 STSong"),
    ("simsun.ttc",                                "05 中易宋体 SimSun（系统默认宋体）"),
    ("simkai.ttf",                                "06 楷体 KaiTi"),
    ("STKAITI.TTF",                               "07 华文楷体 STKaiti"),
    ("msyh.ttc",                                  "08 微软雅黑（对照，非衬线）"),
    ("simhei.ttf",                                "09 黑体（对照，非衬线）"),
]

W, ROW_H = 1500, 250
BG = (42, 42, 42)
TEXT_SIZE, LABEL_SIZE = 118, 30


def load(path, size):
    p = FONTDIR / path
    if not p.exists():
        return None
    try:
        return ImageFont.truetype(str(p), size)
    except Exception:
        return None


rows = []

# 顶部: 用户给的参考图
if REF and REF.exists():
    ref = Image.open(REF).convert("RGB")
    scale = W / ref.width
    ref = ref.resize((W, max(1, int(ref.height * scale))), Image.LANCZOS)
    ref = ref.crop((0, 0, W, min(ref.height, ROW_H)))
    strip = Image.new("RGB", (W, ROW_H), (20, 20, 20))
    strip.paste(ref, (0, 0))
    d = ImageDraw.Draw(strip)
    lab = load("msyh.ttc", LABEL_SIZE)
    d.text((16, ROW_H - 40), "【参考】你发的那张", font=lab, fill=(120, 220, 120))
    rows.append(strip)

ok = 0
for fname, label in CANDIDATES:
    f = load(fname, TEXT_SIZE)
    if f is None:
        print(f"  跳过(读不到): {fname}")
        continue
    img = Image.new("RGB", (W, ROW_H), BG)
    d = ImageDraw.Draw(img)
    # 白字黑边
    x, y = 50, 40
    for dx in (-4, 0, 4):
        for dy in (-4, 0, 4):
            d.text((x + dx, y + dy), SAMPLE, font=f, fill=(0, 0, 0))
    d.text((x, y), SAMPLE, font=f, fill=(255, 255, 255))
    lab = load("msyh.ttc", LABEL_SIZE)
    d.text((52, 196), label, font=lab, fill=(150, 150, 150))
    rows.append(img)
    ok += 1
    print(f"  已渲染: {label}")

sheet = Image.new("RGB", (W, ROW_H * len(rows)), BG)
for i, r in enumerate(rows):
    sheet.paste(r, (0, i * ROW_H))
sheet.save(OUT)
print(f"\n对比图已生成: {OUT}   ({ok} 款字体)")
