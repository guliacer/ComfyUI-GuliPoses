# ComfyUI-GuliPoses

[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom__nodes-4f8cff)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](#license-and-disclaimer)
[![Poses](https://img.shields.io/badge/library-288%20sets%20%C2%B7%201439%20images-ff6b6b)](#data)

**Browse a pose library, pick a pose and a camera angle, and wire it straight into your graph.**

A ComfyUI node for a library of mannequin (3D white-model line-art) pose references. 288 poses × 5 camera angles, all embedded in an in-node gallery — no leaving the canvas to dig through folders, no hand-writing image paths. The output plugs directly into ControlNet / Depth / Lineart.

Three ways to pick: **Fixed** (reproduce an exact pose), **Random (whole library)**, and **Random (scoped)** — sample only within a chosen series and/or category.

[中文说明](README.md)

---

## Why use it

| | |
| --- | --- |
| **No context switching** | The thumbnail grid lives inside the node. One click selects; the node reflows with its width |
| **Three sampling modes** | Reproduce exactly, gacha across the whole library, or sample inside a narrow range |
| **You can see what random picked** | After execution the node pushes the pose it actually drew back into the gallery and jumps to it — not "it randomized, no idea what I got" |
| **Lock what you like** | Drawn a pose you want? Click its thumbnail and the node switches to Fixed, so the workflow stores exactly that one — no seed to remember |
| **Zero extra dependencies** | Only the PIL / numpy / torch already bundled with ComfyUI — no cv2, no kornia |
| **Bilingual UI** | Node, options and labels are in Chinese; the gallery follows ComfyUI's CSS variables in both light and dark themes |

---

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/guliacer/ComfyUI-GuliPoses.git
```

No git? Download the repository and drop the `ComfyUI-GuliPoses` folder into `ComfyUI/custom_nodes/`, then restart ComfyUI.

```
ComfyUI/
└── custom_nodes/
    └── ComfyUI-GuliPoses/     ← put it here
        ├── nodes.py
        ├── pose_db.py
        ├── api_routes.py
        ├── web/
        ├── poses/             ← image library (see "Data")
        └── tools/
```

Then right-click the canvas → **Add Node** → **GuliPoses** → **GG 姿态库**.

> A fresh install needs the image library in `poses/` (~368 MB). See [Data](#data).
> The repository holds code only — images are not versioned, so this step is required or the gallery stays empty.

---

## The node

**GG 姿态库** (`GuliPosePicker`, category `GuliPoses`)

The UI is entirely in Chinese — widget labels, output names, series / category / pose names. No English parameter names, no Japanese source text on screen.

### Inputs

| Parameter | Shown as | Type | Active in | Description |
| --- | --- | --- | --- | --- |
| Parameter | Type | Active in | Description |
| --- | --- | --- | --- |
| 模式 | combo | always | 固定选中 / 全库随机 / 范围内随机 |
| 姿态 | combo | 固定选中 | 288 poses, e.g. `性感全身 P001 · S形站姿・胯部侧顶` |
| 视角 | combo | always | 正面 / 俯视 / 仰视 / 侧面 / 斜侧 / **随机视角** |
| 筛选系列 | combo | 范围内随机 | 全部 + four series (sorted by pose count) |
| 筛选分类 | combo | 范围内随机 | 全部 + 26 categories (sorted by pose count) |
Only five inputs — no `seed`, and no `control_after_generate` attached to one. This node does not sample, so a seed would mean nothing to it.

**Parameters follow the mode.** Only the inputs that actually take effect are shown; the rest hide themselves. In 固定选中 you get a clean three rows (模式 / 姿态 / 视角) instead of a column of dead controls.

**Node height is yours to decide, and it stays that way.** Drag the node taller and the gallery grows with it, showing more rows. The size you drag is saved into the workflow, so switching modes, angles or filters never snaps it back — the gallery simply absorbs the rows that disappear. Height is only ever nudged upward (e.g. after a clipboard import that adds content), never downward.

> Hiding is purely visual — the order and length of `widgets_values` are untouched, so workflows still save and load correctly and the backend receives exactly the same arguments.
> The parameter names themselves are Chinese — there is no "English identifier + Chinese label" mapping layer, so `/prompt` shows exactly these keys.

### Outputs

| Output | Description |
| --- | --- |
| 姿态图 | The selected pose image, `900×1200` RGB, float 0–1, batched |

Image only. The pose name and angle are already on the gallery badge — no need for two string outputs taking up canvas space.

---

## Sampling modes

### Fixed (default)

Resolves exactly by 姿态 + 视角. Clicking a thumbnail or an angle button syncs both combos, and the choice is saved with the workflow — reopening an old workflow gives you the same image.

Use when you already know what you want, or need to reproduce a result.

### Random — whole library

Draws one of all 288 poses. 筛选系列 and 筛选分类 are ignored; the series dropdown in the gallery greys out.

Use for batch exploration or reshuffling poses across a set of images.

### Random — scoped

Draws from the intersection of 筛选系列 × 筛选分类. Both accept "All", so "one series only", "one category only" and "both" are the same set of parameters.

Use when you're building a themed series that needs variation but must stay in range.

> **How scoping resolves**: it takes the series subset first, then looks for the category inside it. If the category isn't there, it falls back to "series only"; if the series is empty too, it falls back to the whole library.
> An empty combination therefore never errors — it **silently widens the range**. The `候选 N 个` ("N candidates") counter at the bottom of the gallery always reflects the pool the backend will really use, so follow that number.

### Angles

Six options: **Front / High / Low / Side / Diagonal / Random angle**. "Random angle" draws from the angles that pose *actually has*.

### No seed — how do I pin a result

Random modes draw fresh every time and store no seed. To keep a result, **click its thumbnail in the gallery**: the mode flips back to Fixed and both the pose and the angle are written into the workflow. Every later run gives you that exact one.

That is more direct than copying a seed: what you see is what you get, one click and it stays.

### Post-execution round-trip

In all three modes the node pushes the pose it actually drew back to the frontend after execution; the gallery jumps to that image and the badge updates to the real result.

> Random modes re-draw on every queue (the node declares `IS_CHANGED`, so the execution cache cannot swallow it); Fixed still uses the cache and won't re-read the file on every run.

---

## The gallery

The lower half of the node is a hand-built DOM gallery, six layers top to bottom:

| Layer | Content | Interaction |
| --- | --- | --- |
| Preview | Current selection, badge in the lower-left with `code · category · angle` | — |
| Angle bar | Front / High / Low / Side / Diagonal | Click to swap every thumbnail to that angle |
| Tool row | Series dropdown · search box · **Import** · **Random** button | Filter / search / import your own images / pick one from what's currently visible |
| Thumbnail grid | Columns follow node width; a lone cell in the last row triggers a balanced re-flow | Click to select |
| Footer | Candidate count on the left, current mode hint on the right | — |
| Promo row | One dim line pointing at the companion plugin | Click opens the ComfyUI-GuliNodes repo |

- **Series dropdown** — filters the gallery; in random modes it directly controls the candidate range
- **Search box** — matches code, pose name, category and label
- **Import** — puts your own pose images into the library, see [Importing your own poses](#importing-your-own-poses)
- **Random button** — picks from what's *currently visible* and switches back to Fixed. It is not "remember a seed" — it pins that exact image into the workflow
- **Gallery in random mode** — shows the candidate pool directly, so the cell count always matches `候选 N 个`
- **Stale preview** — in random mode, if the preview isn't inside the current candidate range (e.g. you just changed the filter), the image dims and the badge gets a `上次 ·` ("last time") prefix

> Pose codes repeat across series (`P001` exists in all four), so 姿态 combo labels carry a series prefix.

---

## Data

**288 poses × 5 angles = 1439 images** (`full_sexy_P018` has no low-angle shot; selecting it falls back to the front view).

| Series | Poses |
| --- | --- |
| Full body — sexy | 80 |
| Upper body | 80 |
| Full body — standard | 73 |
| Two people | 55 |

26 action categories (站姿 / 趴卧 / 坐姿 / 跪立・四肢着地 / 贴脸系 …). Category and pose names are **fully translated to Chinese**; the original Japanese is kept in the `catJp` / `nameJp` fields for reference.

```
data/zh-dict.csv  # Japanese→Chinese dictionary (323 entries: 288 pose names + 26 categories + 5 angles + 4 series)
poses/
├── img/        # full size 900×1200 PNG (343 MB)
├── thumbs/     # 300×400 thumbnails (26 MB), used by the gallery
├── custom/     # your own imported poses, merged into the index on scan
└── index.json  # generated by tools/build_pose_db.py
```

The images are large and not committed (see `.gitignore`). Get them from the source repository listed under [Acknowledgements](#acknowledgements), copy `img/` and `thumbs/` into `poses/`, then rebuild the index:

```bash
python tools/build_pose_db.py "D:\path\to\pose-db-01"
```

The script reads `data/poses.csv`, regenerates `poses/index.json`, and translates categories and pose names through `data/zh-dict.csv`. If the dictionary is missing it falls back to the Japanese source and reports the untranslated entries. The index is re-read when its mtime changes, so no ComfyUI restart is needed.

---

## Importing your own poses

Click **Import** in the tool row, **drag images onto the panel**, or copy an image and press **Ctrl+V** over the canvas — all three open an import dialog. Confirm it and the files land in `poses/custom/`, merged into the index on scan — **no need to rebuild the built-in library or restart ComfyUI**.

The dialog covers three fields, so you never have to go back and rename files:

| Field | Meaning |
| --- | --- |
| Name | Display name for the image (defaults to the file name). Several images sharing one name are numbered "name 1", "name 2", … |
| Category | Which category it belongs to — pick an existing one or type a new one |
| Angle | Which view this image is: front / high / low / side / diag |

- **One file = one view**; **same name + different angle = two views of one pose**, shown as a single cell in the gallery
- Same name + **same angle** never overwrites: it is stored as a new pose "name (2)" and both images are kept
- The dialog also has a **From clipboard** button that reads an image out of the system clipboard; if the browser denies access it tells you to use Ctrl+V instead
- Leave the name empty to use the file name; everything is filed under series **我的姿态** ("my poses") and sorted to the front of the gallery
- Thumbnails are generated by the plugin (320 px long edge, transparency flattened onto white) in `poses/custom/thumbs/`
- The dropdowns refresh **in place** after an import: in Fixed mode the new image is selected automatically *and the gallery switches to the angle it actually has*; in random modes it only joins the candidate pool and your current pick is left alone
- **Right-click a custom thumbnail to delete it** — every view of that pose is removed from `poses/custom/` too (there is a confirmation, and it cannot be undone)
- Supports `png / jpg / jpeg / webp / bmp`; path separators and illegal characters are stripped, Chinese names are preserved
- Dropping files into `poses/custom/` by hand works as well — refresh the page to pick them up. Unreadable images are skipped and reported in the ComfyUI console

```
poses/
└── custom/        # your pose images, one file per view
    ├── thumbs/    # auto-generated thumbnails, don't edit by hand
    └── meta.json  # name / category / angle mapping, don't edit by hand
```

Custom poses share the same filters and random pool as the built-in library: pick series "我的姿态" or category "自定义" to scope them, and whole-library random will draw them too. Display names live in `meta.json`, so **renaming a pose breaks the label stored in existing workflows** — the node will ask you to re-select one.

---

## Recommended companion

### Need more than pose picking? Install [ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes)

This plugin does exactly one thing: **bring the pose library into the canvas**. If your day-to-day graph work is missing any of the following, install the companion **ComfyUI-GuliNodes** — a lightweight efficiency node pack for Chinese workflows, **38 nodes, zero extra Python dependencies**, fully compatible with this plugin.

| What you want | What GuliNodes gives you |
| --- | --- |
| Canvas is a mess, nothing lines up | Top toolbar: coloring, align, equal width/height, auto spacing, batch tidy; groups can collapse into sub-workflow nodes |
| Always computing how 1024×1536 aligns to 8 | `GG 图像宽高` / `GG Latent` — size by edge, by K-resolution, by Latent, or by image |
| Batch crop, scale, grade, compare | `GG 图像裁剪` / `GG 图像缩放` / `GG 图像调整` / `GG 色彩校正` / `GG 图像对比 N张` |
| Stuck writing prompts | `GG 提示词增强qwen2.1` (API / local PE / local LLM) + `GG 提示词优化qwen2.1` |
| Nowhere safe to keep an API key | `GG 密钥输入` — endpoint / key / model, with connectivity test and model listing |
| VRAM full, models never unloaded | `GG 内存清理` — unload models, clear caches, print a report |
| Video work | `GG 视频加载` / `GG 视频合成` / `GG 视频压缩` / `GG 视频保存` (needs `ffmpeg` on PATH) |
| Too many LoRAs to manage | `GG LoRA自定义加载` — up to 20 slots |

Install:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/guliacer/ComfyUI-GuliNodes.git
```

Or search `ComfyUI-GuliNodes` in ComfyUI Manager, restart, then hard-refresh the browser (`Ctrl` + `F5`). Its nodes live under the **GG** / **GuliNodes** category (mind the difference: **GG 姿态库** is *this* plugin's node and sits under **GuliPoses**, not there).

> Division of labour: **GuliPoses decides *which pose*, GuliNodes keeps *the rest of the pipeline* tidy.** They're complementary and don't collide on node names.

---

## Implementation

- `nodes.py` — node definition, the three mode branches, the `IS_CHANGED` cache policy, `ui.picked` round-trip
- `pose_db.py` — index cache, `pool()` candidate set and fallback chain, `pick_angle()`, missing-image fallback
- `api_routes.py` — `/guliposes/index.json`, `/guliposes/thumb/{name}`, `/guliposes/img/{name}` (filename-only lookup, no directory traversal; 7-day cache on images)
- `web/gg-pose-gallery.js` — DOM gallery widget (no build step, plain ES module); its candidate pool mirrors the backend's
- `tools/build_pose_db.py` — index generation
- `AGENTS.md` — development conventions (shared with ComfyUI-GuliNodes): design checklist, naming, visibility rules, frontend red lines, verification
- `tools/verify/*.mjs` — headless Chromium verification scripts

### Verification scripts

After changing the frontend or the mode logic, spin up an **isolated instance** (don't disturb the one you're using):

```bash
python -s ComfyUI/main.py --port 8189 --cpu --disable-all-custom-nodes \
  --whitelist-custom-nodes ComfyUI-GuliPoses --disable-auto-launch
```

```bash
COMFY_PORT=8189 node tools/verify/frontend-modes.mjs    # filter intersection / category only / locked dropdown / serialization
COMFY_PORT=8189 node tools/verify/queue-roundtrip.mjs   # real queues: random re-draws twice, fixed hits the cache, ui.picked round-trips
COMFY_PORT=8189 node tools/verify/layout.mjs            # layout check: no overflow, grid height, promo row visible
COMFY_PORT=8189 node tools/verify/mode-visibility.mjs   # per-mode widget visibility, node height left untouched
COMFY_PORT=8189 node tools/verify/custom-import.mjs     # import loop: dialog opens, name/category/angle, same-name merge, clipboard, right-click delete, clean teardown
```

All five scripts rely on a local playwright-core and Chromium; paths are constants at the top of each file. `custom-import.mjs` creates its own test images, uploads them and deletes them again, so `poses/custom/` should be back to its original state afterwards.

---

## Changelog

### Unreleased

- Three ways to pick: Fixed / Random (whole library) / Random (scoped); parameters appear only in the modes where they apply.
- Fully Chinese UI: parameter names, output names, series / category / pose names (all 288 + 26 translated). No English parameter names, no Japanese source text.
- A single 姿态图 output. No pose-name / pose-info strings and no seed — click a thumbnail to lock the pose you drew.
- Random modes re-draw on every queue (the node declares `IS_CHANGED`); Fixed still uses the cache.
- Aligned with ComfyUI-GuliNodes: node name `GG 姿态库`, category `GuliPoses`, frontend file `web/gg-pose-gallery.js`.
- Old-workflow compatibility: leftover output slots are trimmed on load; the missing `seed` value is ignored and the rest map positionally.
- Import your own poses: **Import** in the tool row, dragging images onto the panel, or **Ctrl+V** all open an import dialog where you can set **name / category / angle**. Same name with a different angle merges into one pose with several views; same name and same angle is stored as "name (2)" instead of overwriting. Files go to `poses/custom/` and are merged into the dropdowns, gallery and random pool (series "我的姿态"). The dropdowns refresh in place, Fixed mode auto-selects the new image and switches to the angle it actually has, right-click deletes. The node keeps the same five parameters, so existing workflows still open.
- Fixed "clicking Import does nothing": the import and random buttons used to share a class name, and the random handler overwrote the import button's click handler.
- Fixed "the node keeps shrinking itself": the gallery now absorbs whatever height the node has (drag it taller and the grid really shows more rows), switching modes / angles / filters no longer rewrites the node height, the size you drag is remembered in the workflow, and trimming old output slots only ever grows the node.
- The index is re-read on mtime change, so rebuilding the built-in library no longer needs a restart.

---

## Acknowledgements

This plugin only exists because someone else organised the library first.

### Inspiration and data source

> **Both the idea and the assets behind this project come from the repository below.**
>
> ### [anhao/ai-pose-gallery-zh](https://github.com/anhao/ai-pose-gallery-zh)
> Chinese edition of an AI pose reference gallery · 288 sets / 1439 source images · fully localised · zero-dependency static gallery

- **Inspiration** — its web gallery (filter by series / category / angle, lightbox, keyboard navigation) is what suggested "put that browsing experience inside a ComfyUI node". The "Random (scoped)" mode here is essentially its filter logic turned into random sampling.
- **Data** — `poses/index.json` in this plugin maps one-to-one to it: 288 poses, 1439 images, 4 series, 26 categories, 5 angles.
- **Chinese dictionary** — `data/zh-dict.csv` (323 entries) comes from its `data/translations.csv`; every Chinese category and pose name you see in the node is from that table.
- [Live demo](https://ai-pose-gallery.anhao.app/) · [GitHub](https://github.com/anhao/ai-pose-gallery-zh)

### Upstream source

- **Original author**: ギア ([@giaaibusi](https://x.com/giaaibusi))
- **Original site**: <https://ai-pose-gallery.pages.dev/>
- **Chinese edition maintained by**: Anhao ([@anhao_ai](https://x.com/anhao_ai))

> Copyright of the images and the original pose data belongs to the original author, ギア. This plugin only provides **local indexing and in-canvas browsing**; it claims no rights over the images and grants no commercial-use license. If the original author believes this project infringes their rights, please open an issue and the content will be removed.

### Companion plugin

- **[guliacer/ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes)** — efficiency node pack for Chinese ComfyUI workflows, recommended in this README as the pipeline-enhancement companion.

### Built with

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — node framework and frontend extension API

---

## License and disclaimer

- The **code** in this plugin (`nodes.py`, `pose_db.py`, `api_routes.py`, `web/`, `tools/`) is released under **MIT** — see [LICENSE](LICENSE).
- That license does **not** cover the images and data under `poses/`; their copyright belongs to the original author, ギア.
- The library contains **adult-oriented pose references** (some category names use sexual terminology). It is intended for artistic creation, motion reference and technical study only. Do not use it for unlawful purposes. Not for minors.
- This project is not affiliated with any of the repositories above; it is a personal study and tooling exercise.
