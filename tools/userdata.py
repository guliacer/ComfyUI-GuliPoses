"""用户素材（自己导入的图 / 自己丢的原始图）的查看、迁移与备份。

节点的内置图库（`poses/img`、`garment/img`、`faces/img`）随仓库分发，升级时被覆盖是正常的。
**用户自己放的东西**从 v1.2.2 起全部落在插件目录外面：

    ComfyUI/user/default/guliposes/<lib>/custom/    节点里点「导入」落盘的图 + meta.json
    ComfyUI/user/default/guliposes/<lib>/png/       自己丢进去的原始图（auto_build 会转 WebP）

插件升级（git pull / 删掉重装 / 整目录覆盖）不会碰到这两个目录。

用法（必须用 ComfyUI 自带的 python，脚本依赖插件本身）：

    python tools/userdata.py info                        # 看现在数据在哪、各库有多少文件
    python tools/userdata.py migrate                     # 把老位置（插件内 custom/、png/）复制过来
    python tools/userdata.py move                        # 同上，但复制成功后删掉插件内的原件
    python tools/userdata.py backup                      # 打 zip 到用户目录旁边
    python tools/userdata.py backup --out D:/gg-backup.zip
"""

import argparse
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pose_db  # noqa: E402


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _scan(root: Path) -> tuple[int, int]:
    """(图片数, 图片总字节)。只算图片：meta.json、说明文件不该被当成"我有几张图"。"""
    if not root.is_dir():
        return 0, 0
    files = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in pose_db.IMAGE_EXTS and "thumbs" not in p.parts
    ]
    return len(files), sum(p.stat().st_size for p in files)


def cmd_info(_args) -> None:
    print(f"用户数据根目录：{pose_db.USER_DATA_ROOT}")
    print(f"  存在：{'是' if pose_db.USER_DATA_ROOT.is_dir() else '否（首次启动时自动创建）'}")
    print()
    for lib in pose_db.LIB_DIRS:
        custom = pose_db.custom_dir(lib)
        raw = pose_db.raw_dir(lib)
        cn, cb = _scan(custom)
        rn, rb = _scan(raw)
        print(f"[{lib}]")
        print(f"  导入的图  {custom}  {cn} 个 / {_human(cb)}")
        print(f"  原始图    {raw}  {rn} 个 / {_human(rb)}")
        legacy_root = pose_db.LIB_DIRS[lib]["index"].parent
        for legacy in (legacy_root / "custom", legacy_root / pose_db.RAW_SUBDIR):
            ln, lb = _scan(legacy)
            if ln:
                print(f"  ! 老位置还有 {ln} 个 / {_human(lb)}：{legacy}")
                print("    跑 `python tools/userdata.py migrate` 搬过来（只复制，不动原件）")
    print()
    print(f"插件里随仓库分发的内置图（升级会覆盖，属正常）：{pose_db.NODE_DIR}")


def cmd_migrate(args) -> None:
    pose_db.USER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    moved = pose_db.migrate_legacy_userdata(move=args.move)
    if not moved:
        print("插件目录里没有需要搬的用户素材。")
    else:
        verb = "移动" if args.move else "复制"
        print(f"已{verb} {len(moved)} 个文件到 {pose_db.USER_DATA_ROOT}")
        for item in moved[:20]:
            print(f"  {item}")
        if len(moved) > 20:
            print(f"  … 还有 {len(moved) - 20} 个")
        if not args.move:
            print("\n插件内原文件仍在。确认没问题后可以跑 `python tools/userdata.py move` 收尾，")
            print("或者手动删掉插件里的 custom/ 与 png/ —— 那两个目录以后不再被读取。")


def cmd_backup(args) -> None:
    src = pose_db.USER_DATA_ROOT
    if not src.is_dir():
        raise SystemExit(f"用户数据目录还不存在：{src}")
    if args.out:
        dst = Path(args.out).expanduser()
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dst = src.parent / f"guliposes-userdata-{stamp}.zip"
    dst.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())
                count += 1
    size = dst.stat().st_size
    print(f"已备份 {count} 个文件 → {dst}（{_human(size)}）")
    print("升级节点前跑一次，出事直接解压覆盖回用户数据目录即可。")


def cmd_prune(args) -> None:
    """清掉 custom/thumbs/ 里没有对应原图的缩略图（删图时留下、或手动删文件留下的死链）。"""
    removed = 0
    for lib in pose_db.LIB_DIRS:
        custom = pose_db.custom_dir(lib)
        if not custom.is_dir():
            continue
        stems = {
            p.stem for p in custom.iterdir() if p.is_file() and p.suffix.lower() in pose_db.IMAGE_EXTS
        }
        thumbs = custom / "thumbs"
        if not thumbs.is_dir():
            continue
        for path in sorted(thumbs.iterdir()):
            if not path.is_file():
                continue
            # 缩略图叫 "<原文件名>.jpg"，重名时是 "名字 (2).jpg"
            if path.stem.split(" (")[0] in stems:
                continue
            print(f"  {lib}: 孤儿缩略图 {path.name}")
            removed += 1
            if args.apply:
                try:
                    path.unlink()
                except OSError as err:
                    print(f"    删不掉：{err}")
    if not removed:
        print("没有孤儿缩略图。")
    elif not args.apply:
        print(f"共 {removed} 个，加 --apply 才真删。")
    else:
        print(f"已删 {removed} 个。")


def main() -> None:
    parser = argparse.ArgumentParser(description="GG 图库 · 用户素材管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="查看用户素材在哪、有多少").set_defaults(func=cmd_info)

    p_mig = sub.add_parser("migrate", help="把插件内老位置的素材复制到用户目录")
    p_mig.add_argument("--move", action="store_true", help="复制后删掉插件内的原件")
    p_mig.set_defaults(func=cmd_migrate)

    p_bak = sub.add_parser("backup", help="把用户素材打包成 zip")
    p_bak.add_argument("--out", help="zip 输出路径（默认放在用户数据目录旁边）")
    p_bak.set_defaults(func=cmd_backup)

    p_prune = sub.add_parser("prune", help="清理没有原图的孤儿缩略图")
    p_prune.add_argument("--apply", action="store_true", help="真的删；不加只列出")
    p_prune.set_defaults(func=cmd_prune)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
