# -*- coding: utf-8 -*-
"""
把字幕数据导出成两种可编辑格式:
  1. 字幕.srt     所有剪辑软件都认, 导入即成可编辑文字轨(最稳)
  2. 剪映草稿/    剪映专业版工程(结构按公开规格生成)

注: 2026-09-28 用户放弃达芬奇, 原来那份 工程.fcpxml 的导出代码已删除。
"""
import json
import shutil
import time
import uuid
from pathlib import Path

WS = Path(r"D:\Users\15241\Desktop\薛世奇视频剪辑流水线")
SRC = WS / "精剪"                      # 字幕中间数据, 2026-09-29 起保持原位(脚本依赖)
OUT = WS / "工程-9.25导演剪辑版"        # 剪映草稿/可编辑工程, 2026-09-29 起搬到这里
OUT.mkdir(parents=True, exist_ok=True)

VIDEO = WS / "分析" / "IMG_3922" / "粗剪_v2.mp4"      # 无字幕的干净底片
DIAG1 = WS / "精剪" / "图示" / "斜面受力分析.png"
DIAG2 = WS / "精剪" / "图示" / "船球模型.png"
DIAG3 = WS / "精剪" / "图示" / "传送带受力分析.png"
DIAG4 = WS / "精剪" / "图示" / "传动模型.png"

DATA = json.loads((SRC / "字幕数据.json").read_text(encoding="utf-8"))
CUES = DATA["cues"]
DUR_FRAMES = 12705                    # 60fps 实际帧数; 时间一律按帧对齐, 免得达芬奇挑刺
DUR = round(DUR_FRAMES / 60, 6)

# SOP 指定的字体(见 字体\ 目录):
#   字幕 金陵体   -> 方正粗金陵简体      FZJinLS-B-GB.ttf
#   标题 丽金黑   -> 华康俪金黑W8(P)     DFPLiJinHeiW8-GB.TTF
FONT_SUB = "方正粗金陵简体"
FONT_TITLE = "华康俪金黑W8(P)"

# 顶部主标题(SOP 步骤 6.2), 两行白字, 全程挂着
MAIN_TITLE = ["以前正常学的知识", "为什么现在成了超纲"]

# SOP 6.3 的三条分论点副标题(文案取自参考片, 时间对到本片时间轴)
SUBTITLE_LINES = [
    ("近20年学生能力反而下降？", 0.00, 45.50),
    ("课标从下限变成了上限", 45.50, 80.30),
    ("初中培优课变成了初高贯通课", 80.30, 149.70),
]

# 四张图示连着出现: 斜面 -> 传送带 -> 传动模型 -> 船球
DIAG = [("d1", 87.0, 89.5), ("d3", 89.6, 92.0), ("d4", 92.1, 94.8), ("d2", 94.9, 98.2)]


def srt_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def export_srt():
    lines = []
    for i, c in enumerate(CUES, 1):
        lines += [str(i), f"{srt_time(c['start'])} --> {srt_time(c['end'])}", c["text"], ""]
    (OUT / "字幕.srt").write_text("\n".join(lines), encoding="utf-8")
    print(f"  字幕.srt  ({len(CUES)} 句)")


