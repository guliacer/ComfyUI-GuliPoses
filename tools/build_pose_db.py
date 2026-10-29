"""从 POSE-DB-01 源库生成节点用的姿态索引 poses/index.json。

用法：
    python tools/build_pose_db.py                 # 使用默认源路径
    python tools/build_pose_db.py <源库目录>       # 指定 pose-db-01 目录

分类与姿势名会按 data/zh-dict.csv 译成中文（该表来自 anhao/ai-pose-gallery-zh）。
对照表缺失时自动退回日文原文，并在结尾报告未命中的条目数。

原图需放在 poses/img（本脚本只生成索引，不动图片）。缩略图不用准备：
poses/thumbs 缺失时节点会在首次请求时用原图现生成。原图推荐先用
tools/optimize_library.py 转成 WebP，体积能降到 1/3.4。
"""

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

NODE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = NODE_DIR / "poses"
IMG_DIR = DB_DIR / "img"
INDEX_FILE = DB_DIR / "index.json"
ZH_DICT = NODE_DIR / "data" / "zh-dict.csv"

# 原图可能是 PNG，也可能已经被 tools/optimize_library.py 转成 WebP。
# 索引里要写实际存在的那个名字，否则前端拿到 404。
IMG_EXTS = (".webp", ".png", ".jpg", ".jpeg")


def resolve_img(name: str) -> str:
    """按实际落盘的文件名返回（优先 WebP）。找不到就原样返回，让缺图由 resolve() 去兜。"""
    path = Path(str(name or "")).name
    if not path:
        return path
    if (IMG_DIR / path).is_file():
        return path
    stem = Path(path).stem
    for ext in IMG_EXTS:
        if (IMG_DIR / f"{stem}{ext}").is_file():
            return f"{stem}{ext}"
    return path

DEFAULT_SRC = Path(
    r"C:\Users\Admin\Desktop\PS高速缓存\1439个白模姿态参考图📢\1400个白模姿态图\pose-db-01"
)

ANGLES = [
    ("front", "正面"),
    ("high", "俯视"),
    ("low", "仰视"),
    ("side", "侧面"),
    ("diag", "斜侧"),
]
ANGLE_LABEL = dict(ANGLES)

# 下拉框里用的短名，太长会把节点撑宽
SERIES_SHORT = {
    "full_sexy": "性感全身",
    "full_single": "标准全身",
    "pair60": "双人",
    "upper80v2": "上半身",
}

POSE_RE = re.compile(r"^(?P<series>.+)_P(?P<code>\d+)$")


def series_key(pose_no: str) -> str:
    head = pose_no.rsplit("_", 1)[0] if pose_no.rsplit("_", 1)[-1] in ANGLE_LABEL else pose_no
    m = POSE_RE.match(head)
    return m.group("series") if m else head


def load_zh_dict(path: Path = ZH_DICT) -> dict:
    """日→中对照表。键为 (字段, 日文原文)，字段取值：分類 / ポーズ名 / 角度 / 系統。"""
    if not path.is_file():
        return {}
    rows = csv.DictReader(path.open(encoding="utf-8-sig"))
    return {(r["字段"], r["日文原文"].strip()): r["中文译文"].strip() for r in rows}


def build(src: Path) -> dict:
    csv_file = src / "data" / "poses.csv"
    if not csv_file.is_file():
        raise SystemExit(f"找不到元数据：{csv_file}")

    rows = list(csv.DictReader(csv_file.open(encoding="utf-8-sig")))
    zh = load_zh_dict()

    poses: dict[str, dict] = {}
    series_meta: dict[str, dict] = {}
    missing: set[tuple[str, str]] = set()

    def tr(field: str, text: str) -> str:
        hit = zh.get((field, text))
        if hit is None:
            missing.add((field, text))
            return text
        return hit

    for row in rows:
        pid = row["ID"].strip()
        angle = pid.rsplit("_", 1)[-1]
        if angle not in ANGLE_LABEL:
            continue
        pose_no = pid[: -(len(angle) + 1)]
        m = POSE_RE.match(pose_no)
        if not m:
            continue
        skey = m.group("series")
        code = m.group("code")

        rec = poses.get(pose_no)
        if rec is None:
            cat_jp = row["分类"].strip()
            name_jp = row["姿势名称(日文)"].strip()
            rec = poses[pose_no] = {
                "no": pose_no,
                "series": skey,
                "code": f"P{code}",
                "cat": tr("分類", cat_jp),
                "catJp": cat_jp,
                "name": tr("ポーズ名", name_jp),
                "nameJp": name_jp,
                "angles": {},
            }
            short = SERIES_SHORT.get(skey, skey)
            rec["label"] = f"{short} {rec['code']} · {rec['name']}"
            meta = series_meta.setdefault(
                skey,
                {
                    "key": skey,
                    "name": row["系列"].strip(),
                    "nameJp": row["系列(日文)"].strip(),
                    "short": short,
                    "count": 0,
                },
            )
            meta["count"] += 1

        img = resolve_img(row["原图"])
        thumb = Path(row["缩略图"]).name
        rec["angles"][angle] = {"img": img, "thumb": thumb}

    ordered = sorted(poses.values(), key=lambda p: (p["series"], p["code"]))

    labels: dict[str, int] = {}
    for rec in ordered:
        labels[rec["label"]] = labels.get(rec["label"], 0) + 1
    for rec in ordered:
        if labels[rec["label"]] > 1:
            rec["label"] = f"{rec['series']} {rec['label']}"

    total_images = sum(len(p["angles"]) for p in ordered)
    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(src),
        "poseCount": len(ordered),
        "imageCount": total_images,
        "zhDict": ZH_DICT.name if zh else None,
        "zhMissing": sorted(f"{field}:{text}" for field, text in missing),
        "angles": [{"key": k, "label": v} for k, v in ANGLES],
        "series": sorted(series_meta.values(), key=lambda s: -s["count"]),
        "poses": ordered,
    }


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    index = build(src)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"已写入 {INDEX_FILE}")
    print(f"姿态 {index['poseCount']} 个 / 图片 {index['imageCount']} 张")
    if index["zhDict"]:
        print(f"已套用中文对照表 {index['zhDict']}，未命中 {len(index['zhMissing'])} 条")
        for item in index["zhMissing"][:10]:
            print(f"  未翻译：{item}")
    else:
        print("未找到 data/zh-dict.csv，分类与姿势名保留日文原文")
    for s in index["series"]:
        print(f"  {s['key']:<12} {s['name']:<10} {s['count']:>3} 个姿态")


if __name__ == "__main__":
    main()
