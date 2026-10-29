"""把内置图库的 PNG 转成 WebP，体积降到原来的 1/5 左右。

为什么要这一步：1439 张 900×1200 的 PNG 一共 343 MB，走 git 推送和 clone 都太慢。
白模线稿是白底黑线的低熵图，PNG 的调色板压缩在这里效率很差，WebP 用同样的观感
只要 40~60 MB。实测 q95 平均 PSNR 50.9 dB，肉眼看不出差别。

用法：
    python tools/optimize_library.py --dry-run     # 只估算，不写文件
    python tools/optimize_library.py               # 转换（默认保留原 PNG）
    python tools/optimize_library.py --remove-png  # 转换后删掉 PNG

转换完记得重建索引：python tools/build_pose_db.py <源库>
"""

from __future__ import annotations

import argparse
import io
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

DB_DIR = Path(__file__).resolve().parent.parent / "poses"
IMG_DIR = DB_DIR / "img"

# 白模图是白底线稿，先铺白再编码，避免某些图带透明通道时背景变黑
BACKDROP = (255, 255, 255)


def flatten(path: Path) -> Image.Image:
    """读图并铺白底，统一成 RGB。"""
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            flat = Image.new("RGB", rgba.size, BACKDROP)
            flat.paste(rgba, mask=rgba.split()[-1])
            return flat
        return im.convert("RGB")


def convert_one(job: tuple[str, int, int]) -> tuple[str, int, int, str]:
    """单张转换，返回 (文件名, 原大小, 新大小, 错误)。"""
    name, quality, method = job
    src = IMG_DIR / name
    dst = src.with_suffix(".webp")
    try:
        before = src.stat().st_size
        if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime:
            return name, before, dst.stat().st_size, ""  # 已经转过了
        im = flatten(src)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=quality, method=method)
        # 先写临时文件再原子替换：中途失败不会留下半张图
        tmp = dst.with_suffix(".webp.tmp")
        tmp.write_bytes(buf.getvalue())
        tmp.replace(dst)
        return name, before, dst.stat().st_size, ""
    except Exception as exc:  # noqa: BLE001 - 单张失败不该中断整批
        return name, 0, 0, f"{type(exc).__name__}: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description="把内置图库的 PNG 转成 WebP")
    ap.add_argument("--quality", type=int, default=95, help="WebP 质量，默认 95（实测 PSNR 约 51 dB）")
    ap.add_argument("--method", type=int, default=4, help="WebP 编码强度 0-6，越大越慢越小，默认 4")
    ap.add_argument("--workers", type=int, default=0, help="并行进程数，默认 CPU 核数")
    ap.add_argument("--remove-png", action="store_true", help="转换成功后删除原 PNG")
    ap.add_argument("--dry-run", action="store_true", help="只统计体积，不写文件")
    args = ap.parse_args()

    if not IMG_DIR.is_dir():
        print(f"找不到 {IMG_DIR}", file=sys.stderr)
        return 1

    sources = sorted(p for p in IMG_DIR.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if not sources:
        print(f"{IMG_DIR} 里没有可转换的图片", file=sys.stderr)
        return 1

    before_total = sum(p.stat().st_size for p in sources)
    print(f"待转换 {len(sources)} 张，原始 {before_total / 1048576:.1f} MB")

    if args.dry_run:
        sample = sources[:8]
        est = 0
        for p in sample:
            im = flatten(p)
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=args.quality, method=args.method)
            est += buf.tell()
        ratio = est / sum(p.stat().st_size for p in sample)
        print(f"抽样 {len(sample)} 张：预计 {before_total * ratio / 1048576:.1f} MB（{ratio * 100:.0f}%）")
        return 0

    workers = args.workers or None
    jobs = [(p.name, args.quality, args.method) for p in sources]
    after_total = 0
    failures: list[tuple[str, str]] = []
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for name, before, after, err in pool.map(convert_one, jobs, chunksize=16):
            done += 1
            if err:
                failures.append((name, err))
                after_total += before
            else:
                after_total += after
            if done % 200 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}  当前 {after_total / 1048576:.1f} MB", flush=True)

    saved = before_total - after_total
    print(f"完成：{before_total / 1048576:.1f} MB → {after_total / 1048576:.1f} MB"
          f"（省 {saved / 1048576:.1f} MB / {saved / before_total * 100:.0f}%）")

    if failures:
        print(f"失败 {len(failures)} 张：", file=sys.stderr)
        for name, err in failures[:10]:
            print(f"  {name}: {err}", file=sys.stderr)
        return 2

    if args.remove_png:
        removed = 0
        for p in sources:
            if p.with_suffix(".webp").is_file():
                p.unlink()
                removed += 1
        print(f"已删除 {removed} 个原 PNG")
    else:
        print("原 PNG 保留；确认无误后可加 --remove-png 删除，或手动删")

    print("\n下一步：python tools/build_pose_db.py <源库路径> 重建索引")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
