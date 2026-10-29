"""姿态库索引、取图范围与图片定位。

内置库的索引由 tools/build_pose_db.py 生成，结构见该脚本 docstring。
用户自己的图放进 poses/custom/：读索引时按目录签名自动补进来，缩略图也在扫描时补齐，
不需要重跑建库脚本；一个文件就是一个姿态，视角固定按「正面」处理。
"""

import json
import os
import threading
from pathlib import Path

from PIL import Image, ImageOps

NODE_DIR = Path(__file__).resolve().parent
DB_DIR = NODE_DIR / "poses"
INDEX_FILE = DB_DIR / "index.json"
IMG_DIR = DB_DIR / "img"
THUMB_DIR = DB_DIR / "thumbs"

# 用户导入的姿态图：平铺放在 custom/ 根目录，thumbs/ 与 meta.json 由插件维护，不要手改
CUSTOM_DIR = DB_DIR / "custom"
CUSTOM_THUMB_DIR = CUSTOM_DIR / "thumbs"
CUSTOM_META_FILE = CUSTOM_DIR / "meta.json"

CUSTOM_SERIES_KEY = "custom"
CUSTOM_SERIES_NAME = "我的姿态"
CUSTOM_SERIES_SHORT = "我的"
CUSTOM_CAT = "自定义"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
THUMB_SIDE = 320
ILLEGAL_CHARS = '\\/:*?"<>|'
# Windows 里不能当文件名用的保留字，撞上就加下划线
RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
)

ANGLE_LABELS = {"front": "正面", "high": "俯视", "low": "仰视", "side": "侧面", "diag": "斜侧"}
LABEL_TO_ANGLE = {label: key for key, label in ANGLE_LABELS.items()}

RANDOM_ANGLE = "随机视角"
ANGLE_CHOICES = list(ANGLE_LABELS.values()) + [RANDOM_ANGLE]

ALL = "全部"

EMPTY_HINT = "（姿态库为空：请在节点里点「导入」放自己的图）"

_index = None
_index_mtime = None

_custom_lock = threading.Lock()
_custom_sig = None
_custom_poses = []

_meta = None
_meta_mtime = None


class PoseDBMissing(RuntimeError):
    """库还没准备好（空库 / 索引缺失），或选中的姿态已经不在库里。"""


def _empty_base():
    return {
        "generated": None,
        "source": None,
        "angles": [{"key": key, "label": label} for key, label in ANGLE_LABELS.items()],
        "series": [],
        "poses": [],
    }


def _builtin():
    """内置库索引；文件缺失时按空库处理，只用自定义图也能开工。

    按 index.json 的 mtime 判断要不要重读，重跑 build_pose_db.py 后不用重启 ComfyUI。
    """
    global _index, _index_mtime
    try:
        mtime = int(INDEX_FILE.stat().st_mtime)
    except OSError:
        mtime = None
    if _index is not None and mtime == _index_mtime:
        return _index
    if mtime is None:
        _index = _empty_base()
    else:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        for key, default in _empty_base().items():
            data.setdefault(key, default)
        _index = data
    _index_mtime = mtime
    return _index


# ---------- 自定义姿态库 ----------


def _custom_files():
    """custom/ 根目录下的图片：[(文件名, 大小, 修改时间)]，按名字排序让编号稳定。"""
    try:
        with os.scandir(CUSTOM_DIR) as entries:
            found = []
            for entry in entries:
                if not entry.is_file():
                    continue
                if Path(entry.name).suffix.lower() not in IMAGE_EXTS:
                    continue
                stat = entry.stat()
                found.append((entry.name, stat.st_size, int(stat.st_mtime)))
    except OSError:  # 目录还不存在：当空库
        return []
    return sorted(found)


def _make_thumb(src: Path, dst: Path) -> None:
    """生成缩略图。透明底铺白，避免格子里出现黑块。"""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.split()[-1])
            im = flat
        else:
            im = im.convert("RGB")
        im.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=86, optimize=True)


