# ComfyUI-GuliPoses

[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom__nodes-4f8cff)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](#license-and-disclaimer)
[![Poses](https://img.shields.io/badge/library-288%20sets%20%C2%B7%201439%20images-ff6b6b)](#data)

**Browse a pose library inside a ComfyUI node, pick a pose and an angle, and wire it straight into your graph.**

A ComfyUI node for a library of mannequin (3D white-model line-art) pose references. 288 poses × 5 camera angles, all embedded in an in-node gallery — no leaving the canvas to dig through folders, no hand-writing image paths. The output plugs directly into ControlNet / Depth / Lineart.

中文 · [English](README_EN.md)

---

## Features

| Capability | Detail |
| --- | --- |
| No context switching | The thumbnail grid lives inside the node. One click selects; columns reflow with the node's width |
| Three sampling modes | Fixed reproduces exactly, whole-library random is gacha, scoped random stays inside a range |
| You can see what random picked | After execution the node pushes the pose it actually drew back into the gallery and jumps to it |
| Lock what you like | Click a thumbnail and the node switches to Fixed, writing pose and angle into the workflow — no seed to remember |
| Import your own poses | **Import** button, drag-and-drop, or `Ctrl+V`, with custom name / category / angle |
| Zero extra dependencies | Only the PIL / numpy / torch already bundled with ComfyUI — no cv2, no kornia |
| Chinese UI throughout | Widget labels, output name, modes, angles, series, categories, pose names. Follows ComfyUI's CSS variables in both light and dark themes |

---

## Installation

**Option 1 — git (recommended)**

```bash
cd ComfyUI/custom_nodes
git clone --depth 1 https://github.com/guliacer/ComfyUI-GuliPoses.git
```

**Option 2 — offline archive**

Download `ComfyUI-GuliPoses.7z` from [Releases](https://github.com/guliacer/ComfyUI-GuliPoses/releases) and extract the `ComfyUI-GuliPoses` folder into `ComfyUI/custom_nodes/`. Useful without git, or on networks where `git clone` keeps failing.

Resulting layout:

```
ComfyUI/
└── custom_nodes/
    └── ComfyUI-GuliPoses/
        ├── nodes.py
        ├── pose_db.py
        ├── api_routes.py
        ├── web/
        ├── poses/          ← image library, shipped with the repo
        └── tools/
```

Restart ComfyUI, then right-click the canvas → **Add Node** → **GuliPoses** → **GG 姿态库**.

> The repository ships every image (~105 MB), so a clone is all you need — no separate download, no index rebuild. Later `git pull`s only fetch code changes, so the size does not keep growing.

---

## The node

**GG 姿态库** (`GuliPosePicker`, category `GuliPoses`)

### Inputs

| Parameter | Type | Active in | Description |
| --- | --- | --- | --- |
| 模式 | combo | always | 固定选中 / 全库随机 / 范围内随机 |
| 姿态 | combo | 固定选中 | 288 poses, e.g. `性感全身 P001 · S形站姿・胯部侧顶` |
| 视角 | combo | always | 正面 / 俯视 / 仰视 / 侧面 / 斜侧 / **随机视角** |
| 筛选系列 | combo | 范围内随机 | 全部 + four series (sorted by pose count) |
| 筛选分类 | combo | 范围内随机 | 全部 + 26 categories (sorted by pose count) |

Only five inputs — no `seed`, and no `control_after_generate` attached to one. This node does not sample, so a seed would mean nothing to it.

**Parameters follow the mode.** Only the inputs that actually take effect are shown: 固定选中 gives you a clean three rows (模式 / 姿态 / 视角), whole-library random leaves two, and there is never a column of dead controls. Hiding is purely visual — the order and length of `widgets_values` are untouched, so workflows still save and load correctly and the backend receives exactly the same arguments.

**Node height is yours to decide.** Drag the node taller and the gallery grows with it, showing more rows; the size you drag is saved into the workflow, and switching modes, angles or filters never snaps it back — the gallery simply absorbs the rows that disappear. Height is only ever nudged upward (e.g. when an import needs to reveal something new), never downward.

> The parameter names themselves are Chinese — there is no "English identifier + Chinese label" mapping layer, so `/prompt` shows exactly these keys.

### Outputs

| Output | Description |
| --- | --- |
| 姿态图 | The selected pose image, `900×1200` RGB, float 0–1, batched |

Image only. The pose name and angle are already on the gallery badge — no need for two string outputs taking up canvas space.

---

## Sampling modes

| Mode | Draws from | Use when |
| --- | --- | --- |
| 固定选中 | Exact 姿态 + 视角 | You know what you want, or need to reproduce a result |
| 全库随机 | All 288 poses | Batch exploration, reshuffling poses across a set of images |
| 范围内随机 | Intersection of 筛选系列 × 筛选分类 | A themed series that needs variation but must stay in range |

**固定选中** (default): clicking a thumbnail or an angle button in the gallery syncs both combos, and the choice is saved with the workflow — reopening an old workflow gives you the same image.

**全库随机** ignores both filters; the series dropdown in the gallery greys out.

**范围内随机**: both filters accept "All", so "one series only", "one category only" and "both" use the same two parameters. Scoping resolves by taking the series subset first, then looking for the category inside it; if the category isn't there it falls back to "series only", and if the series is empty too it falls back to the whole library. An empty combination therefore never errors — it **silently widens the range**. The `候选 N 个` ("N candidates") counter at the bottom of the gallery always reflects the pool the backend will really use, so follow that number.

### Angles

Six options: **正面 / 俯视 / 仰视 / 侧面 / 斜侧 / 随机视角**. "随机视角" draws from the angles that pose *actually has*.

### No seed — how do I pin a result

Random modes draw fresh every time and store no seed. To keep a result, **click its thumbnail in the gallery**: the mode flips back to 固定选中 and both the pose and the angle are written into the workflow. Every later run gives you that exact one — what you see is what you get.

After execution the node always pushes the pose it actually drew back to the frontend; the gallery jumps to that image and the badge updates to the real result. Random modes re-draw on every queue (the node declares `IS_CHANGED`, so the execution cache cannot swallow it); 固定选中 still uses the cache and won't re-read the file on every run.

---

## The gallery

The lower half of the node is a hand-built DOM gallery, six layers top to bottom:

| Layer | Content | Interaction |
| --- | --- | --- |
| Preview | Current selection, badge in the lower-left with `code · category · angle` | — |
| Angle bar | 正面 / 俯视 / 仰视 / 侧面 / 斜侧 | Click to swap every thumbnail to that angle |
| Tool row | Series dropdown · search box · **Import** · **Random** button | Filter / search / import your own images / pick one from what's currently visible |
| Thumbnail grid | Columns follow node width; a lone cell in the last row triggers a balanced re-flow | Click to select |
| Footer | Candidate count on the left, current mode hint on the right | — |
| Promo row | One dim line pointing at the companion plugin | Click opens the ComfyUI-GuliNodes repo |

A few easy misunderstandings:

- The **Random** button picks from what is *currently visible* and switches back to 固定选中. It is not "remember a seed" — it pins that exact image into the workflow.
- The **gallery in random mode** shows the candidate pool directly, so the cell count always matches `候选 N 个`.
- **Stale preview**: in random mode, if the preview isn't inside the current candidate range (e.g. you just changed the filter), the image dims and the badge gets a `上次 ·` ("last time") prefix. That is normal — the preview is the result of the previous run.
- Pose codes repeat across series (`P001` exists in all four), so 姿态 combo labels carry a series prefix.

---

## Data

**288 poses × 5 angles = 1439 images** (`full_sexy_P018` has no low-angle shot; selecting it falls back to the front view).

| Series | Poses |
| --- | --- |
| 全身单人-性感系 | 80 |
| 上半身单人 | 80 |
| 全身单人-标准系 | 73 |
| 双人互动 | 55 |

26 action categories (站姿 / 趴卧 / 坐姿 / 跪立・四肢着地 / 贴脸系 …). Category and pose names are **fully translated to Chinese**; the original Japanese is kept in the `catJp` / `nameJp` fields for reference.

```
data/zh-dict.csv  # Japanese→Chinese dictionary (323 entries: 288 pose names + 26 categories + 5 angles + 4 series)
poses/
├── img/        # full size 900×1200 WebP (104 MB, 1439 files) — shipped
├── thumbs/     # 300×400 thumbnails for the gallery — not versioned, generated on demand
├── custom/     # your own imported poses, merged into the index on scan (not versioned)
└── index.json  # shipped with the repository
```

**The images live in the repository, so a clone is all you need** — no separate download, no index rebuild. The whole repository is ~105 MB and does not keep growing.

**Thumbnails cost the repository nothing.** When `poses/thumbs/` is empty, the node renders one from the full-size image the first time it is requested and writes it to disk — after that it is served from the browser cache exactly as before. Measured: 288 thumbnails (one angle) generated on the fly in 2.8 s, 57 ms each; the gallery lazy-loads only the handful in view, so the first paint is unaffected.

**Why not PNG.** 1439 line-art images at 900×1200 take 343 MB as PNG, which is too slow to push or clone. As WebP q95 they take 104 MB, with PSNR 50.9 dB and a max pixel delta of 8/255 — indistinguishable even at 2.3× zoom. The converter is `tools/optimize_library.py`.

You only need the command below if you replace or add built-in images yourself and want to regenerate the index:

```bash
python tools/build_pose_db.py "D:\path\to\pose-db-01"
```

The script reads `data/poses.csv`, regenerates `poses/index.json`, and translates categories and pose names through `data/zh-dict.csv`. The index records each image under its actual on-disk extension (`.webp` or `.png`), so switching to WebP needs no other change. If the dictionary is missing it falls back to the Japanese source and reports the untranslated entries. The index is re-read when its mtime changes, so no ComfyUI restart is needed.

---

## Importing your own poses

Click **Import** in the tool row, **drag images onto the panel**, or copy an image and press **Ctrl+V** over the canvas — all three open an import dialog. Confirm it and the files land in `poses/custom/`, merged into the index on scan — **no need to rebuild the built-in library or restart ComfyUI**.

The dialog lets you set three things, so you never have to rename files afterwards:

| Field | Purpose |
| --- | --- |
| Name | Display name for the image (defaults to the filename). Several images sharing one name are numbered "name 1", "name 2"… |
| Category | Which category it belongs to — pick an existing one or type a new one |
| Angle | Whether the image is 正面 / 俯视 / 仰视 / 侧面 / 斜侧 |

Key points:

- **One file = one angle**; **same name + different angle = one pose with several views**, merged into a single cell in the gallery
- Same name + **same angle** never overwrites: it is stored as a new pose "name (2)" and both images are kept
- The dialog also has a **"From clipboard"** button that reads the system clipboard; if the browser denies permission it tells you to use Ctrl+V instead
- Leave the name empty to use the filename; imported poses join the series **我的姿态** and sort first in the gallery
- Thumbnails are generated by the plugin (320 px on the long edge, transparency flattened onto white) into `poses/custom/thumbs/` — you don't have to prepare them
- The dropdowns **refresh in place** after an import: in 固定选中 the new image is selected automatically and the angle switches to one it actually has; in random modes it only joins the candidate pool without changing your current selection
- **Right-click a custom thumbnail to delete it** — every angle of that pose is removed from `poses/custom/` (there is a confirmation first; deletion is permanent)
- Supports `png / jpg / jpeg / webp / bmp`; path components and illegal characters in filenames are stripped, Chinese characters are kept as-is
- Dropping files into `poses/custom/` by hand works too — refresh the page to see them; broken images are reported by name in the ComfyUI console and skipped

```
poses/
└── custom/        # your pose images, one file per angle
    ├── thumbs/    # auto-generated thumbnails, don't edit
    └── meta.json  # name / category / angle mapping, don't edit
```

Custom poses share the same filters and random pools as the built-in library: pick series **我的姿态** or category **自定义** to isolate them, and whole-library random can draw them too. Display names live in `meta.json`, so **renaming a pose breaks old workflows that stored the old name** — the node will ask you to pick again.

---

## Companion plugin

### Want more? Install [ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes)

This plugin does one thing: **bring the pose library into the canvas**. If your daily work is missing any of the following, install the companion **ComfyUI-GuliNodes** — a lightweight efficiency node pack for Chinese-language workflows, **38 nodes, zero extra Python dependencies**, compatible with this plugin and installable side by side.

| What you want | What GuliNodes has |
| --- | --- |
| The canvas is a mess, nodes don't line up | Toolbar: colour, align, equal width/height, auto spacing, batch tidy; groups collapse into a subgraph node |
| Always computing how 1024×1536 aligns to 8 | `GG 图像宽高` / `GG Latent`: sizes by edge, by K resolution, by latent, by image |
| Batch crop, resize, grade, compare | `GG 图像裁剪` / `GG 图像缩放` / `GG 图像调整` / `GG 色彩校正` / `GG 图像对比 N张` |
| Prompts are hard work | `GG 提示词增强qwen2.1` (API / local PE / local LLM) + `GG 提示词优化qwen2.1` |
| Nowhere to hide an API key | `GG 密钥输入`: endpoint / key / model, with connectivity test and model listing |
| VRAM maxed out, models not unloading | `GG 内存清理`: unload models + clear cache + report |
| Working with video | `GG 视频加载` / `GG 视频合成` / `GG 视频压缩` / `GG 视频保存` (needs `ffmpeg` on PATH) |
| Too many LoRAs to manage | `GG LoRA自定义加载`: up to 20 slots |

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/guliacer/ComfyUI-GuliNodes.git
```

Or install `ComfyUI-GuliNodes` from ComfyUI Manager, then hard-refresh the browser (`Ctrl` + `F5`). Look for the **GG** or **GuliNodes** category in the right-click menu (note: **GG 姿态库** is this plugin's node and lives under **GuliPoses**, not under GG).

> Division of labour: **GuliPoses decides "which pose", GuliNodes makes "the pipeline itself smooth"**. They complement each other and never collide on node names.

---

## Implementation

| File | Responsibility |
| --- | --- |
| `nodes.py` | Node definition, the three mode branches, `IS_CHANGED` cache strategy, `ui.picked` round-trip |
| `pose_db.py` | Index caching, `pool()` candidate sets and fallback chain, `pick_angle()`, missing-image fallback, on-demand thumbnails; scans `poses/custom/` and merges it into the built-in index |
| `api_routes.py` | Static routes, self-registered on import. Filename-only, no directory traversal; 7-day cache for built-in images, negotiated caching for custom ones |
| `web/gg-pose-gallery.js` | The DOM gallery widget (no build step, plain ES module); its random-mode candidate pool matches the backend |
| `tools/build_pose_db.py` | Generates the index |
| `tools/optimize_library.py` | PNG → WebP conversion |
| `tools/release_upload.py` | Creates the Release and uploads the offline archive |
| `AGENTS.md` | Development rules (shared with ComfyUI-GuliNodes): design checklist, naming, display rules, frontend red lines, verification flow |

Public routes (ComfyUI mounts them both at the root and under `/api`, so either works):

```
GET  /guliposes/index.json            index
GET  /guliposes/img/{name}            built-in full-size image
GET  /guliposes/thumb/{name}          built-in thumbnail (rendered on demand if missing)
GET  /guliposes/custom/img/{name}     custom full-size image
GET  /guliposes/custom/thumb/{name}   custom thumbnail
POST /guliposes/custom/upload         import
POST /guliposes/custom/delete         delete
```

### Verification scripts

After changing frontend or mode logic, start an **isolated instance** first (never touch the one in use):

```bash
python -s ComfyUI/main.py --port 8189 --cpu --disable-all-custom-nodes \
  --whitelist-custom-nodes ComfyUI-GuliPoses --disable-auto-launch
```

```bash
COMFY_PORT=8189 node tools/verify/frontend-modes.mjs    # filter intersection / category-only / random locks the dropdown / serialization round-trip
COMFY_PORT=8189 node tools/verify/queue-roundtrip.mjs   # real queueing: random re-draws twice, Fixed hits the cache, ui.picked returns
COMFY_PORT=8189 node tools/verify/layout.mjs            # layout check: no overflow, grid height, promo row visible
COMFY_PORT=8189 node tools/verify/mode-visibility.mjs   # visibility: each mode shows only its own controls, node height untouched
COMFY_PORT=8189 node tools/verify/custom-import.mjs     # import loop: dialog opens, name/category/angle, same-name merge, clipboard, right-click delete, clean teardown
```

All five rely on a local playwright-core and Chromium; paths are constants at the top of each file. `custom-import.mjs` creates its own test images, uploads them and deletes them again, so `poses/custom/` should be back to its original state afterwards.

---

## Changelog

### v1.0.0 — 2026-10-29

First public release. The repository ships the complete library — `git clone` or the Release archive is all you need.

**Picking and UI**

- Three sampling modes: Fixed / whole-library random / scoped random; parameters appear only in the modes where they apply, so there are no dead controls.
- Fully Chinese UI: parameter names, output name, series / category / pose names (all 288 + 26 translated). No English parameter names, no Japanese source text.
- A single 姿态图 output; no pose-name or pose-info strings, and no seed — click a thumbnail to lock the pose you drew.
- Random modes re-draw on every queue (the node declares `IS_CHANGED`); Fixed still uses the cache.

**Importing your own poses**

- Three entry points — **Import** button, drag-and-drop, `Ctrl+V` — all open the import dialog with name / category / angle.
- Same name with a different angle merges into one pose; same name and same angle is stored as "name (2)".
- Imported images flow into the existing five dropdowns (series 我的姿态), so the node keeps the same parameters and existing workflows still open.
- Dropdowns refresh in place; Fixed mode auto-selects the new image and switches to an angle it actually has; right-click deletes.

**Fixes**

- "Clicking Import does nothing": the import and random buttons used to share a class name, and the random handler overwrote the import button's click handler.
- "The node keeps shrinking itself": the gallery now absorbs whatever height the node has (drag it taller and the grid really shows more rows); switching modes / angles / filters no longer rewrites the node height; the size you drag is remembered in the workflow; trimming old output slots only ever grows the node.

**Size and performance**

- The built-in library ships as WebP: 1439 images at 900×1200 went from 343 MB to 104 MB (PSNR 50.9 dB), taking the whole repository from 370 MB to 105 MB.
- Thumbnails are no longer committed: when `poses/thumbs/` is missing, the node renders each one from the full-size image on first request (57 ms each; the gallery lazy-loads), saving 1439 files.

**Compatibility**

- Old workflows open as-is: leftover output slots are trimmed on load, the missing `seed` value is ignored and the rest map positionally.
- The index is re-read on mtime change, so rebuilding the built-in library no longer needs a restart.
- Aligned with ComfyUI-GuliNodes: node name `GG 姿态库`, category `GuliPoses`, frontend file `web/gg-pose-gallery.js`.

---

## Acknowledgements

This plugin only exists because someone else organised the library first.

### Inspiration and data source

> **Both the idea and the assets behind this project come from the repository below.**
>
> **[anhao/ai-pose-gallery-zh](https://github.com/anhao/ai-pose-gallery-zh)**
> Chinese edition of an AI pose reference gallery · 288 sets / 1439 source images · fully localised · zero-dependency static gallery

- **Idea**: its web gallery — filterable by series / category / angle, with a lightbox and keyboard navigation — came first; "bring that browsing experience into a ComfyUI node" followed. The scoped random mode is essentially its filter logic turned into sampling.
- **Data**: this plugin's `poses/index.json` maps one-to-one onto it — 288 poses, 1439 images, 4 series, 26 categories, 5 angles.
- **Chinese dictionary**: `data/zh-dict.csv` (323 entries) comes from its `data/translations.csv`. Every Chinese category and pose name you see in the node comes from that table; without it this node would still be showing Japanese.
- Its [live demo](https://ai-pose-gallery.anhao.app/) · [GitHub repository](https://github.com/anhao/ai-pose-gallery-zh)

### Original source

- **Original author**: ギア ([@giaaibusi](https://x.com/giaaibusi))
- **Original site**: <https://ai-pose-gallery.pages.dev/>
- **Chinese edition maintained by**: Anhao ([@anhao_ai](https://x.com/anhao_ai))

> Copyright of the images and the source data belongs to the original author, ギア. This plugin only provides **local indexing and in-canvas browsing**; it claims no rights over the images and grants no commercial licence to the original works. If the author believes this project infringes their rights, please open an issue and the content will be removed immediately.

### Companion plugin

- **[guliacer/ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes)** — a ComfyUI efficiency node pack for Chinese-language workflows; this plugin recommends it as the "pipeline enhancement" partner.

### Built with

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — node framework and frontend extension mechanism

---

## License and disclaimer

- The **code** in this plugin (`nodes.py`, `pose_db.py`, `api_routes.py`, `web/`, `tools/`) is released under **MIT**, see [LICENSE](LICENSE).
- That licence **does not cover** the images and source data under `poses/`; their copyright belongs to the original author, ギア.
- The library contains **adult-oriented pose references** (some category names use sexual terminology). It is intended for artistic creation, pose reference and technical study only — do not use it for unlawful purposes. Not for minors.
- This project is not affiliated with any of the source repositories above; it is a personal learning and tooling exercise.
