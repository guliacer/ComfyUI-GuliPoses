"""打发行包：把插件目录压成一个可分发 / 可全量覆盖安装的 zip。

产物给两种人用：
  1. 用户升级 —— 不用 git，解压覆盖插件目录即可（配合 `tools/upgrade.py full --from` 先保护素材）；
  2. 版本留档 —— 每个版本一个 zip，出问题直接回退。

排除规则（都是不该分发的）：`.git/`、`.workbuddy/`、`__pycache__/`、`*.pyc`、
`userdata/`（老兜底目录）、`dist/`、`_release/`、`.tmp*`，以及**用户素材**——
`poses|garment|faces/{custom,png}/` 里的图片、`meta.json`、`thumbs/`（那是别人的私有数据，
打进包里既没用又占体积）。该目录里的 README / 说明文件保留，那是给用户看的引导。

用法：

    python tools/pack_release.py                          # → _release/ComfyUI-GuliPoses-v<版本>.zip
    python tools/pack_release.py --out D:/pkg/gg.zip       # 指定输出
    python tools/pack_release.py --deflate                 # 压缩（慢，代码文本能小一半）
    python tools/pack_release.py --list                    # 只列文件不出包
"""

import argparse
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pose_db  # noqa: E402

NODE_DIR = pose_db.NODE_DIR
PLUGIN_NAME = NODE_DIR.name

SKIP_TOP = {".git", "dist", "_release", "userdata"}
SKIP_FILES = {"MANIFEST.txt"}  # 包内清单是打出来的产物，下次打包不能再吃回去
USER_DIRS = {"custom", "png"}
LIB_ROOTS = {pose_db.LIB_DIRS[lib]["index"].parent.name for lib in pose_db.LIB_DIRS}


def _version() -> str:
    """从 __init__.py 抠 __version__，抠不到就标 dev（不阻断打包）。"""
    init = NODE_DIR / "__init__.py"
    try:
        for line in init.read_text(encoding="utf-8").splitlines():
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return "dev"


def _is_user_material(rel: str, path: Path) -> bool:
    """插件目录里的用户私有素材：<lib根>/custom|png/ 下的图、meta.json、thumbs/。"""
    parts = rel.split("/")
    if len(parts) < 3 or parts[0] not in LIB_ROOTS or parts[1] not in USER_DIRS:
        return False
    if "thumbs" in parts:
        return True
    if path.name == "meta.json":
        return True
    return path.suffix.lower() in pose_db.IMAGE_EXTS


def collect(verbose: bool = False) -> list[Path]:
    out = []
    for path in sorted(NODE_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(NODE_DIR).as_posix()
        parts = rel.split("/")
        # .workbuddy / .workbuddy-ai 是开发期的记忆与备份，.git 是版本库，都不该分发；
        # .gitignore 例外——它能告诉用户哪些是本地产物
        if parts[0].startswith(".") and parts[0] != ".gitignore":
            continue
        if parts[0] in SKIP_TOP or rel.endswith(".pyc") or path.name in SKIP_FILES:
            continue
        if _is_user_material(rel, path):
            continue
        out.append(path)
    if verbose:
        for path in out:
            try:
                print(f"  + {path.relative_to(NODE_DIR).as_posix()}")
            except OSError:  # 管道被 head 关掉时不用报错
                break
    return out


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def main() -> None:
    parser = argparse.ArgumentParser(description="GG 图库 · 打发行包")
    parser.add_argument("--out", help="输出 zip 路径（默认 _release/<插件名>-v<版本>.zip）")
    parser.add_argument("--deflate", action="store_true", help="用 deflate 压缩（默认仅存储，图已是 WebP）")
    parser.add_argument("--list", action="store_true", help="只列文件清单，不写盘")
    parser.add_argument("--manifest", action="store_true", help="在包内附 MANIFEST.txt 文件清单")
    args = parser.parse_args()

    version = _version()
    files = collect(verbose=args.list)
    total = sum(p.stat().st_size for p in files)
    print(f"{PLUGIN_NAME} v{version}：{len(files)} 个文件 / {_human(total)}")
    if args.list:
        return

    out = Path(args.out).expanduser() if args.out else NODE_DIR / "dist" / f"{PLUGIN_NAME}-v{version}.zip"
    out = out if out.is_absolute() else (NODE_DIR / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    mode = zipfile.ZIP_DEFLATED if args.deflate else zipfile.ZIP_STORED
    kwargs = {"compresslevel": 6} if args.deflate else {}
    manifest = [
        f"# {PLUGIN_NAME} v{version}",
        f"# built {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# {len(files)} files / {total} bytes",
        "",
    ]
    with zipfile.ZipFile(out, "w", mode, **kwargs) as zf:
        for path in files:
            rel = path.relative_to(NODE_DIR).as_posix()
            zf.write(path, f"{PLUGIN_NAME}/{rel}")
            manifest.append(rel)
        if args.manifest:
            zf.writestr(f"{PLUGIN_NAME}/MANIFEST.txt", "\n".join(manifest) + "\n")

    print(f"→ {out}（{_human(out.stat().st_size)}）")
    print()
    print("用户装法（不要直接删目录覆盖，先保护素材）：")
    print(f"  python tools/upgrade.py full --from {out.name} --purge")


if __name__ == "__main__":
    main()
