# -*- coding: utf-8 -*-
"""
生成成片用的 ASS: 主标题 + 副标题 + 正文三套样式。
  主标题: 丽金黑, 顶部居中两行, 全程挂着不消失
  副标题: 丽金黑, 金色, 挂在主标题下方, 进入放大/淡出, 每条持续到下一条
  正文:   金陵体, 单行(每句 ≤8 字, 由 split_single_line.py 保证)

字体名可以命令行覆盖:
  python tools\build_final_ass.py "方正粗金陵简体" "华康俪金黑W8(P)"
"""
import json
import sys
from pathlib import Path

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
OUT = WS / "精剪"
# SOP: 字幕用「金陵体」, 标题/花字用「丽金黑」。
# 字体文件在 字体\ 目录, 实际族名:
#   FZJinLS-B-GB.ttf      -> 方正粗金陵简体
#   DFPLiJinHeiW8-GB.TTF  -> 华康俪金黑W8(P)
FONT_SUB = sys.argv[1] if len(sys.argv) > 1 else "方正粗金陵简体"
FONT_TITLE = sys.argv[2] if len(sys.argv) > 2 else "华康俪金黑W8(P)"

# SOP 步骤 6.2 的总标题: 全程挂在画面上方
MAIN_TITLE = ["以前正常学的知识", "为什么现在成了超纲"]
DURATION = 211.776

# SOP 步骤 6.3 的"分论点副标题": 3 条, 每条持续显示到下一条出现。
# 这次的文案是从参考片(薛老师已发布的成片)里读出来的, 时间对到本片时间轴:
#   参考片 0-37s「近20年学生能力反而下降？」/ 38-67s「课标从下限变成了上限」
#   68-125s「初中培优课变成了初高贯通课」; 本片对应内容分别起于 0 / 45.5 / 80.3s。
SUBTITLE_LINES = [
    ("近20年学生能力反而下降？",   0.00,  45.50),
    ("课标从下限变成了上限",      45.50,  80.30),
    ("初中培优课变成了初高贯通课", 80.30, 149.70),
]


def ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: 主标题,{FONT_TITLE},100,&H00FFFFFF,&H00FFFFFF,&H00101010,&H59000000,0,0,0,0,100,100,4,0,1,8,4,8,60,60,190,1
Style: 副标题,{FONT_TITLE},76,&H001EA0FF,&H001EA0FF,&H00101010,&H59000000,0,0,0,0,100,100,2,0,1,6,4,8,60,60,435,1
Style: 正文,{FONT_SUB},74,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,2,0,1,6,4,2,70,70,450,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def main():
    data = json.loads((OUT / "字幕数据.json").read_text(encoding="utf-8"))
    cues = data["cues"]
    events = []

    # 主标题: 从 0 挂到片尾, 不动
    title_text = "\\N".join(MAIN_TITLE)
    events.append(
        f"Dialogue: 2,{ass_time(0)},{ass_time(DURATION)},主标题,,0,0,0,,{title_text}"
    )

    # 副标题放在上层(Layer 1), 正文在下层(Layer 0)
    for text, a, b in SUBTITLE_LINES:
        fx = r"{\fad(200,260)\fscx78\fscy78\t(0,220,\fscx100\fscy100)}"
        events.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},副标题,,0,0,0,,{fx}{text}")

    over = [c for c in cues if len(c["text"]) > 8]
    for c in cues:
        events.append(
            f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},正文,,0,0,0,,{c['text']}"
        )

    (OUT / "成片字幕.ass").write_text(HEAD + "\n".join(events) + "\n", encoding="utf-8")
    print(f"字幕字体: {FONT_SUB}   标题字体: {FONT_TITLE}")
    print(f"主标题: {' / '.join(MAIN_TITLE)}")
    print(f"成片字幕.ass 已生成: {len(cues)} 句正文(单行) + {len(SUBTITLE_LINES)} 条副标题")
    if over:
        print(f"  ！仍有 {len(over)} 句超过 8 字: {[c['text'] for c in over[:3]]}")
    for t, a, b in SUBTITLE_LINES:
        print(f"  {a:7.2f}-{b:7.2f}  {t}")


if __name__ == "__main__":
    main()
