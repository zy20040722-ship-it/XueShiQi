# -*- coding: utf-8 -*-
"""独立版: 合并碎片词 + 纠错, 导出干净正文和词表"""
import json
from pathlib import Path

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
SRC = WS / "分析" / "粗剪校验_v2" / "粗剪_v2" / "transcript.json"
OUT = WS / "精剪"
OUT.mkdir(parents=True, exist_ok=True)

LOCAL_FIXES = [
    ("你又没有一种", "你有没有一种"),
    ("初中数学球一次函数", "初中数学求一次函数"),
    ("你给我的孩子", "你给我家孩子"),
    ("家常就可以投诉", "家长就可以投诉"),
    ("入学分班册", "入学分班考"),
    ("提前召考", "提前招考"),
    ("办分班考识的", "办分班考试的"),
    ("办分班考事的", "办分班考试的"),
    ("分班考识", "分班考试"),
    ("分班考事", "分班考试"),
    ("중考", "中考"),
    ("不被一下架", "不被下架"),
    ("视频의动力", "视频的动力"),
    ("彻底摔给高中", "彻底甩给高中"),
    ("传球模型", "船球模型"),
    ("对边比0边", "对边比邻边"),
    ("TangentTheta", "tan θ"),          # 他说的是 tan θ(2026-09-28 用户确认)
    ("Tangent Theta", "tan θ"),
    ("tangent theta", "tan θ"),
    # 下面几条原本是正则规则, 这里按字面处理
    ("课标是下线", "课标是下限"),
    ("不是下线而是上线", "不是下限而是上限"),
    ("贴着下约走", "贴着下限走"),
    ("贴着下线走", "贴着下限走"),
]

UNITS = set("年月日点个分秒倍周岁万亿")


def load_global_fixes():
    p = WS / "方法论文档" / "术语纠错表.txt"
    rules = []
    if not p.exists():
        return rules
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=>" not in line:
            continue
        left, right = [x.strip() for x in line.split("=>", 1)]
        if left.startswith("re:") or not left or not right or right == "?" or len(left) > 8:
            continue
        rules.append((left, right))
    return rules


def is_latin(s):
    return bool(s) and all((c.isascii() and (c.isalnum() or c in ".-+%")) for c in s)


words = json.loads(SRC.read_text(encoding="utf-8"))["words"]
toks = []
for w in words:
    t = w["w"].replace(" ", "").strip()
    if not t:
        continue
    if toks:
        p = toks[-1]
        if is_latin(p["t"]) and is_latin(t):
            p["t"] += t
            p["e"] = w["e"]
            continue
        if p["t"] and (p["t"][-1].isdigit() or p["t"][-1] in ".%") and t in UNITS:
            p["t"] += t
            p["e"] = w["e"]
            continue
    toks.append({"t": t, "s": w["s"], "e": w["e"]})

print(f"原始词 {len(words)} -> 合并后 {len(toks)}")

text = "".join(t["t"] for t in toks)
for old, new in load_global_fixes() + LOCAL_FIXES:
    if old in text:
        text = text.replace(old, new)
        # 同步到词表(按字符串整体替换, 位置会略偏但用于对齐足够)
        joined = "".join(t["t"] for t in toks)
        if old in joined:
            pos = 0
            a = b = None
            for i, t in enumerate(toks):
                if a is None and pos + len(t["t"]) > joined.find(old):
                    a = i
                if a is not None and pos + len(t["t"]) >= joined.find(old) + len(old):
                    b = i
                    break
                pos += len(t["t"])
            if a is not None and b is not None:
                span = toks[a:b + 1]
                t0, t1 = span[0]["s"], span[-1]["e"]
                step = (t1 - t0) / max(1, len(new))
                toks[a:b + 1] = [{"t": new[i], "s": t0 + step * i, "e": t0 + step * (i + 1)}
                                 for i in range(len(new))]

text = "".join(t["t"] for t in toks)
(OUT / "清洗后正文.txt").write_text(text, encoding="utf-8")
(OUT / "清洗后词表.json").write_text(
    json.dumps([{"t": t["t"], "s": round(t["s"], 3), "e": round(t["e"], 3)} for t in toks],
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"正文 {len(text)} 字 -> 精剪\\清洗后正文.txt")
print()
print(text)
