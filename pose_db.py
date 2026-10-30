"""多库索引、取图范围与图片定位。

本项目把「白模参考图库」抽象成一个可实例化的库（lib）：pose=姿态库、garment=服装库、
face=脸模库。每个库各自有目录、index.json 与角度集，资源平铺存放，
分类信息全部写在索引里（与姿态库约定一致，不靠子目录分堆）。

内置库索引由 tools/build_*_db.py 生成，索引缺失时 auto_build() 也会把原始图
（默认 PNG）转成 WebP 再建索引。**内置素材在插件目录里，用户素材在插件外面**：

    内置（随仓库，升级会被覆盖，属正常）  <插件>/poses|garment|faces/{img,thumbs,index.json}
    用户（升级不会碰）                  <ComfyUI>/user/default/guliposes/<lib>/custom/
    用户原始图（转换来源）               <ComfyUI>/user/default/guliposes/<lib>/png/

读索引时按目录签名自动把 custom/ 补进来，不需要重建内置库。一个文件一个视角，
视角按该库的角度集处理（姿态库 5 视角，服装库 / 脸模库单角度）。
"""

import io
import json
import os
import re
import shutil
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps


def _log(msg: str) -> None:
    """本模块唯一的日志出口。

    不用裸 print：ComfyUI 常被重定向到日志文件或由启动器接管 stdout，那样 Python 会按
    8KB 块缓冲，服务器一跑几小时都不 flush —— 启动时的收件箱播报、迁移提示等于没写。
    flush=True 保证每行立刻落盘，同时也照样进 ComfyUI 的 /internal/logs。
    """
    print(msg, flush=True)


NODE_DIR = Path(__file__).resolve().parent
DB_DIR = NODE_DIR / "poses"
# 服装库（garment）与姿态库（poses）平级，放在插件根目录下、与 poses 并列
GARMENT_DIR = NODE_DIR / "garment"
# 脸模库（face）同样与 poses 平级，目录名是 faces（已在插件根目录下）
FACE_DIR = NODE_DIR / "faces"

# ---------------------------------------------------------------------------
# 用户数据目录：一定放在插件目录**外面**。
#
# 插件升级有两条路——`git pull` 和「删掉文件夹重新解压」，后者会把插件目录里
# 的一切原样盖掉，包括用户自己导入的 `custom/` 和自己的 `png/` 原始素材。
# 所以这两类目录从 v1.2.2 起落在 ComfyUI 的 user 目录下，和插件源码彻底分开：
#
#   ComfyUI/user/default/guliposes/pose/custom/     节点里「导入」的图 + meta.json
#   ComfyUI/user/default/guliposes/pose/png/        自己丢进去的原始图（auto_build 会转）
#   ComfyUI/user/default/guliposes/garment/…        同上
#   ComfyUI/user/default/guliposes/face/…
#
# 内置素材（img/ thumbs/ index.json）仍随仓库分发——被覆盖掉是预期行为，它们是官方的。
# 想要换盘或集中管理，设环境变量 GULIPOSES_DATA_DIR 指到别处即可。
# ---------------------------------------------------------------------------


def _comfy_user_root() -> Optional[Path]:
    """ComfyUI 自己的 user 目录（新版有 folder_paths.get_user_directory）。"""
    try:
        import folder_paths  # ComfyUI 运行时才有；独立导入时拿不到
    except Exception:
        return None
    getter = getattr(folder_paths, "get_user_directory", None)
    if getter is None:
        return None
    try:
        return Path(getter())
    except Exception:
        return None


def _comfy_root_by_tree() -> Optional[Path]:
    """顺着插件目录往上找 ComfyUI 根（含 main.py 且有 custom_nodes/ 的那一层）。

    比写死 parents[1] 结实：有些管理器把插件装在 custom_nodes/<作者>/<插件> 下面，
    多一层目录就会指错地方。最多往上找 5 层。
    """
    for parent in list(NODE_DIR.parents)[:5]:
        if (parent / "main.py").is_file() and (parent / "custom_nodes").is_dir():
            return parent
    return None


def _detect_user_data_root() -> Path:
    """用户数据根目录，优先级：环境变量 > ComfyUI/user/default/guliposes > 兜底。"""
    env = (os.environ.get("GULIPOSES_DATA_DIR") or "").strip()
    if env:
        custom = Path(env).expanduser()
        return custom if custom.is_absolute() else (NODE_DIR / custom).resolve()
    user_root = _comfy_user_root()
    if user_root is None:
        comfy_root = _comfy_root_by_tree()
        user_root = (comfy_root / "user") if comfy_root is not None else None
    if user_root is not None:
        return user_root / "default" / "guliposes"
    # 最后兜底：插件内 userdata/（.gitignore 已忽略，git pull 不会碰；整目录覆盖仍会丢）
    return NODE_DIR / "userdata"


USER_DATA_ROOT = _detect_user_data_root()


def user_lib_dir(lib: str = "pose") -> Path:
    """某个库的用户数据目录（插件外面）。"""
    return USER_DATA_ROOT / lib


def custom_dir(lib: str = "pose") -> Path:
    """用户导入的图：<user>/<lib>/custom/。节点「导入」落盘、右键删除都在这里。"""
    return user_lib_dir(lib) / "custom"


# 姿态库（默认库）路径
INDEX_FILE = DB_DIR / "index.json"
IMG_DIR = DB_DIR / "img"
THUMB_DIR = DB_DIR / "thumbs"
CUSTOM_DIR = custom_dir("pose")
CUSTOM_THUMB_DIR = CUSTOM_DIR / "thumbs"
CUSTOM_META_FILE = CUSTOM_DIR / "meta.json"

# 通用角度标签（姿态库用全 5 视角；服装/脸模库在自己的索引与 LIB_DIRS 里声明自己的角度集）
ANGLE_LABELS = {"front": "正面", "high": "俯视", "low": "仰视", "side": "侧面", "diag": "斜侧"}
LABEL_TO_ANGLE = {label: key for key, label in ANGLE_LABELS.items()}
RANDOM_ANGLE = "随机视角"
ANGLE_CHOICES = list(ANGLE_LABELS.values()) + [RANDOM_ANGLE]

ALL = "全部"
EMPTY_HINT = "（库为空：请在节点里点「导入」放自己的图）"

