把图包丢在这里，重启 ComfyUI 就自动进库
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

    python tools/import_batch.py "D:\图包" --lib garment
    python tools/import_batch.py "D:\图包.zip" --lib pose
