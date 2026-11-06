# -*- coding: utf-8 -*-
"""
读字体文件的 name 表, 打印字体名 / 族名(含中文) / PostScript 名。
只用标准库, 不依赖 fontTools。

用法: python tools\font_info.py <字体文件> [更多文件...]
"""
import struct
import sys
from pathlib import Path

NAME_IDS = {
    1: "族名(Family)",
    2: "子族(Subfamily)",
    3: "唯一标识",
    4: "全名(Full)",
    6: "PostScript名",
    16: "排版族名(Typographic Family)",
    17: "排版子族",
}


def parse(path):
    data = Path(path).read_bytes()
    tag, num_tables = struct.unpack(">4sH", data[:6])
    if tag == b"ttcf":
        raise SystemExit(f"{path}: 这是 TrueType 集合(ttc), 暂不支持")

    tables = {}
    off = 12
    for _ in range(num_tables):
        t, _cs, o, l = struct.unpack(">4sIII", data[off:off + 16])
        tables[t] = (o, l)
        off += 16

    # 字形数
    glyphs = None
    if b"maxp" in tables:
        o, _ = tables[b"maxp"]
        glyphs = struct.unpack(">H", data[o + 4:o + 6])[0]

    # 每 em 单位数
    upem = None
    if b"head" in tables:
        o, _ = tables[b"head"]
        upem = struct.unpack(">H", data[o + 18:o + 20])[0]

    o, _l = tables[b"name"]
    fmt, count, string_off = struct.unpack(">HHH", data[o:o + 6])
    if fmt not in (0, 1):
        print(f"  (name 表格式 {fmt}, 只按 0/1 解析)")
    records = []
    base = o + 6
    for i in range(count):
        rec = data[base + i * 12: base + (i + 1) * 12]
        pid, eid, lid, nid, length, offset = struct.unpack(">6H", rec)
        start = o + string_off + offset
        raw = data[start:start + length]
        if pid == 3 and eid in (1, 10):          # Windows, UCS-2 / UTF-16BE
            text = raw.decode("utf-16-be", "replace")
        elif pid == 3 and eid == 0:              # Windows, symbol
            text = raw.decode("utf-16-be", "replace")
        elif pid == 1 and eid == 0:              # Mac Roman
            text = raw.decode("mac-roman", "replace")
        else:
            continue
        records.append((pid, lid, nid, text.strip()))

    print(f"\n== {Path(path).name} ==")
    print(f"  字形数 {glyphs}   每 em {upem}")
    seen = set()
    for pid, lid, nid, text in records:
        if nid not in NAME_IDS or not text:
            continue
        if (nid, text) in seen:
            continue
        seen.add((nid, text))
        lang = {0x409: "en", 0x804: "zh-CN", 0x404: "zh-TW", 0: "mac"}.get(
            lid, hex(lid))
        print(f"  {NAME_IDS[nid]:<32} [{lang}] {text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for p in sys.argv[1:]:
        parse(p)
