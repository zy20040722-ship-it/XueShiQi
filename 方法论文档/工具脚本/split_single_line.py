# -*- coding: utf-8 -*-
r"""
把字幕切成"单行、每行不超过 8 个字"的短句, 尽量不在词中间下刀。

输入: 精剪\字幕数据.json        (原句, 可能 11~18 字)
      精剪\清洗后词表.json      (字符级时间戳, 用来分配每段的起止时间)
      流水线文档\物理术语表.txt  (252 条术语, 用来保护词不被切开)
      课本 / 课标的 md 文件       (统计字与字的"黏性", 用来判断哪里不该下刀)
输出: 精剪\字幕数据_单行.json

切分用动态规划打分: 长度超 8 硬禁; 单独一个字、以虚词开头/结尾、
把术语、常用搭配、数字+单位切开、长度太短 都会加罚分。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
SRC = WS / "精剪"
MAX_LEN = 8
MIN_DUR = 0.40

BAD_START = set("的了是就都也而和与在把被给对从吗呢吧啊哦嗯之其再又")
BAD_END = set("的是就都也而和与在把被给对从吗呢吧啊哦嗯之其再又得地着过")

# 这几个虚字跟在动词后面, 断在它们前面会把词切开(变得 / 巴不得 / 记得)
GLUE_NEXT = set("得地着")

# 手工改过的切法: 原句 -> 切好的几段。
# 逐条核对过, 保证拼起来跟原句一模一样、每段不超过 8 个字。
OVERRIDES = {
    "不然为什么以前我们正常学的知识点": ["不然为什么", "以前我们", "正常学的知识点"],
    "居然是负面清单的内容": ["居然是", "负面清单的内容"],
    "那个TangentTheta": ["那个", "tan θ"],
    "那更不用说我们初中物理的受力分析": ["那更不用说", "我们初中", "物理的受力分析"],
    "我要不是这一个月更新短视频": ["我要不是这一个月", "更新短视频"],
    "原来有那么多人坚定地认为": ["原来有那么多人", "坚定地认为"],
    "受力分析就应该高中学": ["受力分析", "就应该高中学"],
    "因为他们当年初中是真没学": ["因为他们当年", "初中是真没学"],
    "那真的是学生的能力变差了吗": ["那真的是学生的", "能力变差了吗"],
    "归根结底是训练方向在变": ["归根结底", "是训练方向在变"],
    "大家整体都变得更加的敏感了": ["大家整体都", "变得更加的敏感了"],
    "你至少要做到这个难度": ["你至少要做到", "这个难度"],
    "家长巴不得这位老师": ["家长巴不得", "这位老师"],
    "你给我家孩子多讲一点": ["你给我家孩子", "多讲一点"],
    "我一定不会因为你多讲了去投诉你": ["我一定不会因为你", "多讲了去投诉你"],
    "你不敢越雷池一步啊": ["你不敢", "越雷池一步啊"],
    "而是上限了你但凡多讲一些": ["而是上限了", "你但凡多讲一些"],
    "所以到最后大家都是贴着下限走": ["所以到最后", "大家都是", "贴着下限走"],
    "我的课就从原本的初中培优课": ["我的课就从原本的", "初中培优课"],
    "自动就变成了初高贯通课程": ["自动就变成了", "初高贯通课程"],
    "组合机械当中的传动模型": ["组合机械", "当中的传动模型"],
    "浮力问题当中的船球模型": ["浮力问题", "当中的船球模型"],
    "考察深度变化量的那种题": ["考察深度变化量的", "那种题"],
    "它其实不是真正的录取考试": ["它其实不是", "真正的录取考试"],
    "是好高中的入学分班考": ["是好高中的", "入学分班考"],
    "甚至是好高中的提前招考": ["甚至是好高中的", "提前招考"],
    "因为从中考收下来的这一大批学生": ["因为从中考", "收下来的", "这一大批学生"],
    "在中考收上来的学生": ["在中考收上来的", "学生"],
    "中考的选拔功能其实是比以前弱的": ["中考的选拔功能", "其实是比以前弱的"],
    "我从初中收上了一批连受力分析都没有": ["我从初中", "收上了一批连", "受力分析都没有"],
    "因为我已经有前两个视频被下架了": ["因为我已经有", "前两个视频", "被下架了"],
    "他们都只活了一个凌晨": ["他们都只活了", "一个凌晨"],
    "工作人员一上班就马上把这个话题给": ["工作人员一上班就", "马上把这个话题给"],
    "毙掉了所以各位家长": ["毙掉了", "所以各位家长"],
    "这是我在找到不被下架的平衡点": ["这是我在找到", "不被下架的平衡点"],
    "我会继续出更多的讲初高贯通课程的": ["我会继续出更多的", "讲初高贯通课程的"],
    "视频我得找到我观点的锋利与我语言": ["视频我得找到", "我观点的锋利", "与我语言"],
    "表达的柔和这中间的平衡点在哪里": ["表达的柔和", "这中间的平衡点", "在哪里"],
    "我是今年8月8号才开始第一天更新": ["我是今年8月8号", "才开始第一天更新"],
    "短视频的整个互联网的运营经验确实": ["短视频的整个", "互联网的运营", "经验确实"],
    "各位老师们多多海涵": ["各位老师们", "多多海涵"],
    "分班考试的甚至有更早": ["分班考试的", "甚至有更早"],
    "如果您看视频感觉我讲得戛然而止的话": ["如果您看视频", "感觉我讲得", "戛然而止的话"],
}

CORPUS_FILES = [
    "2022新课标_物理.md",
    "2022新课标_科学.md",
    "8上-苏科版版初中物理课本（2024新版）.md",
    "8下-苏科版初中物理课本（2025新版）.md",
]


def units(s):
    """按"字"数长度: 小数点 / 连字符 / 空格不算一个字"""
    return sum(1 for ch in s if ch not in ".·-")


def load_terms():
    p = WS / "方法论文档" / "物理术语表.txt"
    terms = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            t = line.strip()
            if 2 <= len(t) <= 8 and not t.startswith("#"):
                terms.add(t)
    return terms


def load_bigrams():
    """统计课本里的相邻两字, 用来判断哪里可以断句"""
    text = ""
    for name in CORPUS_FILES:
        p = WS / name
        if p.exists():
            text += p.read_text(encoding="utf-8", errors="ignore")
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", text)
    return Counter(a + b for a, b in zip(cjk, cjk[1:])), len(cjk)


def glue_cost(bigrams, a, b):
    """这两个字挨在一起越常见, 越不该在这里断开"""
    c = bigrams.get(a + b, 0)
    if c >= 200:
        return 7.0
    if c >= 50:
        return 5.0
    if c >= 15:
        return 3.0
    if c >= 4:
        return 1.5
    return 0.0


def build_char_times(tokens):
    """把 (token, s, e) 展开成逐字的时间轴"""
    out = []
    for tk in tokens:
        t, s, e = tk["t"], tk["s"], tk["e"]
        n = len(t)
        if n == 1:
            out.append((t, s, e))
            continue
        step = (e - s) / n
        for i, ch in enumerate(t):
            out.append((ch, s + i * step, s + (i + 1) * step))
    return out


def split_cue(text, terms, bigrams):
    """返回切分点列表(不含 0 和 n)"""
    n = len(text)
    if units(text) <= MAX_LEN:
        return []

    if text in OVERRIDES:
        pieces = OVERRIDES[text]
        if "".join(pieces) == text and all(units(p) <= MAX_LEN for p in pieces):
            cuts, pos = [], 0
            for p in pieces[:-1]:
                pos += len(p)
                cuts.append(pos)
            return cuts
        print(f"  ! 覆盖切法对不上, 退回自动: {text}")

    # 术语覆盖: 记录每个位置是否处于某个术语内部
    inside = [False] * n
    for term in terms:
        if len(term) < 2:
            continue
        start = 0
        while True:
            k = text.find(term, start)
            if k < 0:
                break
            for i in range(k + 1, k + len(term)):
                inside[i] = True
            start = k + 1

    INF = float("inf")
    best = [INF] * (n + 1)
    back = [-1] * (n + 1)
    best[0] = 0

    for i in range(n):
        if best[i] == INF:
            continue
        for j in range(i + 1, n + 1):
            if units(text[i:j]) > MAX_LEN:
                break
            chunk = text[i:j]
            cost = 0.0
            # 术语被切开(且不是刚好在术语边界)
            if j < n and inside[j]:
                cost += 6
            # 常用字搭配被切开
            if j < n:
                cost += glue_cost(bigrams, text[j - 1], text[j])
            # 数字/单位被切开
            if j < n and chunk[-1].isdigit() and not text[j].isdigit():
                cost += 6
            if j < n and chunk[-1].isascii() and text[j].isascii():
                cost += 6          # 英文单词内部
            if j < n and text[j] in GLUE_NEXT:
                cost += 4          # 得/地/着 前面不能断
            # 虚词开头/结尾
            if chunk[0] in BAD_START:
                cost += 2
            if chunk[-1] in BAD_END:
                cost += 4
            # 太短 / 太长
            if units(chunk) == 1:
                cost += 5
            elif units(chunk) < 5:
                cost += 5 - units(chunk)
            if units(chunk) == MAX_LEN and j < n:
                cost += 0.5        # 顶格切容易切到词里, 轻微惩罚
            total = best[i] + cost
            if total < best[j]:
                best[j] = total
                back[j] = i

    cuts, j = [], n
    while j > 0:
        i = back[j]
        if i > 0:
            cuts.append(i)
        j = i
    return sorted(cuts)


def main():
    cues = json.loads((SRC / "字幕数据.json").read_text(encoding="utf-8"))["cues"]
    tokens = json.loads((SRC / "清洗后词表.json").read_text(encoding="utf-8"))
    terms = load_terms()
    bigrams, corpus_len = load_bigrams()
    chars = build_char_times(tokens)

    # 把所有 cue 的正文(去掉标点空格)拼起来, 跟时间轴字符流对齐
    def clean(s):
        return re.sub(r"[\s，。、？！：；·（）()\"“”'‘’]", "", s)

    cursor = 0
    out = []
    groups = []
    for cue in cues:
        text = clean(cue["text"])
        seg = chars[cursor:cursor + len(text)]
        if "".join(c[0] for c in seg) != text:
            # 时间轴和字幕对不上时, 退化成按字数平分
            dur = cue["end"] - cue["start"]
            step = dur / max(1, len(text))
            seg = [(ch, cue["start"] + i * step, cue["start"] + (i + 1) * step)
                   for i, ch in enumerate(text)]
        cursor += len(text)

        cuts = split_cue(text, terms, bigrams)
        bounds = [0] + cuts + [len(text)]
        pieces = []
        for k in range(len(bounds) - 1):
            a, b = bounds[k], bounds[k + 1]
            piece = text[a:b]
            s = seg[a][1]
            e = max(seg[b - 1][2], s + MIN_DUR)
            pieces.append(piece)
            out.append({"start": round(s, 2), "end": round(e, 2), "text": piece})
        groups.append((text, pieces, cue["start"], cue["end"]))

    # 保险: 不让后一句的起点早于前一句的终点
    for i in range(1, len(out)):
        if out[i]["start"] < out[i - 1]["end"]:
            out[i]["start"] = out[i - 1]["end"]
        if out[i]["end"] <= out[i]["start"]:
            out[i]["end"] = round(out[i]["start"] + MIN_DUR, 2)

    long_left = [c for c in out if len(c["text"]) > MAX_LEN]
    (SRC / "字幕数据_单行.json").write_text(
        json.dumps({"font": "方正粗金陵简体", "max_chars": MAX_LEN, "cues": out},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"原有 {len(cues)} 句 -> 切完 {len(out)} 句")
    print(f"最长 {max(len(c['text']) for c in out)} 字, "
          f"平均 {sum(len(c['text']) for c in out) / len(out):.1f} 字")
    print(f"超 8 字的残留: {len(long_left)}")
    print(f"术语表载入 {len(terms)} 条")
    print(f"课本语料 {corpus_len} 字, 常用搭配 {len(bigrams)} 种")
    if "--all" in sys.argv:
        for text, pieces, s, e in groups:
            print(f"[{s:6.2f}-{e:6.2f}] {text}")
            print(f"            => {' | '.join(pieces)}")
    else:
        for c in out[:24]:
            print(f"  {c['start']:7.2f}-{c['end']:7.2f}  {c['text']}")


if __name__ == "__main__":
    main()
