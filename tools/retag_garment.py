"""把 garment/index.json 的分类从「季节」重排成「穿搭类型」。

只动 series / cat / catJp / label / season 五个字段，图片一个不碰、编号 no 不变、
数量也不变。规则在 tools/garment_classify.py，改完规则直接重跑本脚本即可。

用法：
    python tools/retag_garment.py              # 预演，只打印将要发生的变化
    python tools/retag_garment.py --apply      # 落盘（先备份到 .workbuddy-ai/backup-<日期>/）

label 会从「春 SPR-0001」变成「半身裙·迷你 SPR-0001」，旧工作流里已选中的服装名
不用重选：后端 find_pose() 会拿 labelOld 和编号兜底，前端打开时也就地换成新名。
原 label 存进 labelOld 字段备查。
"""

import json
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import garment_classify as gc  # noqa: E402

NODE_DIR = Path(__file__).resolve().parents[1]
INDEX_FILE = NODE_DIR / "garment" / "index.json"
BACKUP_DIR = NODE_DIR / ".workbuddy-ai" / f"backup-{datetime.now():%Y%m%d}"


def retag(poses: list[dict]) -> tuple[list[dict], list[tuple[str, str, str]]]:
    """返回 (新 poses, 变化清单[(code, 旧cat, 新cat)])。原地改副本，不动入参。"""
    changes = []
    out = []
    for src in poses:
        p = dict(src)
        old_cat = p.get("cat", "")
        key, name, cat = gc.classify(p.get("code", ""), p.get("keywords", ""))
        p["series"] = key
        p["cat"] = cat
        p["catJp"] = cat
        p["season"] = gc.season_of(p.get("code", ""))
        new_label = f"{cat} {p['code']}"
        if p.get("label") != new_label:
            p.setdefault("labelOld", p.get("label", ""))
            p["label"] = new_label
        if old_cat != cat:
            changes.append((p["code"], old_cat, cat))
        out.append(p)
    return out, changes


def main() -> None:
    apply = "--apply" in sys.argv
    if not INDEX_FILE.is_file():
        raise SystemExit(f"找不到索引：{INDEX_FILE}")
    data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    poses = data.get("poses") or []
    if not poses:
        raise SystemExit("索引里没有条目，先跑 build_garment_db.py")

    old_series = {s["key"]: s.get("name", s["key"]) for s in data.get("series", [])}
    new_poses, changes = retag(poses)
    new_series = gc.series_counts(new_poses)

    print(f"条目 {len(poses)} 套，分类有变化 {len(changes)} 套")
    print("\n一级类型：")
    old_counter = Counter(p.get("series", "") for p in poses)
    for s in new_series:
        old_key, old_name = next(
            ((k, v) for k, v in old_series.items() if v == s["name"]), (None, None)
        )
        old_n = old_counter.get(old_key, 0) if old_key else 0
        print(f"  {s['name']:<6} {s['count']:>5} 套" + (f"   （原 {old_name} {old_n} 套）" if old_key else ""))
    print(f"  合计   {sum(s['count'] for s in new_series):>5} 套")

    print("\n二级分类：")
    for (key, cat), n in gc.cat_counts(new_poses):
        print(f"  {gc.SERIES_NAME[key]:<6} / {cat:<8} {n:>5}")

    # 自检：数量、类型合法性、series 计数一致
    assert len(new_poses) == len(poses), "条目数变了"
    bad = [p["code"] for p in new_poses if p["series"] not in gc.SERIES_NAME]
    assert not bad, f"出现未知系列：{bad[:5]}"
    assert sum(s["count"] for s in new_series) == len(new_poses), "series 计数与条目数不一致"
    assert all(p["cat"].split("·")[0] in gc.SERIES_NAME[p["series"]] or p["series"] == "swimwear" for p in new_poses), "分类名与系列不匹配"

    if not apply:
        print("\n（预演，未写入。加 --apply 落盘）")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"garment-index.{datetime.now():%H%M%S}.preretag.json"
    backup.write_text(INDEX_FILE.read_text(encoding="utf-8"), encoding="utf-8")

    data["poses"] = new_poses
    data["series"] = new_series
    data["poseCount"] = len(new_poses)
    data["imageCount"] = sum(len(p.get("angles") or {}) for p in new_poses)
    data["generated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["categories"] = "retagged by type (see tools/garment_classify.py)"
    if "imgSig" in data:
        del data["imgSig"]  # 手工索引不参与自动重建，留着反而误导

    tmp = INDEX_FILE.with_name(f"{INDEX_FILE.name}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(INDEX_FILE)
    print(f"\n已写入 {INDEX_FILE}")
    print(f"改前备份 {backup}")


if __name__ == "__main__":
    main()