def clean_label(raw: str, fallback: str = CUSTOM_CAT) -> str:
    """显示名 / 分类名：去控制字符、去路径符号，保留中文与空格。"""
    text = str(raw or "").strip()
    text = "".join(ch for ch in text if ord(ch) >= 32 and ch not in ILLEGAL_CHARS).strip(" .")
    return text[:60] or fallback


def _load_meta() -> dict:
    """custom/meta.json：{文件名: {name, cat, angle}}；按 mtime 缓存。"""
    global _meta, _meta_mtime
    try:
        mtime = int(CUSTOM_META_FILE.stat().st_mtime)
    except OSError:
        mtime = None
    if _meta is not None and mtime == _meta_mtime:
        return _meta
    items = {}
    if mtime is not None:
        try:
            data = json.loads(CUSTOM_META_FILE.read_text(encoding="utf-8"))
            items = data.get("items") or {}
        except Exception as err:
            print(f"[GG 姿态库] poses/custom/meta.json 读不出来，按文件名兜底：{err}")
    _meta = items
    _meta_mtime = mtime
    return _meta


def _write_meta(items: dict) -> None:
    global _meta, _meta_mtime
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_META_FILE.write_text(
        json.dumps({"version": 1, "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _meta = items
    try:
        _meta_mtime = int(CUSTOM_META_FILE.stat().st_mtime)
    except OSError:
        _meta_mtime = None


def set_meta(filename: str, name=None, cat=None, angle=None) -> None:
    """记一张图的显示名 / 分类 / 视角；只覆盖传进来的字段。"""
    items = dict(_load_meta())
    entry = dict(items.get(filename) or {})
    if name:
        entry["name"] = clean_label(name, Path(filename).stem)
    if cat:
        entry["cat"] = clean_label(cat, CUSTOM_CAT)
    if angle in ANGLE_LABELS:
        entry["angle"] = angle
    items[filename] = entry
    _write_meta(items)


def _scan_custom() -> None:
    """扫 custom/，生成姿态记录；缺缩略图或缩略图比原图旧就重做一张。

    **同名文件按视角归并成同一个姿态**：`cat_a_front.png` + `cat_a_side.png` 只要显示名都
    写成同一个（meta.json 里 name 相同），就是一个姿态的两个视角。
    按「文件名+大小+修改时间」判断是否变化，没变就直接用上次结果，不会重复解码图片。
    """
    global _custom_sig, _custom_poses
    files = _custom_files()
    sig = tuple(files)
    with _custom_lock:
        if sig == _custom_sig:
            return
        meta = _load_meta()
        groups, order, used_thumbs, skipped = {}, [], set(), []
        for name, _size, mtime in files:
            entry = meta.get(name) or {}
            display = clean_label(entry.get("name") or Path(name).stem, Path(name).stem)
            angle = entry.get("angle") if entry.get("angle") in ANGLE_LABELS else "front"
            cat = clean_label(entry.get("cat") or CUSTOM_CAT)

            # 缩略图跟文件走（一个文件一张），文件名去重避免 a.png / a.jpg 撞名
            stem = Path(name).stem
            thumb_key, dup = stem, 2
            while thumb_key in used_thumbs:
                thumb_key, dup = f"{stem} ({dup})", dup + 1
            thumb_name = f"{thumb_key}.jpg"
            try:
                thumb_path = CUSTOM_THUMB_DIR / thumb_name
                if not thumb_path.is_file() or int(thumb_path.stat().st_mtime) < mtime:
                    _make_thumb(CUSTOM_DIR / name, thumb_path)
            except Exception as err:  # 坏图直接不进库，免得选了才报错
                skipped.append(f"{name}（{err}）")
                continue
            used_thumbs.add(thumb_key)

            key = display
            # 同名又同视角：不覆盖，另起一个姿态，避免丢图
            if key in groups and angle in groups[key]["angles"]:
                seq = 2
                while f"{display} ({seq})" in groups:
                    seq += 1
                key = f"{display} ({seq})"
            slot = groups.setdefault(key, {"cat": cat, "angles": {}})
            slot["angles"][angle] = {"img": name, "thumb": thumb_name}
            if key not in order:
                order.append(key)

        poses = []
        for index, key in enumerate(order, 1):
            slot = groups[key]
            angles = {a: slot["angles"][a] for a in ANGLE_LABELS if a in slot["angles"]}
            poses.append(
                {
                    "no": f"{CUSTOM_SERIES_KEY}/{key}",
                    "root": CUSTOM_SERIES_KEY,
                    "series": CUSTOM_SERIES_KEY,
                    "code": f"C{index:03d}",
                    "cat": slot["cat"],
                    "name": key,
                    "nameJp": key,
                    "angles": angles,
                    "label": f"{CUSTOM_SERIES_NAME} · {key}",
                }
            )
        _custom_poses = poses
        _custom_sig = sig
        if skipped:
            print("[GG 姿态库] 这些自定义图片读不出来，已跳过：" + "；".join(skipped))


def safe_filename(raw: str) -> str:
    """只留文件名部分，去掉路径与非法字符；中文原样保留。"""
    name = Path(str(raw or "").replace("\\", "/")).name
    stem = Path(name).stem.strip(" .")
    ext = Path(name).suffix.lower()
    if ext not in IMAGE_EXTS:
        ext = ".png"
    stem = "".join(ch for ch in stem if ch not in ILLEGAL_CHARS and ord(ch) >= 32).strip(" .")
    if not stem:
        stem = "姿态"
    if stem.upper() in RESERVED_NAMES:
        stem = "_" + stem
    return stem[:60] + ext


def save_custom(filename: str, data: bytes, name=None, cat=None, angle=None) -> str:
    """写入一张自定义姿态图并把显示名 / 分类 / 视角记进 meta.json，返回落盘后的文件名。

    name 留空就用文件名（去掉扩展名）；同名 + 同视角的两张图不覆盖，落盘时自动加序号。
    """
    global _custom_sig
    safe = safe_filename(filename)
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    stem, ext = Path(safe).stem, Path(safe).suffix
    target, dup = CUSTOM_DIR / safe, 2
    while target.exists():
        target = CUSTOM_DIR / f"{stem} ({dup}){ext}"
        dup += 1
    target.write_bytes(data)
    set_meta(target.name, name=name or stem, cat=cat, angle=angle or "front")
    _custom_sig = None  # 让下次读索引重扫
    return target.name


def delete_custom(filename: str) -> bool:
    """删掉 custom/ 里的一张图，连它的缩略图与 meta 记录一起清掉。"""
    global _custom_sig
    target = (CUSTOM_DIR / Path(str(filename or "").replace("\\", "/")).name).resolve()
    if target.parent != CUSTOM_DIR.resolve() or not target.is_file():
        return False
    # 缩略图跟文件走，按 angles 里的 img 反查（no 是显示名，跟文件名不一定相同）
    thumb = None
    for pose in _custom_poses:
        for entry in pose["angles"].values():
            if entry["img"] == target.name:
                thumb = entry["thumb"]
                break
        if thumb:
            break
    try:
        target.unlink()
    except OSError:
        return False
    if thumb:
        try:
            (CUSTOM_THUMB_DIR / thumb).unlink()
        except OSError:
            pass
    items = dict(_load_meta())
    if items.pop(target.name, None) is not None:
        _write_meta(items)
    _custom_sig = None
    return True


def custom_count() -> int:
    _scan_custom()
    return len(_custom_poses)


def custom_nos(filenames) -> list:
    """一批文件各自落在哪个姿态上（no = custom/<显示名>），找不到给 None。

    导入后前端要用它跳到刚放进去的那张：显示名是用户填的，跟文件名不一定相同，
    而且同名同视角会被自动加序号，所以只有扫完目录才知道真正的 no。
    """
    _scan_custom()
    owner = {}
    for pose in _custom_poses:
        for entry in pose["angles"].values():
            owner[entry["img"]] = pose["no"]
    return [owner.get(name) for name in filenames]


# ---------- 对外查询 ----------


def index():
    """内置库 + 自定义库合并后的索引；自定义姿态排在最前面。"""
    base = _builtin()
    _scan_custom()
    if not _custom_poses:
        return base
    merged = dict(base)
    merged["poses"] = list(_custom_poses) + list(base["poses"])
    merged["series"] = (
        [
            {
                "key": CUSTOM_SERIES_KEY,
                "name": CUSTOM_SERIES_NAME,
                "nameJp": CUSTOM_SERIES_NAME,
                "short": CUSTOM_SERIES_SHORT,
                "count": len(_custom_poses),
            }
        ]
        + list(base["series"])
    )
    merged["customCount"] = len(_custom_poses)
    return merged


def pose_labels():
    """节点下拉框用的姿态名列表。"""
    return [pose["label"] for pose in index()["poses"]]


def series_options():
    """系列下拉：全部 + 各系列（自定义系列排最前，按姿态数降序）。"""
    return [ALL] + [series["name"] for series in index()["series"]]


def category_options():
    """分类下拉：全部 + 各分类（按姿态数降序）。"""
    counts = {}
    for pose in index()["poses"]:
        counts[pose["cat"]] = counts.get(pose["cat"], 0) + 1
    return [ALL] + sorted(counts, key=lambda cat: (-counts[cat], cat))


def find_pose(label):
    for pose in index()["poses"]:
        if pose["label"] == label:
            return pose
    raise PoseDBMissing(
        f"姿态库里没有「{label}」这一项。\n"
        "它可能已被删除或改名（自定义姿态的显示名就是文件名，改名后旧工作流里的名字会对不上）。"
        "请在节点里重新选一个姿态。"
    )


def series_key(name):
    for series in index()["series"]:
        if series["name"] == name:
            return series["key"]
    return None


def pool(series_name=None, category=ALL):
    """范围内随机的候选集。

    分类在该系列里没有匹配时先退到「只按系列」，再空则退全库，
    避免用户选了空组合后节点直接报错。
    """
    poses = index()["poses"]
    if not poses:
        raise PoseDBMissing(
            "姿态库是空的，没法抽图。\n"
            "可以在节点里点「导入」把自己的姿态图放进来，"
            "或者把 pose-db-01 的图片复制到 poses/ 下再运行 tools/build_pose_db.py。"
        )
    key = None if series_name in (None, ALL) else series_key(series_name)
    if key is not None:
        in_series = [pose for pose in poses if pose["series"] == key]
        if category and category != ALL:
            matched = [pose for pose in in_series if pose["cat"] == category]
            if matched:
                return matched
        if in_series:
            return in_series
    if category and category != ALL:
        matched = [pose for pose in poses if pose["cat"] == category]
        if matched:
            return matched
    return poses


def pick_angle(pose, angle_label, rng):
    """把角度下拉解析成具体视角；选「随机视角」时在该姿态可用的视角里抽。"""
    if angle_label == RANDOM_ANGLE:
        return rng.choice([key for key in ANGLE_LABELS if key in pose["angles"]])
    return LABEL_TO_ANGLE[angle_label]


def resolve(pose, angle_key):
    """返回 (姿态记录, 实际角度, 图片路径)。缺图时按 正面→其余角度 回退。"""
    angles = pose["angles"]
    custom = pose.get("root") == CUSTOM_SERIES_KEY
    base = CUSTOM_DIR if custom else IMG_DIR
    order = [angle_key, "front"] + [key for key in ANGLE_LABELS if key not in (angle_key, "front")]
    for key in order:
        entry = angles.get(key)
        if not entry:
            continue
        path = base / entry["img"]
        if path.is_file():
            return pose, key, path
    folder = "poses/custom" if custom else "poses/img"
    raise FileNotFoundError(
        f"姿态图文件缺失：{pose['no']}（找过 {angle_key}、正面等角度）。\n"
        f"请确认 {folder} 里的原图还在；内置库重新复制后要再跑一次 tools/build_pose_db.py。"
    )
