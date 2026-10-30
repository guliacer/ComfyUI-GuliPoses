"""升级器：先把用户素材搬到插件外面，再全量替换插件目录。

为什么需要它
------------
插件目录里从来只有两种东西：**随仓库分发的内置素材**（`poses|garment|faces/img`、
`thumbs`、`index.json`）和**用户自己的东西**（`custom/`、`png/`、收件箱里的图包）。
前者升级时被覆盖是正常的；后者一旦跟着目录被盖掉就找不回来了。
"删文件夹重新解压"这种全量升级，会在解压那一刻直接把后者抹掉——事后任何补救都来不及。

所以顺序必须是：**先搬出去，再覆盖**。这个脚本就干这件事：

    check      体检：老位置还有多少用户素材、收件箱有没有没结算的图包
    protect    复制到 user 区 + 打快照 zip + 结算收件箱（不动原件，可反复跑）
    protect --purge   同上，复制校验通过后删掉插件内的原件，插件目录变干净
    full --from <zip|目录>    protect + 全量替换插件目录 + 逐文件校验

用户素材的落点（插件外面，升级碰不到）：

    ComfyUI/user/default/guliposes/<lib>/custom/     导入的图 + meta.json + thumbs/
    ComfyUI/user/default/guliposes/<lib>/png/        自己丢的原始图（auto_build 会转 WebP）
    ComfyUI/user/default/guliposes/_backup/*.zip     每次升级前的素材快照

用法（必须用 ComfyUI 自带的 python，脚本依赖插件本身）：

    python tools/upgrade.py check
    python tools/upgrade.py protect
    python tools/upgrade.py full --from D:/pkg/ComfyUI-GuliPoses-v1.2.3.zip
    python tools/upgrade.py full --from D:/pkg/ComfyUI-GuliPoses-v1.2.3.zip --purge
    python tools/upgrade.py full --from ... --dry-run      # 只列会删/会写哪些文件
"""

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pose_db  # noqa: E402

NODE_DIR = pose_db.NODE_DIR
BACKUP_DIR = pose_db.USER_DATA_ROOT / "_backup"

# 全量替换时**永不删除**的顶层项。.git 是版本库本身；.workbuddy 是项目记忆；
# inbox 里是用户还没结算的图包（结算过的已经搬到 user 区，剩下的属于用户）；
# dist / _release 放发行包，不该被当插件内容删掉。
KEEP_TOP = {".git", ".workbuddy", "inbox", "__pycache__", ".idea", ".vscode", "dist", "_release"}


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _legacy_targets() -> list[tuple[str, Path, Path]]:
    """[(lib, 插件内的老目录, 用户区对应的目录)]，覆盖 custom/ 与 png/ 两类。"""
    out = []
    for lib in pose_db.LIB_DIRS:
        root = pose_db.LIB_DIRS[lib]["index"].parent
        out.append((lib, root / "custom", pose_db.custom_dir(lib)))
        out.append((lib, root / pose_db.RAW_SUBDIR, pose_db.raw_dir(lib)))
    return out


def _material(root: Path):
    """老目录里算"用户素材"的文件：图片 + meta.json。thumbs/ 是派生物，不搬。"""
    if not root.is_dir():
        return []
    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if "thumbs" in rel.parts:
            continue
        if path.suffix.lower() in pose_db.IMAGE_EXTS or path.name == "meta.json":
            out.append((rel, path))
    return out


def _pending_inbox() -> list[tuple[str, Path]]:
    """收件箱里还没结算的东西（非说明文件）。"""
    out = []
    for lib in pose_db.LIB_DIRS:
        for box in pose_db._inbox_roots():
            folder = box / lib
            if not folder.is_dir():
                continue
            for path in sorted(folder.rglob("*")):
                if path.is_file() and not path.name.startswith("说明"):
                    out.append((lib, path))
    return out


def _snapshot(tag: str = "upgrade") -> Path:
    """把用户区 + 插件内老位置的全部素材打成一个 zip。失败也不阻断升级（只警告）。"""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dst = BACKUP_DIR / f"{tag}-{stamp}.zip"
    count = 0
    try:
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            if pose_db.USER_DATA_ROOT.is_dir():
                for path in sorted(pose_db.USER_DATA_ROOT.rglob("*")):
                    if path.is_file() and BACKUP_DIR not in path.parents:
                        zf.write(path, f"user/{path.relative_to(pose_db.USER_DATA_ROOT).as_posix()}")
                        count += 1
            for lib, legacy, _target in _legacy_targets():
                for rel, path in _material(legacy):
                    zf.write(path, f"legacy/{lib}/{legacy.name}/{rel.as_posix()}")
                    count += 1
    except OSError as err:
        print(f"  ! 快照失败（继续升级）：{err}")
        return dst
    print(f"  快照：{count} 个文件 → {dst}（{_human(dst.stat().st_size)}）")
    return dst


