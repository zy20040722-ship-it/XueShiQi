# -*- coding: utf-8 -*-
"""画初中物理示意图卡片(透明底 PNG)。卡片放在画面顶部空白区, 不挡脸。"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
OUT = WS / "精剪" / "图示"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 900, 360
SS = 3
FONT_PATH = r"C:\Windows\Fonts\STZHONGS.TTF"
BG = (16, 20, 28, 220)
FG = (238, 243, 250, 255)
DIM = (160, 172, 190, 255)
GOLD = (255, 214, 0, 255)
CYAN = (110, 210, 255, 255)
SALMON = (255, 150, 120, 255)


def font(sz):
    return ImageFont.truetype(FONT_PATH, sz * SS)


def label(d, x, y, s, size=28, color=FG, anchor="la"):
    d.text((x * SS, y * SS), s, font=font(size), fill=color, anchor=anchor)


def arrow(d, x1, y1, x2, y2, color, w=3, head=15):
    d.line([x1 * SS, y1 * SS, x2 * SS, y2 * SS], fill=color, width=w * SS)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (math.radians(152), math.radians(-152)):
        hx = x2 + head * math.cos(ang + da)
        hy = y2 + head * math.sin(ang + da)
        d.line([x2 * SS, y2 * SS, hx * SS, hy * SS], fill=color, width=w * SS)


def card():
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W * SS - 1, H * SS - 1], radius=24 * SS, fill=BG)
    d.rounded_rectangle([0, 0, W * SS - 1, H * SS - 1], radius=24 * SS, outline=(70, 90, 120, 200), width=2 * SS)
    return img, d


def incline():
    img, d = card()
    label(d, 40, 24, "斜面上的受力分析", 34)
    # 三角形: 直角在左下
    ox, oy = 150, 268
    tx, ty = 560, 268
    px, py = 150, 120
    for a, b, c, e in ((ox, oy, tx, ty), (ox, oy, px, py), (px, py, tx, ty)):
        d.line([a * SS, b * SS, c * SS, e * SS], fill=(200, 210, 225, 230), width=3 * SS)
    label(d, 300, 278, "斜面", 24, DIM)

    t = 0.5
    bx, by = ox + (px - ox) * t, oy + (py - oy) * t
    ang = math.atan2(py - oy, px - ox)
    ca, sa = math.cos(ang), math.sin(ang)
    nx, ny = -sa, ca
    L, Wd = 84, 56
    pts = [((bx + dx * ca + dy * nx) * SS, (by + dx * sa + dy * ny) * SS)
           for dx, dy in ((-L / 2, 0), (L / 2, 0), (L / 2, -Wd), (-L / 2, -Wd))]
    d.polygon(pts, fill=(64, 104, 168, 255), outline=(230, 238, 248, 255), width=2 * SS)

    cx, cy = bx - Wd / 2 * nx, by - Wd / 2 * ny
    arrow(d, cx, cy, cx, cy + 104, GOLD)
    arrow(d, cx, cy, cx - 92 * nx, cy - 92 * ny, CYAN)
    arrow(d, cx, cy, cx + 84 * ca, cy + 84 * sa, SALMON)
    label(d, cx + 100 * ca, cy + 100 * sa, "f", 24, SALMON, "lm")

    label(d, 640, 100, "重力 G", 26, GOLD)
    label(d, 640, 146, "支持力 N", 26, CYAN)
    label(d, 640, 192, "摩擦力 f", 26, SALMON)
    label(d, 40, 316, "初中只要求定性看方向，高中要算大小和分解", 22, DIM)
    return img


def boat():
    img, d = card()
    label(d, 40, 24, "浮力问题中的船球模型", 34)
    wy = 232
    d.line([60 * SS, wy * SS, 840 * SS, wy * SS], fill=CYAN, width=3 * SS)
    label(d, 764, 242, "水面", 22, CYAN)

    # 船体: 上沿在 200, 底部 272, 水面 232 穿过船身
    d.polygon([(230 * SS, 200 * SS), (610 * SS, 200 * SS),
               (556 * SS, 272 * SS), (284 * SS, 272 * SS)],
              fill=(150, 112, 72, 255), outline=(240, 232, 220, 255), width=2 * SS)
    label(d, 420, 214, "船", 26, (255, 248, 236, 255), "ma")

    # 球
    d.ellipse([(486 - 40) * SS, (158 - 40) * SS, (486 + 40) * SS, (158 + 40) * SS],
              fill=(226, 88, 88, 255), outline=(255, 240, 240, 255), width=2 * SS)

    # 左下角画力: 浮力向上 / 重力向下
    arrow(d, 150, 252, 150, 172, GOLD)
    arrow(d, 150, 252, 150, 318, (140, 220, 140, 255))

    label(d, 640, 116, "浮力 ↑　重力 ↓", 24, GOLD)
    label(d, 640, 158, "球放船上：船下沉一点", 24, FG)
    label(d, 640, 198, "球丢水里：水面反而降", 24, FG)
    label(d, 40, 316, "排水量怎么变，是这类题的考点", 22, DIM)
    return img


def belt():
    """传送带上的物块受力: 竖直两个力, 水平一个摩擦力"""
    img, d = card()
    label(d, 40, 24, "传送带的受力分析", 34)

    # 两个滚轮 + 皮带
    for cx in (170, 730):
        d.ellipse([(cx - 32) * SS, (250 - 32) * SS, (cx + 32) * SS, (250 + 32) * SS],
                  fill=(58, 70, 88, 255), outline=(210, 220, 235, 255), width=2 * SS)
        d.ellipse([(cx - 8) * SS, (250 - 8) * SS, (cx + 8) * SS, (250 + 8) * SS],
                  fill=(140, 152, 170, 255))
    for y in (218, 282):
        d.line([170 * SS, y * SS, 730 * SS, y * SS], fill=(200, 210, 225, 230), width=3 * SS)

    # 物块(坐在上层皮带上)
    d.rectangle([275 * SS, 150 * SS, 385 * SS, 218 * SS],
                fill=(64, 104, 168, 255), outline=(230, 238, 248, 255), width=2 * SS)
    label(d, 330, 168, "物块", 22, (238, 243, 250, 255), "ma")

    cx, cy = 330, 184
    arrow(d, cx, cy, cx, 92, CYAN)                 # 支持力 N
    arrow(d, cx, cy, cx, 252, GOLD)                # 重力 G
    arrow(d, cx + 20, 206, cx + 140, 206, SALMON)  # 摩擦力 f

    # 皮带运动方向(画在皮带圈里, 别跟底部说明打架)
    arrow(d, 450, 250, 560, 250, CYAN, 3)
    label(d, 570, 244, "皮带运动方向", 22, CYAN, "lm")

    label(d, 640, 96, "重力 G", 26, GOLD)
    label(d, 640, 142, "支持力 N", 26, CYAN)
    label(d, 640, 188, "摩擦力 f", 26, SALMON)
    label(d, 40, 316, "摩擦力方向看相对运动，不一定跟运动方向相反", 22, DIM)
    return img


def gear(d, cx, cy, r, teeth, color, tooth=11):
    pts = []
    for i in range(teeth * 4):
        ang = i * math.pi * 2 / (teeth * 4)
        rr = r + (tooth if (i % 4) in (1, 2) else 0)
        pts.append(((cx + math.cos(ang) * rr) * SS, (cy + math.sin(ang) * rr) * SS))
    d.polygon(pts, fill=color, outline=(235, 240, 248, 255), width=2 * SS)
    d.ellipse([(cx - r * 0.18) * SS, (cy - r * 0.18) * SS,
               (cx + r * 0.18) * SS, (cy + r * 0.18) * SS],
              fill=(20, 26, 36, 255), outline=(220, 228, 240, 255), width=2 * SS)


def arc_arrow(d, cx, cy, r, a0, a1, color):
    """齿轮上的转向箭头(一段弧 + 箭头)"""
    d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS],
          start=a0, end=a1, fill=color, width=3 * SS)
    ex = cx + r * math.cos(math.radians(a1))
    ey = cy + r * math.sin(math.radians(a1))
    tang = math.radians(a1 + (90 if a1 > a0 else -90))
    for da in (math.radians(150), math.radians(-150)):
        d.line([ex * SS, ey * SS,
                (ex + 15 * math.cos(tang + da)) * SS,
                (ey + 15 * math.sin(tang + da)) * SS], fill=color, width=3 * SS)


def gears():
    """组合机械: 一大一小两个齿轮咬合 → 传动比"""
    img, d = card()
    label(d, 40, 24, "组合机械当中的传动模型", 34)

    r1, r2 = 88, 56
    cx1, cy1 = 250, 200
    cx2, cy2 = cx1 + r1 + r2 + 6, cy1
    gear(d, cx1, cy1, r1, 18, (64, 104, 168, 255))
    gear(d, cx2, cy2, r2, 12, (196, 150, 70, 255))
    arc_arrow(d, cx1, cy1, r1 + 22, 200, 340, CYAN)
    arc_arrow(d, cx2, cy2, r2 + 22, 20, -120, SALMON)

    label(d, cx1, cy1 + 6, "大齿轮", 22, (240, 244, 250, 255), "mm")
    label(d, cx2, cy2 + 6, "小齿轮", 20, (255, 248, 236, 255), "mm")
    label(d, 640, 108, "咬合处线速度相同", 24, FG)
    label(d, 640, 152, "转向相反", 24, CYAN)
    label(d, 640, 196, "转速与齿数成反比", 24, GOLD)
    label(d, 40, 316, "组合机械先看传动比，再看省力不省力", 22, DIM)
    return img


for name, fn in (("斜面受力分析.png", incline), ("船球模型.png", boat),
                 ("传送带受力分析.png", belt), ("传动模型.png", gears)):
    fn().resize((W, H), Image.LANCZOS).save(OUT / name)
    print(f"已生成 {name}  {W}x{H}")
