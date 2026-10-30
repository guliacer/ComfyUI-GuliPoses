# 这个目录已经搬家了

从 v1.2.2 起，脸模原图**不再放这里**。往这里丢图不会被读取，升级节点时还会被覆盖。

新的位置（在插件外面，升级不会碰）：

    ComfyUI/user/default/guliposes/face/png/

想换到别的盘，设环境变量 `GULIPOSES_DATA_DIR` 指过去即可。

节点里点「导入」放进去的图同样在插件外面：

    ComfyUI/user/default/guliposes/face/custom/

老版本留在这个目录里的图，启动时会自动复制到新位置（原件保留）。
也可以手动搬（用 ComfyUI 自带的 python）：

    python tools/userdata.py info      # 看两个位置各有几张
    python tools/userdata.py migrate   # 复制到新位置（不动原件）
    python tools/userdata.py move      # 复制完再删原件
