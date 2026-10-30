# 节点截图工具

README 顶部那三张轮播图（`docs/screenshots/`）不是手工截的，用这两个脚本重拍，界面改了重跑一遍就行。

```bash
# 一次性：装无头浏览器驱动（不装浏览器本体，用本机已有的 chromium）
npm i playwright-core

# 前提：ComfyUI 已经在跑（默认 http://127.0.0.1:8188）
node tools/screenshot/shoot.mjs GuliPosePicker    docs/screenshots/node-pose.png    620 940
node tools/screenshot/shoot.mjs GuliGarmentPicker docs/screenshots/node-garment.png 620 900
node tools/screenshot/shoot.mjs GuliFacePicker    docs/screenshots/node-face.png    620 900

# 裁掉节点底部那块为输出槽预留的空白，再压到 1000px 宽
python tools/screenshot/trim.py docs/screenshots/node-pose.png docs/screenshots/node-garment.png docs/screenshots/node-face.png
```

`shoot.mjs` 里踩过的三个坑都写在注释里，别随手删：

- 节点宽度由画廊 widget 的 `computeSize` 决定（默认 210），要顶到目标宽度才是宽面板；
- 节点 y 坐标小于 ~110 会被 ComfyUI 顶部菜单压住；
- 无头页面久不活动会弹 Reconnecting，拍照前要藏掉。

`trim.py` 只处理底部：节点下方那块空白是给输出槽预留的，跟着节点高度走，固定裁多少都不对，所以按「最后一行非白像素」算。