def _user_hashes() -> dict[str, str]:
    """用户区素材的 {lib/种类/相对路径: sha256}。meta.json 不算（合并后本来就不同）。"""
    out = {}
    for lib in pose_db.LIB_DIRS:
        for kind, root in (("custom", pose_db.custom_dir(lib)), ("png", pose_db.raw_dir(lib))):
            for rel, path in _material(root):
                if path.name == "meta.json":
                    continue
                out[f"{lib}/{kind}/{rel.as_posix()}"] = _sha(path)
    return out


def cmd_check() -> None:
    print(f"插件目录：{NODE_DIR}")
    print(f"用户数据：{pose_db.USER_DATA_ROOT}")
    print()
    risky = 0
    for lib, legacy, target in _legacy_targets():
        items = _material(legacy)
        imgs = [p for _r, p in items if p.suffix.lower() in pose_db.IMAGE_EXTS]
        if not imgs:
            # 只剩一份空 meta.json 的老目录不算风险，覆盖掉也没内容可丢
            continue
        size = sum(p.stat().st_size for p in imgs)
        print(f"! [{lib}] 插件内还有 {len(imgs)} 张用户图 / {_human(size)}：{legacy}")
        print(f"    升级会覆盖这个目录 → 目标 {target}")
        risky += len(imgs)
    for lib in pose_db.LIB_DIRS:
        n = len([1 for _r, p in _material(pose_db.custom_dir(lib)) if p.suffix.lower() in pose_db.IMAGE_EXTS])
        r = len([1 for _r, p in _material(pose_db.raw_dir(lib)) if p.suffix.lower() in pose_db.IMAGE_EXTS])
        print(f"  [{lib}] 用户区已有：导入 {n} 张 / 原始 {r} 张")
    inbox = _pending_inbox()
    if inbox:
        print()
        print(f"! 收件箱还有 {len(inbox)} 个没结算的文件（升级会随 inbox/ 一起被覆盖）：")
        for lib, path in inbox[:10]:
            print(f"    {lib}: {path.name}")
        if len(inbox) > 10:
            print(f"    … 还有 {len(inbox) - 10} 个")
    print()
    if risky or inbox:
        print(f"结论：有 {risky} 张图 + {len(inbox)} 个收件箱文件处在危险位置。")
        print("      先跑 `python tools/upgrade.py protect`，再做全量升级。")
    else:
        print("结论：插件目录里没有用户素材，可以直接全量升级。")


def cmd_protect(purge: bool = False) -> dict[str, str]:
    print("== 1/4 打快照")
    _snapshot("pre-upgrade")

    print("== 2/4 把插件内的用户素材搬到 user 区")
    pose_db.USER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    moved = pose_db.migrate_legacy_userdata(move=purge)
    if moved:
        for item in moved[:20]:
            print(f"  {item}")
        if len(moved) > 20:
            print(f"  … 还有 {len(moved) - 20} 个")
    else:
        legacy_left = sum(len([1 for _r, p in _material(legacy) if p.suffix.lower() in pose_db.IMAGE_EXTS])
                          for _lib, legacy, _t in _legacy_targets())
        if legacy_left:
            print(f"  不用重复搬：老位置那 {legacy_left} 张图 user 区已有同字节副本")
            print("  （原件还在插件里，加 --purge 会删掉它们）")
        else:
            print("  没有需要搬的（老位置本来就是空的）")

    print("== 3/4 结算收件箱（里面的图包也是用户数据）")
    try:
        drained = pose_db.drain_all_inboxes()
    except Exception as err:  # 单个图包坏了不该拦住整个升级
        print(f"  ! 收件箱结算出错（继续）：{err}")
        drained = {}
    if drained:
        for lib, names in drained.items():
            print(f"  {lib}: 入库 {len(names)} 张")
    else:
        print("  收件箱是空的")

    print("== 4/4 校验")
    hashes = _user_hashes()
    missing, diff = [], []
    for lib, legacy, target in _legacy_targets():
        for rel, path in _material(legacy):
            dest = target / rel
            if not dest.is_file():
                missing.append(f"{lib}/{legacy.name}/{rel.as_posix()}")
            elif path.name != "meta.json" and _sha(dest) != _sha(path):
                diff.append(f"{lib}/{legacy.name}/{rel.as_posix()}")
    if missing or diff:
        print(f"  ! 没落地 {len(missing)} 个、内容不一致 {len(diff)} 个：")
        for item in (missing + diff)[:15]:
            print(f"    {item}")
        if purge:
            print("  已拒绝删除原件（--purge 没生效）。请先解决上面的差异。")
            purge = False
    else:
        print(f"  用户区共 {len(hashes)} 个素材文件，插件内老位置全部已落地且字节一致")
    return {"purge_ok": purge, "hashes": hashes}


def _keep_rel(rel: str) -> bool:
    parts = rel.split("/")
    top = parts[0]
    # .workbuddy 与 .workbuddy-ai 都是开发期的项目记忆 / 备份，不属于发行内容，也不该被清掉
    return top in KEEP_TOP or top.startswith(".workbuddy") or rel.endswith(".pyc")