def export_jianying():
    """剪映专业版草稿(11.x)。

    字段按公开规格 + 剪映自带 AI 模块里出现的草稿文件名(draft_content.json /
    draft_meta_info.json)对齐; 位置用剪映那套 transform.y(1.0 ≈ 半个画面高)。
    本机剪映 11.5.3.14501, 结构仍属手写, 若打不开就照真草稿对齐。
    """
    root = OUT / "剪映草稿" / "初高断层-精剪"
    root.mkdir(parents=True, exist_ok=True)
    US = 1_000_000  # 微秒
    total = int(DUR * US)
    now = int(time.time() * US)
    mid = uuid.uuid4().hex.upper()
    platform = {
        "app_id": 3704, "app_source": "lv", "app_version": "11.5.3",
        "device_id": uuid.uuid4().hex, "os": "windows", "os_version": "10",
    }

    def seg_y(px):
        """画面像素偏移 -> 剪映 transform.y (1.0 = 半个画面高 960px)"""
        return round(px / 960.0, 4)

    def make_seg(material_id, a, b, y):
        dur = int((b - a) * US)
        return {
            "id": uuid.uuid4().hex.upper(), "material_id": material_id,
            "target_timerange": {"start": int(a * US), "duration": dur},
            "source_timerange": {"start": 0, "duration": dur},
            "speed": 1.0, "volume": 1.0, "visible": True,
            "clip": {"scale": {"x": 1.0, "y": 1.0},
                     "transform": {"x": 0.0, "y": y},
                     "flip": {"horizontal": False, "vertical": False}, "rotation": 0.0},
            "extra_material_refs": [], "group_id": "", "render_index": 0,
            "template_id": "", "reverse": False, "is_placeholder": False,
        }

    # 视频素材
    vid_id = uuid.uuid4().hex.upper()
    videos = [{
        "id": vid_id, "type": "video", "path": str(VIDEO), "material_name": "口播正片",
        "duration": total, "width": 1080, "height": 1920,
        "has_audio": True, "reverse_path": "", "crop": {
            "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0},
    }]

    # 图示素材(四张 PNG)
    photos, photo_segs = [], []
    for a, b, p in ((87.0, 89.5, DIAG1), (89.6, 92.0, DIAG3),
                    (92.1, 94.8, DIAG4), (94.9, 98.2, DIAG2)):
        pid = uuid.uuid4().hex.upper()
        photos.append({"id": pid, "type": "photo", "path": str(p),
                       "material_name": p.stem, "width": 900, "height": 360})
        photo_segs.append(make_seg(pid, a, b, seg_y(340)))

    # 文字素材
    texts = []

    def text_material(s, font, size, color="#FFFFFF"):
        tid = uuid.uuid4().hex.upper()
        texts.append({
            "id": tid, "type": "text",
            "content": json.dumps({"text": s}, ensure_ascii=False),
            "font_name": font, "font_size": size, "text_color": color,
            "text_alpha": 1.0, "border_color": "#000000", "border_width": 0.08,
            "border_alpha": 1.0, "background_color": "", "background_style": 0,
            "background_alpha": 1.0, "alignment": 1, "letter_spacing": 0.0,
            "line_spacing": 0.02, "bold": False, "italic": False, "underline": False,
            "typesetting": 0, "base_content": "", "style_name": "",
        })
        return tid

    # 主标题: 全程挂在画面上方(y=+0.677 ≈ 画面 310px 处)
    main_tid = text_material("\n".join(MAIN_TITLE), FONT_TITLE, 12.0)
    main_segs = [make_seg(main_tid, 0.0, DUR, seg_y(650))]
    # 副标题: 3 条挂屏
    sub_segs = []
    for text, a, b in SUBTITLE_LINES:
        sub_segs.append(make_seg(text_material(text, FONT_TITLE, 9.0, "#FFA01E"),
                                 a, b, seg_y(495)))
    # 正文: 166 条单行, 位置在画面 74%(y≈1428)
    cue_segs = [make_seg(text_material(c["text"], FONT_SUB, 8.0), c["start"], c["end"],
                         seg_y(-468))
                for c in CUES]

    draft = {
        "canvas_config": {"height": 1920, "ratio": "original", "width": 1080},
        "color_space": 0,
        "config": {"adjust_max_index": 1, "export_color_space": 0,
                   "material_save_mode": 0},
        "cover": None,
        "create_time": now,
        "duration": total, "fps": 60.0, "id": mid,
        "extra_info": None,
        "free_render_index_mode_on": False,
        "keyframe_graph_list": [],
        "keyframes": {"adjusts": [], "audios": [], "effects": [], "filters": [],
                      "handwrites": [], "stickers": [], "texts": [], "videos": []},
        "last_modified_platform": platform,
        "materials": {
            "videos": videos, "photos": photos, "audios": [], "texts": texts,
            "stickers": [], "images": [],
            "canvases": [{"id": uuid.uuid4().hex.upper(), "type": "canvas",
                          "width": 1080, "height": 1920, "ratio": "original"}],
            "speeds": [], "sound_channel_mappings": [], "beats": [], "vocal_separations": [],
        },
        "mutable_config": None,
        "name": "",
        "new_version": "110.0.0",
        "platform": platform,
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": [
            {"id": uuid.uuid4().hex.upper(), "type": "video", "attribute": 0,
             "flag": 0, "is_default_name": True, "name": "",
             "segments": [make_seg(vid_id, 0.0, DUR, 0.0)]},
            {"id": uuid.uuid4().hex.upper(), "type": "video", "attribute": 0,
             "flag": 0, "is_default_name": True, "name": "",
             "segments": photo_segs},
            {"id": uuid.uuid4().hex.upper(), "type": "text", "attribute": 0,
             "flag": 0, "is_default_name": True, "name": "",
             "segments": main_segs},
            {"id": uuid.uuid4().hex.upper(), "type": "text", "attribute": 0,
             "flag": 0, "is_default_name": True, "name": "",
             "segments": sub_segs},
            {"id": uuid.uuid4().hex.upper(), "type": "text", "attribute": 0,
             "flag": 0, "is_default_name": True, "name": "",
             "segments": cue_segs},
        ],
        "update_time": now,
        "version": 360000,
    }
    (root / "draft_content.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "draft_fold_path": str(root).replace("\\", "/"),
        "draft_name": "初高断层-精剪",
        "draft_root_path": str(OUT / "剪映草稿").replace("\\", "/"),
        "draft_id": mid,
        "draft_json_file": "draft_content.json",
        "draft_new_version": "110.0.0",
        "draft_timeline_materials_size_": 0,
        "tm_draft_create": now, "tm_draft_modified": now, "tm_duration": 0,
        "draft_removable_storage_device": "",
        "draft_cover": "",
        "draft_type": "",
    }
    (root / "draft_meta_info.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  剪映草稿/  (底片 + 4 图示 + 主标题 + {len(SUBTITLE_LINES)} 副标题 + {len(CUES)} 字幕)")


print("导出可编辑工程 ->", OUT)
export_srt()
export_jianying()

# 把图示素材也拷过去, 方便手动摆放
dst = OUT / "图示素材"
dst.mkdir(exist_ok=True)
for f in (DIAG1, DIAG2, DIAG3, DIAG4):
    if f.exists():
        shutil.copy2(f, dst / f.name)
shutil.copy2(SRC / "成片字幕.ass", OUT / "字幕.ass")
print(f"  图示素材/ + 字幕.ass")
print("完成")
