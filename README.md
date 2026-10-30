# ComfyUI-GuliPoses

<p align="center">
  <a href="docs/showcase.html"><img src="docs/screenshots/node-pose.png" alt="GG 姿态库" width="248"></a>
  <a href="docs/showcase.html"><img src="docs/screenshots/node-garment.png" alt="GG 服装库" width="248"></a>
  <a href="docs/showcase.html"><img src="docs/screenshots/node-face.jpg" alt="GG 脸模库" width="248"></a>
</p>

<p align="center"><sub>GG 姿态库 288 组 × 5 视角 ｜ GG 服装库 1405 套 ｜ GG 脸模库 44 张 —— <a href="docs/showcase.html">点图看全屏预览 ↗</a></sub></p>

[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom__nodes-4f8cff)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](#许可与免责)
[![Poses](https://img.shields.io/badge/姿态库-288%20组%20%C2%B7%201439%20张-ff6b6b)](#数据)
[![Garments](https://img.shields.io/badge/服装库-1405%20套%20%C2%B7%206%20类型-9b6bff)](#数据)
[![Faces](https://img.shields.io/badge/脸模库-44%20张%20%C2%B7%20单角度-22c55e)](#数据)

**在 ComfyUI 节点里翻参考图库，选好就出图。**

姿态 288 组 × 5 视角、服装 1405 套、脸模 44 张，画廊里翻选即出图，输出直接接 ControlNet / Depth / Lineart / IP-Adapter。

> 自己导入的图存在 `ComfyUI/user/default/guliposes/`，不在插件目录里，升级不会丢。

[English](README_EN.md) · 中文

---

## 特性

| 能力 | 说明 |
| --- | --- |
| 不出画布 | 缩略图栅格就在节点里，点一下即选中，列数随节点宽度伸缩 |
| 三种取图 | 固定选中精确复现，全库随机抽卡，范围内随机只在小范围里抽 |
| 随机看得见结果 | 执行后自动跳到真正抽中的姿态，满意就点缩略图锁定，不用记种子 |
| 导入自己的图 | 点「导入」、拖进面板或 `Ctrl+V`，可自定义名称 / 分类 / 视角 |
| 全中文 · 零依赖 | 参数、输出、分类、姿势名全中文；只用 ComfyUI 自带的 PIL / numpy / torch |

---

## 安装

```bash
cd ComfyUI/custom_nodes
git clone --depth 1 https://github.com/guliacer/ComfyUI-GuliPoses.git
```

没有 git 就下载 [Release 离线包](https://github.com/guliacer/ComfyUI-GuliPoses/releases/latest)（约 263 MB），解压到 `custom_nodes/`。

已有旧版、且插件目录里放了自己的图，**别直接删目录覆盖**，这样升级：

```bash
python tools/upgrade.py full --from ComfyUI-GuliPoses-v1.2.3.zip --purge
```

重启 ComfyUI → 画布右键 → **GuliPoses** → **GG 姿态库**。仓库自带全部图片（约 270 MB），clone 完即用，之后 `git pull` 只拉代码。

---

## 节点

三个节点结构一致，只有底层图库不同。参数名是中文，输出一张 `IMAGE`，分类都是 `GuliPoses`。

| 节点 | 节点 ID | 图库内容 | 视角 | 输出 |
| --- | --- | --- | --- | --- |
| GG 姿态库 | `GuliPosePicker` | 288 组姿态 × 5 视角（1439 张，4 系列 / 26 分类） | 正面 / 俯视 / 仰视 / 侧面 / 斜侧 / 随机 | `900×1200` |
| GG 服装库 | `GuliGarmentPicker` | 1405 套穿搭（6 类型 / 20 分类） | 正面（控件自动隐藏） | `1366×2048` |
| GG 脸模库 | `GuliFacePicker` | 44 张脸模，可自行扩充 | 正面（控件自动隐藏） | RGB |

### 通用参数

| 参数 | 生效模式 | 说明 |
| --- | --- | --- |
| 模式 | 全部 | 固定选中 / 全库随机 / 范围内随机 |
| 姿态 / 服装 / 脸模 | 固定选中 | 当前库的条目 |
| 视角 | 全部 | 姿态库 6 项；单角度库只有「正面」 |
| 筛选系列 | 范围内随机 | 全部 + 当前库的系列 |
| 筛选分类 | 范围内随机 | 全部 + 当前库的分类 |

- 没有 `seed`，节点不参与采样；参数跟着模式显隐，`widgets_values` 顺序不变。
- 节点高度由你定，拉高就多显示几行，切模式不会吸回去。
- 只输出一张图，编号 / 名称写在画廊徽标上。

### 各库差异

- **服装库**：按穿搭类型分六系列——半身裙 440 / 连衣裙 391 / 裤装 293 / 内衣·家居 200 / 上装 58 / 泳装 23，二级 20 分类。原季节留在 `season` 字段，搜索框能搜「春」「派对」与英文关键词（`pleated`、`denim`）。
- **脸模库**：默认 44 张，只挑了一部分做适配。要更多就把图片丢进用户数据区的 `face/png/`，加载时自动转 WebP 并重建索引。

---

## 取图模式

| 模式 | 从哪抽 | 用在哪 |
| --- | --- | --- |
| 固定选中 | 「姿态」+「视角」精确取图 | 想好要什么姿势，或复现某次结果 |
| 全库随机 | 全部 288 个姿态 | 批量探索、给一批图随机换姿势 |
| 范围内随机 | 「筛选系列」×「筛选分类」的交集 | 做某个题材的系列图，有变化又不跑题 |

- 全库随机时两个筛选参数被忽略，系列下拉变灰。
- 空组合不报错，但会**静默放宽**（先退到只按系列，再退到全库）；画廊底部「候选 N 个」就是真正会用的池子。
- 随机模式每次排队都重新抽（`IS_CHANGED`，不被缓存挡），固定选中正常走缓存。想留住结果就点那张缩略图，模式切回固定选中，姿态与视角一起写进工作流。

---

## 画廊

节点下半部分是自绘 DOM 画廊，从上到下六层：

| 层 | 内容 | 操作 |
| --- | --- | --- |
| 大图预览 | 当前选择，左下角徽标 `编号 · 分类 · 视角` | — |
| 视角栏 | 正面 / 俯视 / 仰视 / 侧面 / 斜侧 | 点一下整栅格跟着换视角 |
| 工具行 | 系列下拉 · 搜索框 · 「导入」 · 「随机」 | 筛选 / 检索 / 导入 / 在当前可见范围挑一个 |
| 缩略图栅格 | 列数随节点宽度自适应，末行单张自动均分 | 点一下即选中 |
| 页脚 | 左边候选数，右边当前模式 | — |
| 推荐行 | 一行小字指向 ComfyUI-GuliNodes | 点击打开仓库 |

- 「随机」是在**当前可见范围**里挑一个并切回固定选中，直接把那张图钉进工作流。
- 随机模式下预览图若不在当前候选里（比如刚改了筛选），图片会压暗、徽标变成「上次 · 」，那是上次结果不是出错。
- 姿态编号跨系列重复（`P001` 有四个系列各一份），所以下拉选项带系列前缀。

---

## 数据

**288 组姿态 × 5 视角 = 1439 张图**（`full_sexy_P018` 缺「仰视」，选到该角度回退正面）。

| 系列 | 姿态数 |
| --- | --- |
| 全身单人-性感系 | 80 |
| 上半身单人 | 80 |
| 全身单人-标准系 | 73 |
| 双人互动 | 55 |

26 个动作分类（站姿 / 趴卧 / 坐姿 / 跪立・四肢着地 / 贴脸系 …），分类与姿势名全译成中文，日文原文留在 `catJp` / `nameJp`。

### 服装库

**1405 套 × 单角度 = 1405 张图**。原库按季节分目录，找一条百褶裙要翻四个 tab，所以改按品类归类：一级决定系列，二级是同一主件下的细分（长度 / 版型 / 材质）。

| 系列 | 套数 | 二级分类（套数） |
| --- | --- | --- |
| 半身裙 | 440 | 迷你 207 / 百褶 114 / 常规 82 / 中长 37 |
| 连衣裙 | 391 | 迷你 247 / 常规 94 / 中长 40 / 长款 10 |
| 裤装 | 293 | 长裤 182 / 牛仔 68 / 短裤 38 / 阔腿 3 / 连体 2 |
| 内衣·家居 | 200 | 套装 173 / 家居服 27 |
| 上装 | 58 | 针织 40 / 衬衫 13 / 外套 3 / 吊带 2 |
| 泳装 | 23 | 泳装 |

- 只按关键词里的「主件」判定：有 dress 归连衣裙、有 skirt 归半身裙，剩下的才看裤子；外套、包、鞋不参与一级判定。
- 14 套源关键词漏了主件，逐张看图确认后钉在 `tools/garment_classify.py` 的 `OVERRIDES` 表里（6 套缎面礼服 → 连衣裙·长款，8 套阔腿 / 直筒 / 连体裤 → 裤装）。
- 原季节留在 `season` 字段（春 213 / 夏 254 / 秋 244 / 冬 253 / 内衣 199 / 派对 48 / 泳装 54 / 性感 140），搜索照样能筛。

### 脸模库

**44 张 × 单角度 = 44 张图**，分类统一「脸模」。源图是 PNG，转换后统一 WebP。

与服装库同为「平行库」：索引 schema、画廊、导入删除全部复用，只是目录、角度集、源图不同。加新库 = `pose_db.LIB_DIRS` 加一项 + 写 `build_*_db.py` + 加一个 `GuliXxxPicker`。

### 目录

**内置素材在插件目录里，用户的素材在插件外面**——升级只会动插件目录，用户目录碰不到。

```
<插件目录> ComfyUI/custom_nodes/ComfyUI-GuliPoses/
data/zh-dict.csv  # 日→中对照表
inbox/            # ★ 收件箱：图包丢这里，启动时自动入库
poses/            # 姿态库 · img/ thumbs/ index.json
garment/          # 服装库 · 同上
faces/            # 脸模库 · 同上；png/ 已废弃，只剩引导说明

<ComfyUI>/user/default/guliposes/   # ★ 用户素材，升级不会动
├── inbox/           # 收件箱的另一份，最保险
├── pose/custom/     # 导入的图 + meta.json + thumbs/
├── pose/png/        # 转换来源：原始图丢这里
├── garment/…  face/…
```

- 原图用 WebP（q95）不用 PNG：同 1439 张，PNG 要 343 MB，WebP 只 104 MB。
- `<lib>/png/` 只是转换来源，索引只认 `img/` 里的 WebP——转换产物被覆盖也没关系，源图在你目录里，下次启动自动重转。
- 缩略图不入库，`thumbs/` 为空时首次请求现生成（单张 57 ms），之后走浏览器缓存。

只有自己替换或新增了内置图才需要重建索引：

```bash
python tools/build_pose_db.py "D:\path\to\pose-db-01"     # 姿态库
python tools/build_garment_db.py "…\服装1407"              # 服装库
python tools/build_face_db.py [--clean]                   # 脸模库，--clean 转换后删原图
```

---

## 升级不会丢自己的图

用户素材全在 **`ComfyUI/user/default/guliposes/`**，插件目录里只有内置图（被覆盖是预期行为，可重建）。

| 你自己的东西 | 位置 |
| --- | --- |
| 导入的图 + 显示名 / 分类 | `user/default/guliposes/<lib>/custom/` |
| 批量添加的原始图 | `user/default/guliposes/<lib>/png/` |
| 转换产物、缩略图、内置索引 | 插件目录内，可重建 |

老版本留在插件里的素材，启动时会自动复制到新位置（只复制不动原件，`meta.json` 走合并）：

```bash
python tools/userdata.py info      # 看两个位置各有几张
python tools/userdata.py migrate   # 复制到新位置，原件保留
python tools/userdata.py move      # 复制成功后删原件
python tools/userdata.py backup    # 打 zip 备份
python tools/userdata.py prune     # 清理孤儿缩略图，加 --apply 才真删
```

想换盘（不占 C 盘）：`setx GULIPOSES_DATA_DIR "W:\AI\guliposes-data"`，重启生效。探测顺序：环境变量 → ComfyUI 的 user 目录 → 插件内 `userdata/`（兜底）。

### 一条命令升级

```bash
python tools/upgrade.py check                       # 体检：老位置还有几张图、收件箱有没有没结算的
python tools/upgrade.py protect                     # 只搬（复制），不动原件
python tools/upgrade.py protect --purge             # 搬完且校验通过，删掉插件内原件
python tools/upgrade.py full --from gg-v1.2.3.zip   # 保护 + 全量替换
```

`--from` 可以给 zip 或解压好的目录。它依次做五件事：打快照 → 搬素材（`meta.json` 合并）→ 结算收件箱 → 逐文件 sha256 校验（有差异就拒绝删原件）→ 全量对齐插件目录（`.git`、`.workbuddy*`、`inbox`、`dist` 不碰）。

自己打发行包：

```bash
python tools/pack_release.py            # → dist/ComfyUI-GuliPoses-v<版本>.zip
python tools/pack_release.py --list     # 只列清单
```

包里不含 `.git`、`__pycache__`，也不含你的素材（`custom/`、`png/` 下的图与 `meta.json` 全部排除），可以直接发给别人。

---

## 导入自己的图

点「导入」、把图拖进面板，或复制图片后在画布按 `Ctrl+V`，都会弹导入对话框。确认后存进 `user/default/guliposes/pose/custom/`，扫目录时自动并进索引，不用重建内置库也不用重启。

| 字段 | 作用 |
| --- | --- |
| 名称 | 显示名（默认取文件名），多张共用一个名称时自动编号 |
| 分类 | 可从已有分类选，也可直接输入新分类 |
| 视角 | 这张图是正面 / 俯视 / 仰视 / 侧面 / 斜侧 |

- **一个文件 = 一个视角**；同名 + 不同视角合成一格，同名 + 同视角另存「名称 (2)」，两张都留。
- 导入后自动选中新图并切到它实际拥有的视角；随机模式只把它加进候选池。
- **右键点自定义缩略图可删除**，该姿态所有视角一起移除（会先确认）。
- 归到系列 **我的姿态**，排最前面；显示名存在 `meta.json`。

---

## 整包导入

几十上百张图时不用一张张点。把东西丢进**收件箱**，重启 ComfyUI 自动进库：

```
ComfyUI/custom_nodes/ComfyUI-GuliPoses/inbox/
├── pose/      → 姿态库「我的姿态」
├── garment/   → 服装库「我的服装」
├── face/      → 脸模库「我的脸模」
└── 直接丢根目录也行，按姿态库收
```

- **认**：单张图片、整个文件夹（递归）、zip（里面套几层目录都行）。
- **不认**：其它文件（说明、txt、psd）原样留着，不会被删。
- 结算后图进库、收件箱不留副本；不想重启就 `python tools/import_batch.py --scan`。

**多视角自动识别**：文件名尾部带 `front` / `side` / `high` / `low` / `diag`（或中文「正面 / 侧面 / 俯视 / 仰视 / 斜侧」，分隔符 `_` `-` 空格 `·`）的，剥掉后缀并把同名图合成一个姿态的多视角；单角度库照样剥后缀，角度统一正面。

| 收件箱位置 | 特点 |
| --- | --- |
| `custom_nodes/ComfyUI-GuliPoses/inbox/` | 丢着方便，**但没结算就升级会被一起删掉** |
| `ComfyUI/user/default/guliposes/inbox/` | 在插件外面，升级碰不到，最保险 |

| 命令 | 作用 |
| --- | --- |
| `python tools/import_batch.py --scan` | 结算收件箱（两处都扫） |
| `python tools/import_batch.py "D:\图包" --lib garment` | 指定路径直接入库，认文件夹和 zip |
| `--cat 分类名` | 落库用的分类，默认「自定义」 |

---

## 搭配推荐

本插件只做「把姿态图库搬进画布」。配套的 **[ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes)** 是中文工作流效率节点合集，38 个节点、零额外依赖，不冲突。

| 你想要的 | GuliNodes 里对应的 |
| --- | --- |
| 画布一团乱，节点对不齐 | 工具栏：上色、对齐、等宽等高、自动间距、批量整理 |
| 总在算 1024×1536 怎么对齐到 8 | `GG 图像宽高` / `GG Latent` |
| 批量裁剪、缩放、调色 | `GG 图像裁剪` / `GG 图像缩放` / `GG 色彩校正` |
| 提示词写不动 | `GG 提示词增强qwen2.1` / `GG 提示词优化qwen2.1` |
| 显存吃满、模型不卸载 | `GG 内存清理` |

```bash
cd ComfyUI/custom_nodes && git clone https://github.com/guliacer/ComfyUI-GuliNodes.git
```

装完在右键菜单找 **GG** 或 **GuliNodes**（本插件在 **GuliPoses** 分类下）。

---

## 更新记录

### v1.2.3 — 2026-10-30

- 新增服装库（1405 套 / 6 类型）与脸模库（44 张），节点扩到三个。
- 服装库改按穿搭类型归类，替代原季节分法。
- 用户素材移到 `user/default/guliposes/`，升级不再覆盖。
- 老位置素材启动时自动迁移，`meta.json` 合并而非覆盖。
- 新增收件箱：图包丢进 `inbox/` 重启入库，支持文件夹与 zip。
- 文件名视角后缀自动识别，同名合成多视角。
- 新增 `upgrade.py`：先搬素材、校验通过再全量替换。
- 新增 `pack_release.py`：打发行包，自动排除用户素材。
- 新增 `userdata.py` 与 `import_batch.py` 两个管理脚本。
- 启动日志改为强制 flush，重定向到文件也能看到。
- 修复迁移时 `meta.json` 被覆盖、删图后缩略图死链。

### v1.0.0 — 2026-10-29

- 首个版本：姿态库 288 组 × 5 视角，画廊内选图。
- 三种取图模式：固定选中 / 全库随机 / 范围内随机。
- 支持导入自己的图（按钮 / 拖拽 / `Ctrl+V`）。
- 内置图改 WebP，仓库体积 370 MB → 105 MB。
- 缩略图不入库，首次浏览时现场生成。

---

## 致谢

图库与中文数据来自 **[anhao/ai-pose-gallery-zh](https://github.com/anhao/ai-pose-gallery-zh)**：`poses/index.json` 与它一一对应（288 组 / 1439 张 / 4 体系 / 26 分类 / 5 视角），`data/zh-dict.csv` 取自它的 `data/translations.csv`。

原始来源：原作者 **ギア**（[@giaaibusi](https://x.com/giaaibusi)）· 原站 <https://ai-pose-gallery.pages.dev/> · 中文版维护 Anhao（[@anhao_ai](https://x.com/anhao_ai)）

> 图片与原始数据著作权归原作者所有。本插件只做本地索引与画布内浏览，不对图片主张任何权利。原作者若认为侵权，请开 Issue，会立即移除。

配套插件：[guliacer/ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes) · 框架：[ComfyUI](https://github.com/comfyanonymous/ComfyUI)

---

## 许可与免责

- **代码**以 **MIT** 协议开源，见 [LICENSE](LICENSE)；该协议**不覆盖** `poses/` 下的图片与原始数据。
- 图库包含**成人向内容**：姿态库性感系姿势、服装库性感 / 内衣 / 泳装系列均涉及成人向题材，仅供艺术创作、动作与穿搭参考及技术学习。未成年人请勿使用。
- 本项目与上述来源仓库均无隶属关系，仅为个人学习与工具实践。