# 各库的物理路径与角度集。加库只需在此追加一项 + 写对应的 build_*_db.py。
LIB_DIRS = {
    "pose": {
        "index": INDEX_FILE,
        "img": IMG_DIR,
        "thumb": THUMB_DIR,
        "custom": CUSTOM_DIR,
        "custom_thumb": CUSTOM_THUMB_DIR,
        "custom_meta": CUSTOM_META_FILE,
        "angles": ANGLE_LABELS,
    },
    "garment": {
        "index": GARMENT_DIR / "index.json",
        "img": GARMENT_DIR / "img",
        "thumb": GARMENT_DIR / "thumbs",
        "custom": custom_dir("garment"),
        "custom_thumb": custom_dir("garment") / "thumbs",
        "custom_meta": custom_dir("garment") / "meta.json",
        "angles": {"front": "正面"},
    },
    "face": {
        "index": FACE_DIR / "index.json",
        "img": FACE_DIR / "img",
        "thumb": FACE_DIR / "thumbs",
        "custom": custom_dir("face"),
        "custom_thumb": custom_dir("face") / "thumbs",
        "custom_meta": custom_dir("face") / "meta.json",
        "angles": {"front": "正面"},
    },
}


def _lib_cfg(lib: str = "pose") -> dict:
    return LIB_DIRS[lib]


