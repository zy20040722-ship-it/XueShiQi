# -*- coding: utf-8 -*-
"""只做清洗和合词, 把正文导出来(供人工加标点用)"""
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("bs", Path(__file__).parent / "build_subtitles.py")
bs = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], ".", "."]          # 避免它读参数
spec.loader.exec_module(bs)

DIR = Path(sys.argv[0] and sys.argv[0])  # noqa
src = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线\分析\粗剪校验_v2\粗剪_v2")
out = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线\精剪")
out.mkdir(parents=True, exist_ok=True)

t = json.loads((src / "transcript.json").read_text(encoding="utf-8"))
toks = bs.merge_tokens(t["words"])
print(f"合词后 {len(toks)} 个词")
toks = bs.apply_fixes(toks, bs.load_global_fixes() + bs.LOCAL_FIXES)
text = "".join(x["t"] for x in toks)
(out / "清洗后正文.txt").write_text(text, encoding="utf-8")
(out / "清洗后词表.json").write_text(
    json.dumps([{"t": x["t"], "s": round(x["s"], 3), "e": round(x["e"], 3)} for x in toks],
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"正文 {len(text)} 字, 已写出 清洗后正文.txt")
print()
print(text)
