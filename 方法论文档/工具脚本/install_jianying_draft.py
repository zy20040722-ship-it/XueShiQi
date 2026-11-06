# -*- coding: utf-8 -*-
r"""
把生成的剪映草稿装进剪映的草稿目录, 并把 meta 里的路径改成本机实际路径。
用法: python tools\install_jianying_draft.py

同名草稿已存在时不会覆盖, 而是备份成 <名字>_backup_<时间>。
"""
import json
import os
import shutil
import time
from pathlib import Path

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
SRC = WS / "工程-9.25导演剪辑版" / "剪映草稿" / "初高断层-精剪"
DRAFT_ROOT = (Path(os.environ["LOCALAPPDATA"]) / "JianyingPro" / "User Data"
              / "Projects" / "com.lveditor.draft")
DST = DRAFT_ROOT / SRC.name


def main():
    if not SRC.exists():
        raise SystemExit(f"源草稿不存在: {SRC}\n先跑 tools\\export_project.py")
    DRAFT_ROOT.mkdir(parents=True, exist_ok=True)

    if DST.exists():
        bak = DST.with_name(f"{DST.name}_backup_{time.strftime('%Y%m%d_%H%M%S')}")
        DST.rename(bak)
        print("同名草稿已存在, 先备份成:", bak.name)

    shutil.copytree(SRC, DST)

    meta_p = DST / "draft_meta_info.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta["draft_fold_path"] = str(DST).replace("\\", "/")
    meta["draft_root_path"] = str(DRAFT_ROOT).replace("\\", "/")
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("草稿已装好 ->", DST)
    for f in sorted(DST.iterdir()):
        print(f"    {f.name}  {f.stat().st_size / 1024:.1f} KB")
    print("\n打开剪映专业版, 首页「本地草稿」里应该能看到「初高断层-精剪」。")


if __name__ == "__main__":
    main()