def _merge_meta_file(src: Path, dst: Path) -> bool:
    """把老位置 meta.json 的条目并进新位置那份，返回是否写了盘。

    不能直接覆盖：两边都有记录时，覆盖等于把一边的显示名 / 分类 / 视角抹掉。
    并集里以新位置为准（它更新），老位置只补新位置没有的条目。
    """
    try:
        old = json.loads(src.read_text(encoding="utf-8")).get("items") or {}
    except Exception:
        return False
    cur = {}
    if dst.is_file():
        try:
            cur = json.loads(dst.read_text(encoding="utf-8")).get("items") or {}
        except Exception:
            cur = {}
    merged = dict(old)
    merged.update(cur)
    if merged == cur:
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(
            json.dumps({"version": 1, "items": merged}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as err:
        _log(f"[GG 图库] 合并 {dst.name} 失败：{err}")
        return False
    return True


def migrate_legacy_userdata(move: bool = False) -> list[str]:
    """把插件目录里老位置的用户素材搬到 USER_DATA_ROOT（v1.2.2 之前的 custom/ 与 png/）。

    默认**只复制、不动原件**：新旧两版插件都能读到，回滚也不会空手。
    move=True 时复制成功后删源（`python tools/userdata.py move` 用）。
    返回已落到用户数据区的文件（形如 `garment/custom/xxx.webp`）。
    """
    copied: list[str] = []
    legacy_dirs = []
    for lib in LIB_DIRS:
        root = LIB_DIRS[lib]["index"].parent
        for legacy, target in ((root / "custom", custom_dir(lib)), (root / RAW_SUBDIR, raw_dir(lib))):
            if legacy.is_dir():
                legacy_dirs.append((lib, legacy, target))
    for lib, legacy, target in legacy_dirs:
        for src in sorted(legacy.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(legacy)
            # thumbs/ 是派生物，到那边会按需重新生成，不必搬
            if "thumbs" in rel.parts:
                continue
            # 只搬素材本身（图片 + meta.json）。老目录里的 README 是引导文案，
            # 新位置有自己的一份，搬过去反而会把新版说明覆盖成旧的。
            if src.suffix.lower() not in IMAGE_EXTS and src.name != "meta.json":
                continue
            dst = target / rel
            # meta.json 走合并：直接复制会把新位置已有的显示名 / 分类 / 视角盖掉，
            # 图还在但全变成「文件名 + 正面 + 自定义」，等于用户自定义内容失效。
            if src.name == "meta.json":
                if _merge_meta_file(src, dst):
                    _custom_cache.pop(lib, {})  # 让下次读索引重读 meta
                    copied.append(f"{lib}/{dst.relative_to(user_lib_dir(lib))}")
                if move:
                    try:
                        src.unlink()
                    except OSError:
                        pass
                continue
            try:
                if dst.exists() and dst.stat().st_size == src.stat().st_size:
                    continue  # 已经搬过（或同名同大小），不重复写
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            except OSError as err:
                _log(f"[GG 图库] 迁移 {src.name} 失败：{err}")
                continue
            copied.append(f"{lib}/{dst.relative_to(user_lib_dir(lib))}")
            if move:
                try:
                    src.unlink()
                except OSError:
                    pass
    if move:
        # 原件都搬走了就把空壳目录收掉；插件目录变干净，下次升级没什么可覆盖的
        for _lib, legacy, _target in legacy_dirs:
            for path in sorted(legacy.rglob("*"), reverse=True):
                if path.is_dir() and not any(path.iterdir()):
                    try:
                        path.rmdir()
                    except OSError:
                        pass
            if legacy.is_dir() and not any(legacy.iterdir()):
                try:
                    legacy.rmdir()
                except OSError:
                    pass
    return copied


_userdata_ready = False

# 首次启动时写一份到用户数据目录里，防止用户不敢动 / 误删。
# 更新插件不会覆盖这个文件（它在插件外面）。
_USER_DATA_README = """GG 图库（ComfyUI-GuliPoses）· 用户素材目录
=================================================

升级 / 重装节点不会动这里的任何东西。可以把整个 guliposes 文件夹备份或挪到别的盘，
再用环境变量 GULIPOSES_DATA_DIR 指过来。

pose/  garment/  face/   三个库各一份，结构相同：

  custom/    节点里点「导入」放进来、或右键删除的图都在这。里面有：
               *.webp / *.png ...   图片本体
               meta.json            显示名 / 分类 / 视角
               thumbs/              缩略图（可删，会自动重生成）
  png/       想批量加图就把原始图（PNG / JPG / BMP）丢这里，重启 ComfyUI 会自动
             转成 WebP 并重建索引。兼容旧位置：插件目录里的 /png/ 也还认。

内置图库（随身分发的姿态 / 服装 / 脸模）不在这里——那些在插件目录下，
升级时被覆盖是正常的，反正每次升级都是同一批官方素材。

命令行工具（用 ComfyUI 自带的 python 跑）：
  python tools/userdata.py info      看数据在哪、有多少
  python tools/userdata.py migrate   把插件内老位置的素材复制过来（不动原件）
  python tools/userdata.py move      同上并删掉原件
  python tools/userdata.py backup    打个 zip 备份
"""


def _write_userdata_readme() -> None:
    readme = USER_DATA_ROOT / "说明_README.txt"
    if readme.is_file():
        return
    try:
        readme.write_text(_USER_DATA_README, encoding="utf-8")
    except OSError:
        pass


def ensure_userdata() -> None:
    """启动时接管老位置的用户素材、结算收件箱；只跑一次，失败也不影响节点使用。"""
    global _userdata_ready
    if _userdata_ready:
        return
    _userdata_ready = True
    try:
        USER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        _write_userdata_readme()
        copied = migrate_legacy_userdata()
    except Exception as err:  # 目录不可写等情况：节点照旧能用，只是素材还在老位置
        _log(f"[GG 图库] 用户素材目录准备失败（不影响使用）：{err}")
        return
    if copied:
        _log(f"[GG 图库] 已把 {len(copied)} 个用户素材搬到 {USER_DATA_ROOT}")
        _log("          插件内原文件保留，确认无误后可自行删除；")
        _log("          以后把图放进这个目录，升级节点（含整目录覆盖）不会再丢。")

    # 收件箱：用户把图包丢进插件根的 inbox/ 就自动入库，不用记路径
    try:
        _ensure_inbox()
        drained = drain_all_inboxes()
    except Exception as err:
        _log(f"[GG 图库] 收件箱结算失败（不影响使用）：{err}")
        return
    for lib, names in drained.items():
        where = {"pose": "姿态库", "garment": "服装库", "face": "脸模库"}.get(lib, lib)
        _log(f"[GG 图库] 收件箱：{len(names)} 张图已入库到{where}（系列「我的」）")
    if drained:
        _log(f"          刷新页面即可在画廊「我的」系列看到；原文件已搬到 {USER_DATA_ROOT}")


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
# 原始图默认丢进用户数据目录下的 png/ 子目录（默认 PNG），auto_build 会自动转成 WebP
RAW_SUBDIR = "png"
THUMB_SIDE = 320


def raw_dir(lib: str = "pose") -> Path:
    """用户放原始图（默认 PNG）的目录：<user>/<lib>/png/。auto_build 会自动转换。

    放在插件外面，升级时不会被覆盖；转换产物（img/*.webp）丢了也能从这里重建。
    """
    return user_lib_dir(lib) / RAW_SUBDIR


ILLEGAL_CHARS = '\\/:*?"<>|'
# Windows 里不能当文件名用的保留字，撞上就加下划线
RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
)

# 自定义库系列（每个 lib 共用同一套「我的」系列键，但显示名按库区分）
CUSTOM_SERIES_KEY = "custom"
CUSTOM_SERIES_SHORT = "我的"
CUSTOM_CAT = "自定义"

_lock = threading.Lock()

# 按 lib 分别缓存：避免多库互相污染，也保证 pose 库零回归
_builtin_cache: dict = {}   # lib -> {"index":..., "mtime":...}
_custom_cache: dict = {}    # lib -> {"poses":..., "sig":..., "meta":..., "meta_mtime":...}
_raw_cache: dict = {}       # lib -> {"sig":..., "pending":...}  原始图是否有待转换的新图
_auto_sig: dict = {}        # lib -> index.json 里记录的 imgSig（自动建库的库才非 None）



class PoseDBMissing(RuntimeError):
    """库还没准备好（空库 / 索引缺失），或选中的姿态已经不在库里。"""


def _custom_series_name(lib: str = "pose") -> str:
    return {"pose": "我的姿态", "garment": "我的服装", "face": "我的脸模"}.get(lib, "我的")


def _empty_base(angles: dict) -> dict:
    return {
        "generated": None,
        "source": None,
        "angles": [{"key": key, "label": label} for key, label in angles.items()],
        "series": [],
        "poses": [],
    }


def _builtin(lib: str = "pose"):
    """内置库索引；文件缺失时按空库处理，只用自定义图也能开工。

    按 index.json 的 mtime 判断要不要重读，重跑 build 脚本后不用重启 ComfyUI。
    """
    cfg = _lib_cfg(lib)
    cache = _builtin_cache.setdefault(lib, {})
    # 用纳秒精度：秒级 mtime 在同一秒内重建索引时不会变，会读到旧缓存
    try:
        mtime = cfg["index"].stat().st_mtime_ns
    except OSError:
        mtime = None
    if cache.get("index") is not None and cache.get("mtime") == mtime:
        return cache["index"]
    if mtime is None:
        # 索引缺失：库目录里若直接放了原始图（默认 PNG），现场转 WebP 并建索引，
        # 用户把图丢进对应目录、重启即可用，不必手动跑 build 脚本。
        auto_build(lib)
        try:
            mtime = cfg["index"].stat().st_mtime_ns
        except OSError:
            mtime = None
    if mtime is None:
        data = _empty_base(cfg["angles"])
    else:
        data = json.loads(cfg["index"].read_text(encoding="utf-8"))
        for key, default in _empty_base(cfg["angles"]).items():
            data.setdefault(key, default)
        # 给每条内置姿态打上所属库，resolve/ensure_thumb 据此找对目录
        for p in data.get("poses", []):
            p["lib"] = lib
        # 顺带同步 imgSig：索引被外部脚本重写过也不会误判成「有变化」
        if lib in _auto_sig or "imgSig" in data:
            _auto_sig[lib] = data.get("imgSig")
    cache["index"] = data
    cache["mtime"] = mtime
    return data


# ---------- 原始图自动转 WebP 并建索引（用户把图丢进库目录时）----------

WEBP_QUALITY = 95
WEBP_METHOD = 4

# auto_build 兜底建索引时的系列名（按库区分，免得服装库重建后显示「脸模」）
_AUTO_SERIES = {
    "pose": ("default", "姿态"),
    "garment": ("default", "穿搭"),
    "face": ("face", "脸模"),
}


def _convert_to_webp(src: Path, dst: Path) -> None:
    """源图（默认 PNG）转成插件统一格式的 WebP，保持原尺寸、RGB。

    WebP 已存在且不比源图旧就跳过；源图更新（同名覆盖）则重新转，保证内容是最新的。
    """
    try:
        # 纳秒精度：同一秒内覆盖同名源图也能识别出「源图更新了」
        if dst.is_file() and dst.stat().st_mtime_ns >= src.stat().st_mtime_ns:
            return
    except OSError:
        pass
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f"{dst.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.save(tmp, "WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
        tmp.replace(dst)
    except OSError:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _img_sig(lib: str = "pose"):
    """img/ 下 WebP 的签名：[文件数, 最新 mtime_ns]；目录不存在返回 None。

    只 scandir + stat，不解码图片，几十张图的成本在微秒级。
    """
    img = _lib_cfg(lib)["img"]
    try:
        files = [
            e
            for e in os.scandir(img)
            if e.is_file() and Path(e.name).suffix.lower() == ".webp"
        ]
    except OSError:
        return None
    newest = 0
    for e in files:
        try:
            newest = max(newest, e.stat().st_mtime_ns)
        except OSError:
            continue
    return [len(files), newest]


def auto_build(lib: str = "face") -> None:
    """把库目录里的原始图（默认 PNG）转成 WebP，并以 img/*.webp 重建 index.json。

    幂等：已转的不会重复转。供 tools/build_*_db.py 与 _builtin/_raw_pending/_img_pending
    调用，保证「丢进图就能用、删了图就消失」。
    """
    cfg = _lib_cfg(lib)
    root = cfg["index"].parent  # 库根目录，如 faces/
    img_dir = cfg["img"]
    # 原始图目录在插件外面（用户数据区），升级覆盖插件也丢不了源图
    raw_sub = raw_dir(lib)
    raw_sub.mkdir(parents=True, exist_ok=True)
    # 原始图优先从用户数据区的 png/ 收；为兼容旧用法，也接受直接丢在库根目录或 img/ 下
    raw = []
    for d in (raw_sub, root, img_dir):
        try:
            for e in os.scandir(d):
                if not e.is_file():
                    continue
                suffix = Path(e.name).suffix.lower()
                if suffix in IMAGE_EXTS and suffix != ".webp":
                    raw.append(Path(e.path))
        except OSError:
            continue
    if not raw and not any(img_dir.glob("*.webp")):
        _auto_sig[lib] = _img_sig(lib)  # 空库：记住现状，别每轮都进来扫一遍
        return  # 真的空库，等用户放图

    # 1) 原始图 → img/ 下的 WebP（不递归 img/thumbs/custom 子目录）
    for src in raw:
        dst = img_dir / f"{src.stem}.webp"
        try:
            _convert_to_webp(src, dst)
        except Exception as exc:  # 单张坏图不影响其它
            _log(f"[GG {lib} 库] 转换失败 {src.name}: {exc}")

    # 2) 以 img/ 下现有 WebP 为准建索引（无系列分目录时归到一个默认系列）
    webs = sorted(img_dir.glob("*.webp"))
    if not webs:
        _auto_sig[lib] = _img_sig(lib)  # 全是坏图：别让 _img_pending 反复触发重建
        return
    series_key, series_name = _AUTO_SERIES.get(lib, ("default", "默认"))
    poses = []
    for im in webs:
        stem = im.stem
        poses.append(
            {
                "no": f"{series_key}/{stem}",
                "series": series_key,
                "code": stem,
                "cat": series_name,
                "catJp": series_name,
                "name": stem,
                "nameJp": stem,
                "keywords": "",
                "angles": {"front": {"img": f"{stem}.webp", "thumb": f"{stem}.jpg"}},
                "label": f"{series_name} {stem}",
            }
        )
    index = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": f"auto-built from raw images in {lib}/{RAW_SUBDIR}/",
        "lib": lib,
        # 建库时 img/ 的签名（文件数 + 最新 mtime）。img/ 变了就据此判断要不要重建，
        # 手工/官方索引没这个字段，因此永远走不到自动重建，元数据不会被覆盖。
        "imgSig": _img_sig(lib),
        "poseCount": len(poses),
        "imageCount": len(poses),
        "angles": [{"key": "front", "label": "正面"}],
        "series": [
            {
                "key": series_key,
                "name": series_name,
                "nameJp": series_name,
                "short": series_name,
                "count": len(poses),
            }
        ],
        "poses": poses,
    }
    cfg["index"].parent.mkdir(parents=True, exist_ok=True)
    tmp = cfg["index"].with_name(f"{cfg['index'].name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        tmp.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(cfg["index"])
    except OSError:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    # 建完立刻记下这次签名：_img_pending 下一轮就不会把它当「有变化」再重建一次
    _auto_sig[lib] = index["imgSig"]


def _auto_managed(lib: str = "pose") -> bool:
    """这个库的索引是否由 auto_build 生成（因而允许自动重建）。

    判据是索引里带 `imgSig`，或 source 以 `auto-built` 开头（早期自动建的索引）。
    姿态库（288 组、4 系列 26 分类）和服装库（1405 套、6 类型 19 分类）是人工整理
    的索引，没有这个字段 —— 一旦被 auto_build 重扫，元数据会被冲成「单系列 + 默认
    分类」，所以这里必须挡住：往 poses/png/ 丢一张图不该把整个库的分类抹平。

    索引还不存在时返回 True：新库第一次建索引就该走自动流程。
    """
    cfg = _lib_cfg(lib)
    if lib not in _auto_sig:
        try:
            data = json.loads(cfg["index"].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return True  # 还没索引，交给 _builtin 建
        sig = data.get("imgSig")
        if sig is None and str(data.get("source", "")).startswith("auto-built"):
            sig = []  # 早期自动索引没写 imgSig：给一次自愈机会，重建后就带上
        _auto_sig[lib] = sig
    return _auto_sig[lib] is not None


def _img_pending(lib: str = "pose") -> bool:
    """img/ 里的 WebP 是否和 index.json 记录的不一致（用户删了/换了图）。

    只对 auto_build 生成的索引生效，判断依据见 _auto_managed()。
    """
    if not _auto_managed(lib):
        return False
    stored = _auto_sig.get(lib)
    if stored is None:
        return False
    sig = _img_sig(lib)
    if sig is None:
        return False
    return list(stored) != sig


# ---------- 自定义库 ----------


def _custom_files(lib: str = "pose"):
    """<lib>/custom/ 根目录下的图片：[(文件名, 大小, 修改时间)]，按名字排序让编号稳定。"""
    cfg = _lib_cfg(lib)
    try:
        with os.scandir(cfg["custom"]) as entries:
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


def ensure_thumb(thumb_name: str, lib: str = "pose") -> Optional[Path]:
    """拿到缩略图路径；没有就用原图现生成一张。

    内置库只分发原图：缩略图不随仓库分发（能省体积和文件数），首次请求时现场生成并落盘，
    之后走浏览器缓存。原图和缩略图同 stem 不同后缀（`xxx.webp` → `xxx.jpg`）。
    """
    cfg = _lib_cfg(lib)
    name = Path(str(thumb_name or "")).name
    if not name:
        return None
    target = cfg["thumb"] / name
    if target.is_file():
        return target

    stem = Path(name).stem
    source = next((p for ext in IMAGE_EXTS if (p := cfg["img"] / f"{stem}{ext}").is_file()), None)
    if source is None:
        return None

    target.parent.mkdir(parents=True, exist_ok=True)
    # 同一张图被并发请求时各写各的临时文件，最后一次 replace 胜出，不会有人读到半个 JPEG
    tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        _make_thumb(source, tmp)
        tmp.replace(target)
    except OSError:
        tmp.unlink(missing_ok=True)
        return None
    return target


def clean_label(raw: str, fallback: str = CUSTOM_CAT) -> str:
    """显示名 / 分类名：去控制字符、去路径符号，保留中文与空格。"""
    text = str(raw or "").strip()
    text = "".join(ch for ch in text if ord(ch) >= 32 and ch not in ILLEGAL_CHARS).strip(" .")
    return text[:60] or fallback


def _load_meta(lib: str = "pose") -> dict:
    """<lib>/custom/meta.json：{文件名: {name, cat, angle}}；按 mtime 缓存。"""
    cfg = _lib_cfg(lib)
    cache = _custom_cache.setdefault(lib, {})
    try:
        mtime = int(cfg["custom_meta"].stat().st_mtime)
    except OSError:
        mtime = None
    if cache.get("meta") is not None and cache.get("meta_mtime") == mtime:
        return cache["meta"]
    items = {}
    if mtime is not None:
        try:
            data = json.loads(cfg["custom_meta"].read_text(encoding="utf-8"))
            items = data.get("items") or {}
        except Exception as err:
            _log(f"[GG 姿态库] {cfg['custom_meta']} 读不出来，按文件名兜底：{err}")
    cache["meta"] = items
    cache["meta_mtime"] = mtime
    return items


def _write_meta(items: dict, lib: str = "pose") -> None:
    cfg = _lib_cfg(lib)
    cache = _custom_cache.setdefault(lib, {})
    cfg["custom"].mkdir(parents=True, exist_ok=True)
    cfg["custom_meta"].write_text(
        json.dumps({"version": 1, "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    cache["meta"] = items
    try:
        cache["meta_mtime"] = int(cfg["custom_meta"].stat().st_mtime)
    except OSError:
        cache["meta_mtime"] = None


def set_meta(filename: str, name=None, cat=None, angle=None, lib: str = "pose") -> None:
    """记一张图的显示名 / 分类 / 视角；只覆盖传进来的字段。"""
    cfg = _lib_cfg(lib)
    angles = cfg["angles"]
    items = dict(_load_meta(lib))
    entry = dict(items.get(filename) or {})
    if name:
        entry["name"] = clean_label(name, Path(filename).stem)
    if cat:
        entry["cat"] = clean_label(cat, CUSTOM_CAT)
    if angle in angles:
        entry["angle"] = angle
    items[filename] = entry
    _write_meta(items, lib)


def _scan_custom(lib: str = "pose") -> None:
    """扫 <lib>/custom/，生成姿态记录；缺缩略图或缩略图比原图旧就重做一张。

    **同名文件按视角归并成同一个姿态**：cat_a_front.png + cat_a_side.png 只要显示名都
    写成同一个（meta.json 里 name 相同），就是一个姿态的两个视角。
    """
    cfg = _lib_cfg(lib)
    angles = cfg["angles"]
    cache = _custom_cache.setdefault(lib, {})
    files = _custom_files(lib)
    sig = tuple(files)
    if cache.get("poses") is not None and cache.get("sig") == sig:
        return
    meta = _load_meta(lib)
    groups, order, used_thumbs, skipped = {}, [], set(), []
    for name, _size, mtime in files:
        entry = meta.get(name) or {}
        if entry.get("name"):
            display = clean_label(entry["name"], Path(name).stem)
            angle = entry.get("angle") if entry.get("angle") in angles else "front"
        else:
            # 没有 meta 记录（用户直接往 custom/ 拷图、或 meta 丢过）：从文件名推视角，
            # 「姿势A_side.png」照样能归成 side 视角，不会全挤到正面。
            display, angle = _split_angle(Path(name).stem, angles)
            display = clean_label(display, Path(name).stem)
        cat = clean_label(entry.get("cat") or CUSTOM_CAT)

        # 缩略图跟文件走（一个文件一张），文件名去重避免 a.png / a.jpg 撞名
        stem = Path(name).stem
        thumb_key, dup = stem, 2
        while thumb_key in used_thumbs:
            thumb_key, dup = f"{stem} ({dup})", dup + 1
        thumb_name = f"{thumb_key}.jpg"
        try:
            thumb_path = cfg["custom_thumb"] / thumb_name
            if not thumb_path.is_file() or int(thumb_path.stat().st_mtime) < mtime:
                _make_thumb(cfg["custom"] / name, thumb_path)
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
        ang = {a: slot["angles"][a] for a in angles if a in slot["angles"]}
        poses.append(
            {
                "no": f"{CUSTOM_SERIES_KEY}/{key}",
                "lib": lib,
                "root": CUSTOM_SERIES_KEY,
                "series": CUSTOM_SERIES_KEY,
                "code": f"C{index:03d}",
                "cat": slot["cat"],
                "name": key,
                "nameJp": key,
                "angles": ang,
                "label": f"{_custom_series_name(lib)} · {key}",
            }
        )
    with _lock:
        cache["poses"] = poses
        cache["sig"] = sig
        if skipped:
            _log(f"[GG 姿态库] {lib} 自定义图片读不出来，已跳过：" + "；".join(skipped))


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


def save_custom(filename: str, data: bytes, name=None, cat=None, angle=None, lib: str = "pose") -> str:
    """写入一张自定义图并把显示名 / 分类 / 视角记进 meta.json，返回落盘后的文件名。"""
    cfg = _lib_cfg(lib)
    cache = _custom_cache.setdefault(lib, {})
    safe = safe_filename(filename)
    cfg["custom"].mkdir(parents=True, exist_ok=True)
    stem, ext = Path(safe).stem, Path(safe).suffix
    target, dup = cfg["custom"] / safe, 2
    while target.exists():
        target = cfg["custom"] / f"{stem} ({dup}){ext}"
        dup += 1
    target.write_bytes(data)
    set_meta(target.name, name=name or stem, cat=cat, angle=angle, lib=lib)
    cache["sig"] = None  # 让下次读索引重扫
    return target.name


# ---------- 收件箱：图包丢进插件目录就自动入库 ----------
#
# 用户手里通常是一个文件夹或一个 zip，让他自己去 ComfyUI/user/default/guliposes/…
# 里翻目录、按库分位置，太麻烦。所以插件根目录下留一个收件箱：
#
#   <插件>/inbox/pose/      丢这里 → 进姿态库「我的姿态」
#   <插件>/inbox/garment/   丢这里 → 进服装库「我的服装」
#   <插件>/inbox/face/      丢这里 → 进脸模库「我的脸模」
#   <插件>/inbox/           直接丢根目录也行，按姿态库收（日志会写明）
#
# 图片、子文件夹（递归）、zip 都认；启动时或跑 tools/import_batch.py 时结算，
# 结算完源文件搬走（不是复制），收件箱自动清空。非图片文件（说明、txt）原样留着。

INBOX_SUBDIR = "inbox"
# 单张图上限、一次 zip 最多取多少个条目：防呆，别让一个几百 MB 的包把启动卡住
MAX_INBOX_FILE = 200 * 1024 * 1024
MAX_ZIP_ENTRIES = 2000

# 文件名尾部的视角标记 → 角度 key。批量导入靠它把「姿势A_front / 姿势A_side」
# 归成同一个姿态的两个视角，而不是两个各自独立的姿态。
_ANGLE_HINTS = {
    "front": "front",
    "正面": "front",
    "side": "side",
    "侧面": "side",
    "high": "high",
    "俯视": "high",
    "top": "high",
    "low": "low",
    "仰视": "low",
    "diag": "diag",
    "斜侧": "diag",
    "斜侧面": "diag",
}

_INBOX_README = """把图包丢在这里，重启 ComfyUI 就自动进库
==========================================

  inbox/pose/       → 姿态库「我的姿态」（可多视角）
  inbox/garment/    → 服装库「我的服装」
  inbox/face/       → 脸模库「我的脸模」
  inbox/            → 直接丢这里也行，按姿态库收

认这些：单张图片、整个文件夹（会递归找图）、zip 压缩包。
不认：其它文件（说明、txt）——原样留着，不会被删。

文件名带视角后缀会自动识别，多视角合成同一个姿态：
  姿势A_front.png + 姿势A_side.png  →  「姿势A」的正反两个视角
支持的后缀：front / side / high / low / diag，或 正面 / 侧面 / 俯视 / 仰视 / 斜侧。

结算完源文件会被搬走（进库），收件箱里不留副本。
不用重启也能立刻结算：

    python tools/import_batch.py "D:\\图包" --lib garment
    python tools/import_batch.py "D:\\图包.zip" --lib pose
    python tools/import_batch.py --scan

两个位置都认，效果一样：
  插件目录 .../ComfyUI-GuliPoses/inbox/       丢着方便，但没结算就升级会被覆盖
  ComfyUI/user/default/guliposes/inbox/       外部目录，升级不会碰，最保险
"""


def _inbox_roots() -> list[Path]:
    """收件箱的两个根：插件目录（方便）与用户数据区（升级不会碰，最保险）。"""
    return [NODE_DIR / INBOX_SUBDIR, USER_DATA_ROOT / INBOX_SUBDIR]


def inbox_dir(lib: str = "pose") -> Path:
    """收件箱（插件内那份）：<插件>/inbox/<lib>/。用户数据区还有一份同名目录。"""
    return NODE_DIR / INBOX_SUBDIR / lib


def _split_angle(stem: str, angles: dict) -> tuple[str, str]:
    """从文件名尾部剥离视角标记：'姿势A_side' → ('姿势A', 'side')。

    剥完名字会空（文件就叫 side.png）就保持原名，不硬拆。
    单角度库（服装 / 脸模）没有 side 这个角度，但后缀照样剥掉——不然显示名里
    会留一个没用的 `_side`，只是角度按正面算。
    """
    low = stem.lower()
    default = "front" if "front" in angles else next(iter(angles))
    for token, key in _ANGLE_HINTS.items():
        for sep in ("_", "-", " ", "·"):
            suffix = (sep + token).lower()
            if low.endswith(suffix) and len(stem) > len(suffix):
                return stem[: -len(suffix)].strip(" _-·"), (key if key in angles else default)
    return stem, default


def _import_batch(lib: str, items: list, cat: Optional[str] = None) -> list[str]:
    """批量落盘：一次写完所有图、只写一次 meta.json。

    items 是 [(文件名, bytes)]。逐张调 save_custom 也能用，但那样每张都重写一遍
    meta.json，几百张时会变成 O(n²) 的写放大。
    """
    cfg = _lib_cfg(lib)
    angles = cfg["angles"]
    cfg["custom"].mkdir(parents=True, exist_ok=True)
    meta = dict(_load_meta(lib))
    taken = set()
    saved = []
    for filename, data in items:
        if not data:
            continue
        safe = safe_filename(filename)
        stem, ext = Path(safe).stem, Path(safe).suffix
        name, dup = stem, 2
        while f"{name}{ext}" in taken or (cfg["custom"] / f"{name}{ext}").exists():
            name = f"{stem} ({dup})"
            dup += 1
        target = cfg["custom"] / f"{name}{ext}"
        try:
            target.write_bytes(data)
        except OSError as err:
            _log(f"[GG 图库] 写入失败 {target.name}: {err}")
            continue
        taken.add(target.name)
        display, angle = _split_angle(stem, angles)
        meta[target.name] = {
            "name": clean_label(display, stem),
            "cat": clean_label(cat or CUSTOM_CAT, CUSTOM_CAT),
            "angle": angle,
        }
        saved.append(target.name)
    if saved:
        _write_meta(meta, lib)
        _custom_cache.setdefault(lib, {})["sig"] = None
    return saved


def _images_in_zip(data: bytes) -> list[tuple[str, bytes]]:
    """从 zip 里取图片，不落盘解压：只读图片条目，跳过目录与超大的文件。"""
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()][:MAX_ZIP_ENTRIES]
        for info in infos:
            if Path(info.filename).suffix.lower() not in IMAGE_EXTS:
                continue
            if info.file_size > MAX_INBOX_FILE:
                _log(f"[GG 图库] 压缩包里这张太大，跳过：{info.filename}")
                continue
            try:
                out.append((Path(info.filename).name, zf.read(info)))
            except Exception as err:
                _log(f"[GG 图库] 压缩包里读不出来 {info.filename}: {err}")
    return out


def _collect_inbox(folder: Path, recursive: bool) -> list[tuple[str, bytes]]:
    """收一个目录下的图片与 zip，收完把源文件删掉（搬走语义）。"""
    if not folder.is_dir():
        return []
    items = []
    paths = sorted(folder.rglob("*")) if recursive else sorted(folder.iterdir())
    for path in paths:
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTS:
            try:
                if path.stat().st_size > MAX_INBOX_FILE:
                    _log(f"[GG 图库] 跳过过大的图片：{path.name}")
                    continue
                items.append((path.name, path.read_bytes()))
            except OSError as err:
                _log(f"[GG 图库] 读不出来 {path.name}: {err}")
                continue
        elif suffix == ".zip":
            try:
                items.extend(_images_in_zip(path.read_bytes()))
            except Exception as err:
                _log(f"[GG 图库] 解不开的压缩包 {path.name}: {err}")
                continue
        else:
            continue  # 说明文件之类，原样留着
        try:
            path.unlink()
        except OSError as err:
            _log(f"[GG 图库] 搬走后删不掉 {path.name}: {err}")
    # 收完把空文件夹收掉（inbox 根目录本身留着当入口）
    for sub in sorted(folder.rglob("*"), reverse=True):
        if sub.is_dir() and not any(sub.iterdir()):
            try:
                sub.rmdir()
            except OSError:
                pass
    return items


def drain_inbox(lib: str = "pose", include_root: bool = False) -> list[str]:
    """结算某个库的收件箱（插件内与用户数据区两处），返回入库后的文件名列表。"""
    items = []
    for base in _inbox_roots():
        items += _collect_inbox(base / lib, recursive=True)
    if include_root:
        # inbox/ 根下直接丢的文件按默认库（姿态）收，只扫一层，别把各库子目录再扫一遍
        for base in _inbox_roots():
            items += _collect_inbox(base, recursive=False)
    if not items:
        return []
    return _import_batch(lib, items)


def drain_all_inboxes() -> dict:
    """启动时统一结算，返回 {lib: [文件名…]}（只含真的进了库的）。"""
    out = {}
    for lib in LIB_DIRS:
        got = drain_inbox(lib)
        if got:
            out[lib] = got
    root_got = drain_inbox("pose", include_root=True)
    if root_got:
        out.setdefault("pose", []).extend(root_got)
    return out


def _ensure_inbox() -> None:
    """建好收件箱目录（插件内 + 用户数据区各一套），各放一份简短说明。"""
    for base in _inbox_roots():
        for folder in [base] + [base / lib for lib in LIB_DIRS]:
            try:
                folder.mkdir(parents=True, exist_ok=True)
                readme = folder / "说明_README.txt"
                if not readme.is_file():
                    readme.write_text(_INBOX_README, encoding="utf-8")
            except OSError:
                pass


def delete_custom(filename: str, lib: str = "pose") -> bool:
    """删掉 <lib>/custom/ 里的一张图，连它的缩略图与 meta 记录一起清掉。"""
    cfg = _lib_cfg(lib)
    cache = _custom_cache.setdefault(lib, {})
    target = (cfg["custom"] / Path(str(filename or "").replace("\\", "/")).name).resolve()
    if target.parent != cfg["custom"].resolve() or not target.is_file():
        return False
    # 缩略图跟文件走，按 angles 里的 img 反查（no 是显示名，跟文件名不一定相同）。
    # 新进程里还没扫过目录时缓存是空的，直接反查会漏掉缩略图，留一份死链在 thumbs/ 里。
    if "poses" not in cache:
        try:
            _scan_custom(lib)
        except Exception:
            pass
    thumb = None
    for pose in cache.get("poses", []):
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
            (cfg["custom_thumb"] / thumb).unlink()
        except OSError:
            pass
    items = dict(_load_meta(lib))
    if items.pop(target.name, None) is not None:
        _write_meta(items, lib)
    cache["sig"] = None
    return True


def custom_count(lib: str = "pose") -> int:
    _scan_custom(lib)
    return len(_custom_cache.setdefault(lib, {}).get("poses", []))


def custom_nos(filenames, lib: str = "pose") -> list:
    """一批文件各自落在哪个姿态上（no = custom/<显示名>），找不到给 None。"""
    _scan_custom(lib)
    poses = _custom_cache.setdefault(lib, {}).get("poses", [])
    owner = {}
    for pose in poses:
        for entry in pose["angles"].values():
            owner[entry["img"]] = pose["no"]
    return [owner.get(name) for name in filenames]


# ---------- 对外查询 ----------


def _raw_pending(lib: str = "pose") -> bool:
    """`<lib>/png/` 里是否有尚未转换（或比 WebP 更新）的原始图。

    只看文件 mtime，不解码图片；用 sig 缓存，png/ 没变化就直接返回上次结论。
    这样用户把新 PNG 丢进 png/、即使索引已存在，也能被自动转掉。
    """
    raw = raw_dir(lib)
    img = _lib_cfg(lib)["img"]
    if not _auto_managed(lib):
        return False
    try:
        raw_sig = raw.stat().st_mtime_ns
        img_sig = img.stat().st_mtime_ns
        entries = []
        for entry in os.scandir(raw):
            if not entry.is_file():
                continue
            suffix = Path(entry.name).suffix.lower()
            if suffix not in IMAGE_EXTS or suffix == ".webp":
                continue
            entries.append((Path(entry.name).stem, entry.stat().st_mtime_ns))
    except OSError:
        return False
    # sig 里带上「文件数 + 最新文件 mtime」：同名覆盖源图时目录 mtime 不变，
    # 只有文件自身 mtime 变，光看目录会漏判。
    newest = max((mt for _stem, mt in entries), default=0)
    sig = (raw_sig, img_sig, len(entries), newest)
    cached = _raw_cache.setdefault(lib, {})
    if cached.get("sig") == sig:
        return cached.get("pending", False)
    pending = False
    for stem, src_mt in entries:
        dst = img / f"{stem}.webp"
        try:
            if not dst.is_file() or src_mt > dst.stat().st_mtime_ns:
                pending = True
                break
        except OSError:
            pending = True
            break
    cached["sig"] = sig
    cached["pending"] = pending
    return pending


def index(lib: str = "pose"):
    """内置库 + 自定义库合并后的索引；自定义姿态排在最前面。"""
    # png/ 里有新图、或 img/ 被用户增删过：先自动转换/重建索引，再读
    if _raw_pending(lib) or _img_pending(lib):
        auto_build(lib)
    base = _builtin(lib)
    _scan_custom(lib)
    custom_poses = _custom_cache.setdefault(lib, {}).get("poses", [])
    if not custom_poses:
        return base
    merged = dict(base)
    merged["poses"] = list(custom_poses) + list(base["poses"])
    merged["series"] = (
        [
            {
                "key": CUSTOM_SERIES_KEY,
                "name": _custom_series_name(lib),
                "nameJp": _custom_series_name(lib),
                "short": CUSTOM_SERIES_SHORT,
                "count": len(custom_poses),
            }
        ]
        + list(base["series"])
    )
    merged["customCount"] = len(custom_poses)
    return merged


def pose_labels(lib: str = "pose"):
    """节点下拉框用的姿态名列表。"""
    return [pose["label"] for pose in index(lib)["poses"]]


def series_options(lib: str = "pose"):
    """系列下拉：全部 + 各系列（自定义系列排最前，按姿态数降序）。"""
    return [ALL] + [series["name"] for series in index(lib)["series"]]


def category_options(lib: str = "pose"):
    """分类下拉：全部 + 各分类。

    排序先按系列顺序、再按条目数降序 —— 服装库 19 个分类如果纯按数量排，
    连衣裙·迷你 会和半身裙·百褶 交错在一起，同一类型的归不到一块。
    """
    data = index(lib)
    order = {s["key"]: i for i, s in enumerate(data.get("series", []))}
    counts, series_of = {}, {}
    for pose in data["poses"]:
        cat = pose["cat"]
        counts[cat] = counts.get(cat, 0) + 1
        series_of[cat] = pose.get("series", "")
    return [ALL] + sorted(
        counts, key=lambda cat: (order.get(series_of.get(cat), 99), -counts[cat], cat)
    )


def angle_choices(lib: str = "pose"):
    """视角下拉：该库的角度标签；多视角库额外加「随机视角」。"""
    labels = list(_lib_cfg(lib)["angles"].values())
    if len(labels) > 1:
        labels = labels + [RANDOM_ANGLE]
    return labels


# 从显示名里抠编号：内置库的编号（SPR-0001 / LW-00012 …）是稳定 ID，不会随改名变。
# 纯字母数字加短横，够宽松，只在 labelOld 都对不上时才用。
_CODE_IN_LABEL = re.compile(r"([A-Z][A-Z0-9]{1,7}-\d{3,5})")


def find_pose(label, lib: str = "pose"):
    poses = index(lib)["poses"]
    for pose in poses:
        if pose["label"] == label:
            return pose
    # 兜底一：分类重排前把旧 label 存进了 labelOld，旧工作流里那个名字还能对上，
    # 运行一次就会按新 label 回传，工作流下次保存自动升级，不用手工重选。
    for pose in poses:
        if pose.get("labelOld") == label:
            return pose
    # 兜底二：改名改过不止一轮时，中间那版名字两头都不在（labelOld 只留最早一版）。
    # 编号是稳定 ID，从任意 label 里抠出 SPR-0001 这种串回查，改名多少次都不丢。
    match = _CODE_IN_LABEL.search(label or "")
    if match:
        code = match.group(1)
        for pose in poses:
            if pose.get("code") == code:
                return pose
    raise PoseDBMissing(
        f"库里没有「{label}」这一项。\n"
        "它可能已被删除或改名（自定义姿态的显示名就是文件名，改名后旧工作流里的名字会对不上）。"
        "请在节点里重新选一个姿态。"
    )


def series_key(name, lib: str = "pose"):
    for series in index(lib)["series"]:
        if series["name"] == name:
            return series["key"]
    return None


def pool(series_name=None, category=ALL, lib: str = "pose"):
    """范围内随机的候选集。

    分类在该系列里没有匹配时先退到「只按系列」，再空则退全库，
    避免用户选了空组合后节点直接报错。
    """
    poses = index(lib)["poses"]
    if not poses:
        raise PoseDBMissing(
            "姿态库是空的，没法抽图。\n"
            "可以在节点里点「导入」把自己的图放进来，"
            "或者把 pose-db-01 的图片复制到 poses/ 下再运行 tools/build_pose_db.py。"
        )
    key = None if series_name in (None, ALL) else series_key(series_name, lib)
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
    # 该库角度标签（如「正面」）必然在全局 ANGLE_LABELS 里，直接映射；映射不到则兜底正面
    return LABEL_TO_ANGLE.get(angle_label, "front")


def resolve(pose, angle_key):
    """返回 (姿态记录, 实际角度, 图片路径)。缺图时按 正面→其余角度 回退。"""
    lib = pose.get("lib", "pose")
    cfg = _lib_cfg(lib)
    custom = pose.get("root") == CUSTOM_SERIES_KEY
    base = cfg["custom"] if custom else cfg["img"]
    order = [angle_key, "front"] + [key for key in cfg["angles"] if key not in (angle_key, "front")]
    for key in order:
        entry = pose["angles"].get(key)
        if not entry:
            continue
        path = base / entry["img"]
        if path.is_file():
            return pose, key, path
    folder = f"poses/{lib}/custom" if custom else f"poses/{lib}"
    raise FileNotFoundError(
        f"姿态图文件缺失：{pose['no']}（找过 {angle_key}、正面等角度）。\n"
        f"请确认 {folder} 里的原图还在；内置库重新复制后要再跑一次对应的 build 脚本。"
    )
