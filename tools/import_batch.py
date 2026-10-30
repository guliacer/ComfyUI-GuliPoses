"""批量把图灌进某个库的自定义系列（不用一张张点「导入」）。

节点里的「导入」适合几张图；整包几百张的时候用这个，或者更省事——直接把包丢进
插件根目录的 `inbox/<lib>/`，重启 ComfyUI 就自动入库。

用法（用 ComfyUI 自带的 python 跑，脚本依赖插件本身）：

    python tools/import_batch.py "D:\\图包"              --lib garment
    python tools/import_batch.py "D:\\图包.zip"          --lib pose
    python tools/import_batch.py "D:\\a.png" "D:\\b.png" --lib face
    python tools/import_batch.py --scan                  # 结算 inbox/ 里的所有东西

认：单张图片、文件夹（递归找图）、zip 压缩包。
文件名带视角后缀会自动识别，多视角合成同一个姿态：
    姿势A_front.png + 姿势A_side.png → 「姿势A」两个视角
支持 front / side / high / low / diag，或 正面 / 侧面 / 俯视 / 仰视 / 斜侧。

不会覆盖已有图：重名自动加 (2)。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pose_db  # noqa: E402

LIBS = {"pose": "姿态库", "garment": "服装库", "face": "脸模库"}


def collect(paths: list[str]) -> list[tuple[str, bytes]]:
    """把命令行给的路径摊平成 [(文件名, bytes)]。目录递归、zip 内联解。"""
    items = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            for sub in sorted(path.rglob("*")):
                if sub.is_file():
                    items.extend(_one(sub))
        elif path.is_file():
            items.extend(_one(path))
        else:
            print(f"  跳过（不存在）：{path}")
    return items


def _one(path: Path) -> list[tuple[str, bytes]]:
    suffix = path.suffix.lower()
    if suffix in pose_db.IMAGE_EXTS:
        size = path.stat().st_size
        if size > pose_db.MAX_INBOX_FILE:
            print(f"  跳过（超过 {pose_db.MAX_INBOX_FILE // 1024 // 1024} MB）：{path.name}")
            return []
        return [(path.name, path.read_bytes())]
    if suffix == ".zip":
        try:
            return pose_db._images_in_zip(path.read_bytes())
        except Exception as err:
            print(f"  解不开的压缩包 {path.name}：{err}")
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="GG 图库 · 批量导入")
    parser.add_argument("paths", nargs="*", help="图片 / 文件夹 / zip，可以给多个")
    parser.add_argument("--lib", default="pose", choices=list(LIBS), help="进哪个库（默认姿态库）")
    parser.add_argument("--cat", default=None, help="分类名，默认「自定义」")
    parser.add_argument("--scan", action="store_true", help="结算 inbox/ 收件箱，忽略 paths")
    args = parser.parse_args()

    if args.scan:
        drained = pose_db.drain_all_inboxes()
        if not drained:
            print("收件箱是空的（inbox/<lib>/ 里没有图片或 zip）")
            return
        for lib, names in drained.items():
            print(f"{LIBS.get(lib, lib)}：入库 {len(names)} 张")
            for name in names[:10]:
                print(f"  {name}")
            if len(names) > 10:
                print(f"  … 还有 {len(names) - 10} 张")
        print(f"\n文件已搬到 {pose_db.USER_DATA_ROOT}")
        return

    if not args.paths:
        parser.error("给个路径，或者用 --scan 结算收件箱")

    items = collect(args.paths)
    if not items:
        print("没找到可导入的图片（认 PNG / JPG / JPEG / WEBP / BMP 和 zip）")
        return

    print(f"准备导入 {len(items)} 张 → {LIBS[args.lib]}")
    saved = pose_db._import_batch(args.lib, items, args.cat)
    print(f"已入库 {len(saved)} 张到 {pose_db.custom_dir(args.lib)}")
    for name in saved[:10]:
        print(f"  {name}")
    if len(saved) > 10:
        print(f"  … 还有 {len(saved) - 10} 张")
    print("\n刷新一下页面就能在画廊「我的」系列里看到；单角度库按正面入库，多视角靠文件名后缀识别。")


if __name__ == "__main__":
    main()
