# -*- coding: utf-8 -*-
"""
把「带标点的正文」对齐到「逐词时间戳」, 生成字幕。

输入:
  精剪/清洗后词表.json     已纠错的逐词时间戳(由 clean_text.py 产出)
  精剪/正文加标点.txt      人工加好标点的正文(只能多标点, 不能改字)
输出:
  精剪/字幕数据.json       与剪辑软件无关的中间数据
  精剪/字幕.ass            可直接烧录
"""
import json
import sys
from pathlib import Path

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
OUT = WS / "精剪"
FONT = sys.argv[1] if len(sys.argv) > 1 else "STZhongsong"

MAX_CHARS = 16      # 一句最多多少字
MIN_CHARS = 6       # 到标点时如果不足这个字数, 就并到下一句
MIN_DUR = 0.8       # 一句至少显示多久
FIRST_GAP = 0.05    # 与上一句衔接时留的最小空隙

PUNCT = "，。？！、：；…—"


def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def wrap(text, per_line):
    return [text[i:i + per_line] for i in range(0, len(text), per_line)] or [""]


def main():
    toks = json.loads((OUT / "清洗后词表.json").read_text(encoding="utf-8"))
    raw = (OUT / "正文加标点.txt").read_text(encoding="utf-8")
    # 去掉所有空白, 只留正文和标点
    punctuated = "".join(ch for ch in raw if not ch.isspace())

    # 建一张「第几个非空白字符 -> 属于哪个词」的索引表
    # (词里可能含空格, 比如 "Tangent Theta", 空格不参与对齐)
    seq = []
    for ti, t in enumerate(toks):
        for ci, ch in enumerate(t["t"]):
            if ch.isspace():
                continue
            seq.append((ti, ci))
    plain = "".join(toks[ti]["t"][ci] for ti, ci in seq)
    stripped = "".join(ch for ch in punctuated if ch not in PUNCT)
    if plain != stripped:
        # 找出第一处不同, 方便定位
        for i, (a, b) in enumerate(zip(plain, stripped)):
            if a != b:
                print(f"!! 对不齐: 第 {i} 字  词表里是「{a}」 正文里是「{b}」")
                print(f"   词表: ...{plain[max(0,i-25):i+25]}...")
                print(f"   正文: ...{stripped[max(0,i-25):i+25]}...")
                sys.exit(1)
        print(f"!! 长度不同: 词表 {len(plain)} 字, 正文 {len(stripped)} 字")
        sys.exit(1)
    print(f"对齐成功: 正文 {len(plain)} 字, 标点 {len(punctuated)-len(stripped)} 个")

    # 标点位置 -> 第几个词之后断开
    break_after = set()
    k = 0
    for ch in punctuated:
        if ch in PUNCT:
            if k > 0:
                break_after.add(seq[k - 1][0])
            continue
        k += 1

    # 切句
    cues, cur = [], []
    for i, t in enumerate(toks):
        cur.append(t)
        n = sum(len(x["t"]) for x in cur)
        at_punct = i in break_after
        hard = n >= MAX_CHARS or (at_punct and n >= MIN_CHARS) or i == len(toks) - 1
        if hard:
            cues.append({
                "start": round(cur[0]["s"], 3),
                "end": round(cur[-1]["e"], 3),
                "text": "".join(x["t"] for x in cur),
            })
            cur = []
    print(f"初步切出 {len(cues)} 句")

    # 太短的并到上一句
    merged = []
    for c in cues:
        if merged and len(c["text"]) < MIN_CHARS and len(merged[-1]["text"]) + len(c["text"]) <= MAX_CHARS + 3:
            merged[-1]["end"] = c["end"]
            merged[-1]["text"] += c["text"]
        else:
            merged.append(c)

    # 最短显示时长 + 衔接空隙
    for c in merged:
        if c["end"] - c["start"] < MIN_DUR:
            c["end"] = round(c["start"] + MIN_DUR, 3)
    for a, b in zip(merged, merged[1:]):
        if b["start"] < a["end"]:
            a["end"] = round(b["start"] - 0.01, 3)

    lens = [len(c["text"]) for c in merged]
    print(f"最终 {len(merged)} 句, 平均 {sum(lens)/len(lens):.1f} 字, 最长 {max(lens)} 字")

    (OUT / "字幕数据.json").write_text(
        json.dumps({"font": FONT, "cues": merged}, ensure_ascii=False, indent=2), encoding="utf-8")

    per_line = 8
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: 正文,{FONT},74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,5,3,2,70,70,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},正文,,0,0,0,,"
             + "\\N".join(wrap(c["text"], per_line)) for c in merged]
    (OUT / "字幕.ass").write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"已写出 字幕数据.json / 字幕.ass")
    print("\n前 18 句:")
    for c in merged[:18]:
        print(f"  {c['start']:7.2f}-{c['end']:7.2f}  {c['text']}")


if __name__ == "__main__":
    main()
