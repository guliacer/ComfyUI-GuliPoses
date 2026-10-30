"""从服装源库生成 garment/index.json 并把原图复制到 garment/img。

源库布局（实测）：
  <src>/01_spring/SPR-0001.webp ...        图片按系列分目录，每套单张 WebP
  <src>/原始数据.json                      list，每项 {id, カテゴリ(系列中文名), キーワード, ...}
  <src>/关键词表.csv                       字段：编号, 分类(=系列目录名), 英文关键词, 文件名

服装只有单一角度，故 angles 退化为 {front}，与姿态库「不生效不展示」原则一致。

**分类不按源库的季节目录走**：季节分 tab 找图很别扭（找一条百褶裙要翻四个季节），
改为按穿搭类型分，规则在 tools/garment_classify.py（连衣裙 / 半身裙 / 裤装 / 上装 /
内衣·家居 / 泳装，二级再分迷你 / 中长 / 百褶 / 牛仔…）。源库的季节目录只用来取图，
它的中文名记进 season 字段，画廊搜索「春」仍能翻到那一批。

用法：
    python tools/build_garment_db.py                 # 使用内置默认源路径
    python tools/build_garment_db.py <源库目录>       # 指定源库
"""

import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import garment_classify as gc  # noqa: E402

NODE_DIR = Path(__file__).resolve().parents[1]
GARMENT_DIR = NODE_DIR / "garment"
IMG_DIR = GARMENT_DIR / "img"
INDEX_FILE = GARMENT_DIR / "index.json"

DEFAULT_SRC = Path(r"C:\Users\Admin\Desktop\PS高速缓存\1407套服装穿搭\服装1407")

# 系列中文名：源库 JSON 的 カテゴリ 字段含日文（ランジェリー/水着…），按 AGENTS.md
# 「用户可见一律中文」强制映射；春夏秋冬虽已是中文也一并写死，避免以后源库改日文。
SERIES_CN = {
    "01_spring": "春",
    "02_summer": "夏",
    "03_autumn": "秋",
    "04_winter": "冬",
    "05_lingerie": "内衣",
    "06_party": "派对",
    "07_swimwear": "泳装",
    "08_sexy": "性感",
}


def load_meta(src: Path) -> dict:
    """原始数据.json：id -> {系列中文名, 英文关键词}。"""
    if not (src / "原始数据.json").is_file():
        return {}
    raw = json.load((src / "原始数据.json").open(encoding="utf-8"))
    out = {}
    for it in raw:
        out[it["id"]] = {
            "cat_cn": (it.get("カテゴリ") or "").strip(),
            "kw": (it.get("キーワード") or "").strip(),
        }
    return out


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.is_dir():
        raise SystemExit(f"找不到源库：{src}")
    meta = load_meta(src)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    poses: list[dict] = []
    copied = 0

    for series_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        skey = series_dir.name  # 源库的季节目录名，只用来取图 + 记 season
        imgs = sorted(series_dir.glob("*.webp"))
        if not imgs:
            continue
        season = SERIES_CN.get(skey, "")

        for img in imgs:
            pid = img.stem
            dst = IMG_DIR / img.name
            alt = IMG_DIR / f"{skey}_{img.name}"
            if dst.exists():
                # 平铺名已就位：直接复用，重跑不重复复制、也不误改名
                pass
            elif alt.exists():
                # 上轮曾因撞名改成「系列_文件名」，沿用之
                dst = alt
            else:
                shutil.copy2(img, dst)
                copied += 1
            info = meta.get(pid, {})
            kw = info.get("kw", "")
            skey_type, _sname, cat = gc.classify(pid, kw)
            poses.append(
                {
                    "no": f"{skey}_{pid}",  # 稳定 ID：沿用源库季节目录名，改分类也不动
                    "series": skey_type,
                    "code": pid,
                    "cat": cat,
                    "catJp": cat,
                    "name": pid,
                    "nameJp": pid,
                    "keywords": kw,
                    "season": season,
                    "angles": {"front": {"img": dst.name, "thumb": dst.stem + ".jpg"}},
                    "label": f"{cat} {pid}",
                }
            )

    series = gc.series_counts(poses)
    index = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(src),
        "lib": "garment",
        "poseCount": len(poses),
        "imageCount": len(poses),
        "angles": [{"key": "front", "label": "正面"}],
        "series": series,
        "poses": poses,
    }
    GARMENT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"已写入 {INDEX_FILE}")
    print(f"服装 {len(poses)} 套 / 图片 {len(poses)} 张，复制 {copied} 张")
    for s in series:
        print(f"  {s['name']:<8} {s['count']:>4} 套")
    print("二级分类：")
    for (key, cat), n in gc.cat_counts(poses):
        print(f"  {gc.SERIES_NAME[key]:<7} {cat:<10} {n:>4}")


if __name__ == "__main__":
    main()
