"""把 faces/png/ 下的原始图（默认 PNG）转成 WebP，并生成 faces/index.json。

「GG 脸模库」节点只认 WebP + index.json。用户把脸模图丢进 faces/png/（也兼容 faces/ 与 faces/img/）后，
本脚本会：①非 WebP 的图统一转成 WebP（quality 95，保持原尺寸）②以 img/ 下现有 WebP 建索引。
ComfyUI 启动、索引缺失时也会自动跑同一套逻辑，所以不跑本脚本、只重启也能用。

用法：
    python tools/build_face_db.py            # 转换并建索引，保留原始 PNG
    python tools/build_face_db.py --clean    # 转换后删掉已转好的原始 PNG，给仓库瘦身
"""

import argparse
import sys
from pathlib import Path

NODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(NODE_DIR))

import pose_db  # noqa: E402

FACE_DIR = NODE_DIR / "faces"
RAW_DIR = FACE_DIR / pose_db.RAW_SUBDIR  # faces/png/
IMG_DIR = FACE_DIR / "img"
INDEX_FILE = FACE_DIR / "index.json"

# 与 pose_db 保持一致：这些后缀都算可转换的源图（webp 不再转）
SRC_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _webp_count() -> int:
    return len(list(IMG_DIR.glob("*.webp"))) if IMG_DIR.is_dir() else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="把 faces/png/ 原始图转成 WebP 并生成脸模库索引")
    ap.add_argument("--clean", action="store_true", help="转换成功后删除原始 PNG（默认保留）")
    args = ap.parse_args()

    before = _webp_count()
    pose_db.auto_build("face")
    after = _webp_count()

    index = pose_db.index("face")
    total = len(index["poses"])
    if total == 0:
        print(f"faces/png/ 里没找到可用的图片。把 PNG 放进来再跑一次：{RAW_DIR}")
        return

    print(f"已写入 {INDEX_FILE}")
    print(f"脸模 {total} 张（本次新转 {after - before} 张 WebP，img/ 共 {after} 张）")

    if args.clean:
        removed = 0
        # 原始图默认在 faces/png/，也兼容仍留在 faces/ 根目录的情况
        for folder in (RAW_DIR, FACE_DIR):
            if not folder.is_dir():
                continue
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in SRC_EXTS:
                    if (IMG_DIR / f"{p.stem}.webp").is_file():
                        p.unlink()
                        removed += 1
        print(f"已删除原始图 {removed} 张（保留 WebP）")


if __name__ == "__main__":
    main()
