"""裁掉节点内部底部的纯白空白：从底部往上找最后一行「有像素不是白色」的内容。

用法：python tools/screenshot/trim.py docs/screenshots/node-pose.png
"""
import sys
from pathlib import Path
from PIL import Image

WHITE = 252
NEED = 0.01   # 一行里有 1% 非白像素就算「有内容」

def nonwhite_ratio(im, y):
    w = im.size[0]
    step = max(1, w // 400)
    xs = list(range(int(w * 0.12), int(w * 0.88), step))
    hit = sum(1 for x in xs if min(im.getpixel((x, y))) < WHITE)
    return hit / len(xs)

def trim(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    y = h - 1
    while y > h // 3 and nonwhite_ratio(im, y) < NEED:
        y -= 1
    cut = min(h, y + 16)
    if cut >= h - 6:
        print(f"{Path(path).name}: 底部无空白（{h}px）")
        return
    im.crop((0, 0, w, cut)).save(path, optimize=True)
    print(f"{Path(path).name}: 高 {h} -> {cut}（裁掉 {h - cut}px）")

for p in sys.argv[1:]:
    trim(p)