def _extract(src: Path, workdir: Path) -> Path:
    """把 --from 的参数变成"含插件文件的目录"。zip 会解到临时目录并自动下钻单层。"""
    if src.is_dir():
        return src
    if not src.is_file():
        raise SystemExit(f"找不到来源：{src}")
    print(f"  解包 {src.name} → {workdir}")
    with zipfile.ZipFile(src) as zf:
        for info in zf.infolist():
            target = (workdir / info.filename).resolve()
            if not str(target).startswith(str(workdir.resolve())):
                raise SystemExit(f"压缩包里有越界路径，拒绝解包：{info.filename}")
        zf.extractall(workdir)
    # 顶层如果只有一个文件夹（github zip 常见），钻进去
    entries = [p for p in workdir.iterdir() if p.name not in {"__MACOSX"}]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return workdir


def cmd_full(src: Path, purge: bool, dry: bool) -> None:
    if dry and purge:
        print("（--dry-run 时不执行 --purge，原件保留）")
        purge = False
    print("### 阶段 A：先把用户素材搬出去")
    state = cmd_protect(purge=purge)
    print()

    print("### 阶段 B：全量替换插件目录")
    tmp = None
    try:
        if not src.is_dir():
            tmp = Path(tempfile.mkdtemp(prefix="gg-upgrade-"))
        payload = _extract(src, tmp) if tmp else src
        files = {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()}
        if "pose_db.py" not in files or "__init__.py" not in files:
            raise SystemExit("来源里没有 pose_db.py / __init__.py，看起来不是插件目录，已中止")
        print(f"  来源 {payload}：{len(files)} 个文件")

        # 1) 删掉新版本里没有的文件（旧脚本、废弃目录、老位置残留）
        removed = []
        for path in sorted(NODE_DIR.rglob("*"), reverse=True):
            rel = path.relative_to(NODE_DIR).as_posix()
            if _keep_rel(rel):
                continue
            if path.is_file() and rel not in files:
                removed.append(rel)
                if not dry:
                    path.unlink()
            elif path.is_dir():
                try:
                    if not any(path.iterdir()):
                        path.rmdir()
                except OSError:
                    pass
        print(f"  删除旧版本多余文件：{len(removed)} 个")
        for rel in removed[:10]:
            print(f"    - {rel}")
        if len(removed) > 10:
            print(f"    … 还有 {len(removed) - 10} 个")

        # 2) 铺新版本（覆盖同名、补齐新增）
        written = 0
        for rel in sorted(files):
            s = payload / rel
            d = NODE_DIR / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            if dry:
                written += 1
                continue
            shutil.copy2(s, d)
            written += 1
        print(f"  {'（dry-run 未写盘）' if dry else '写入'}文件：{written} 个")
    finally:
        if tmp and tmp.is_dir():
            shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("### 阶段 C：校验")
    after = _user_hashes()
    before = state.get("hashes") or {}
    lost = [k for k in before if k not in after]
    changed = [k for k in before if k in after and before[k] != after[k]]
    print(f"  用户区素材：{len(after)} 个（替换前 {len(before)} 个）")
    if lost or changed:
        print(f"  ! 丢失 {len(lost)} 个、被改动 {len(changed)} 个：")
        for item in (lost + changed)[:15]:
            print(f"    {item}")
    else:
        print("  逐个 sha256 比对：0 丢失、0 改动")
    if state.get("purge_ok"):
        print("  插件内老位置已清空（--purge 生效），以后覆盖不会有残留")
    print()
    print("完成。以下两点自己确认一下：")
    print(f"  1. 素材在 {pose_db.USER_DATA_ROOT}（插件外面，怎么升级都碰不到）")
    print(f"  2. 回滚用 {BACKUP_DIR} 里的 zip，解压覆盖回用户数据目录即可")


def main() -> None:
    parser = argparse.ArgumentParser(description="GG 图库 · 升级器（先搬素材再全量替换）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="体检：老位置还有多少用户素材、收件箱有没有没结算的")

    p = sub.add_parser("protect", help="把插件内的用户素材复制到 user 区 + 打快照")
    p.add_argument("--purge", action="store_true", help="校验通过后删掉插件内的原件")

    p = sub.add_parser("full", help="保护 + 用新版全量替换插件目录")
    p.add_argument("--from", dest="src", required=True, help="新版 zip 或新版插件目录")
    p.add_argument("--purge", action="store_true", help="同时清掉插件内的老素材原件")
    p.add_argument("--dry-run", action="store_true", help="只列会删 / 会写哪些文件，不落盘")

    args = parser.parse_args()
    if args.cmd == "check":
        cmd_check()
    elif args.cmd == "protect":
        cmd_protect(purge=args.purge)
    else:
        cmd_full(Path(args.src).expanduser(), purge=args.purge, dry=args.dry_run)


if __name__ == "__main__":
    main()
