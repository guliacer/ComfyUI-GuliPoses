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
| You can see what random picked | After execution the node jumps to the pose it actually drew; click a thumbnail to lock it — no seed to remember |
| Import your own poses | **Import** button, drag-and-drop, or `Ctrl+V`, with custom name / category / angle |
| Chinese UI, zero dependencies | Widget labels, output, categories and pose names in Chinese; only the PIL / numpy / torch bundled with ComfyUI |

---

## Installation

```bash
cd ComfyUI/custom_nodes
git clone --depth 1 https://github.com/guliacer/ComfyUI-GuliPoses.git
```

No git? Download the [Release archive](https://github.com/guliacer/ComfyUI-GuliPoses/releases) and extract the `ComfyUI-GuliPoses` folder into `ComfyUI/custom_nodes/`.

Restart ComfyUI, then right-click the canvas → **Add Node** → **GuliPoses** → **GG 姿态库**.

> The repository ships every image (~105 MB), so a clone is all you need. Later `git pull`s only fetch code changes.

---

## The node

**GG 姿态库** (`GuliPosePicker`, category `GuliPoses`)

### Inputs

| Parameter | Active in | Description |
| --- | --- | --- |
| 模式 | always | 固定选中 / 全库随机 / 范围内随机 |
| 姿态 | 固定选中 | 288 poses, e.g. `性感全身 P001 · S形站姿・胯部侧顶` |
| 视角 | always | 正面 / 俯视 / 仰视 / 侧面 / 斜侧 / **随机视角** |
| 筛选系列 | 范围内随机 | 全部 + four series |
| 筛选分类 | 范围内随机 | 全部 + 26 categories |

No `seed` and no `control_after_generate` — this node does not sample, so a seed would mean nothing to it.

**Parameters follow the mode**: only the inputs that actually take effect are shown — a clean three rows in 固定选中, two in whole-library random. Hiding is purely visual, so `widgets_values` keeps its order and workflows save and load as before.

**Node height is yours to decide**: drag it taller and the gallery grows with it, showing more rows. The size is saved into the workflow, and switching modes, angles or filters never snaps it back.

### Outputs

| Output | Description |
| --- | --- |
| 姿态图 | The selected pose image, `900×1200` RGB, float 0–1, batched |

Image only. The pose name and angle are already on the gallery badge.

---

## Sampling modes

| Mode | Draws from | Use when |
| --- | --- | --- |
| 固定选中 | Exact 姿态 + 视角 | You know what you want, or need to reproduce a result |
| 全库随机 | All 288 poses | Batch exploration, reshuffling poses across a set of images |
| 范围内随机 | Intersection of 筛选系列 × 筛选分类 | A themed series that needs variation but must stay in range |

全库随机 ignores both filters; the series dropdown in the gallery greys out.

Both filters in 范围内随机 accept "All". An empty combination never errors, it **silently widens the range** (falls back to series only, then to the whole library) — the `候选 N 个` counter at the bottom of the gallery always shows the pool the backend will really use.

**视角** has six options; 随机视角 draws from the angles that pose *actually has*.

**No seed — how do I pin a result**: random modes draw fresh every time. To keep one, click its thumbnail in the gallery — the mode flips back to 固定选中 and pose plus angle are written into the workflow. Random modes re-draw on every queue (the node declares `IS_CHANGED`); 固定选中 uses the cache.

---

## The gallery

The lower half of the node is a hand-built DOM gallery, six layers top to bottom:

| Layer | Content | Interaction |
| --- | --- | --- |
| Preview | Current selection, badge in the lower-left with `code · category · angle` | — |
| Angle bar | 正面 / 俯视 / 仰视 / 侧面 / 斜侧 | Click to swap every thumbnail to that angle |
| Tool row | Series dropdown · search box · **Import** · **Random** | Filter / search / import your own images / pick one from what's visible |
| Thumbnail grid | Columns follow node width; a lone cell in the last row triggers a balanced re-flow | Click to select |
| Footer | Candidate count on the left, current mode hint on the right | — |
| Promo row | One dim line pointing at the companion plugin | Click opens the ComfyUI-GuliNodes repo |

- The **Random** button picks from what is *currently visible* and switches back to 固定选中 — it pins that exact image into the workflow rather than remembering a seed
- In random mode, a preview outside the current candidate range (e.g. right after changing the filter) dims and gets a `上次 ·` prefix — that is the previous run's result, not an error
- Pose codes repeat across series (`P001` exists in all four), so 姿态 combo labels carry a series prefix

---

## Data

**288 poses × 5 angles = 1439 images** (`full_sexy_P018` has no low-angle shot; selecting it falls back to the front view).

| Series | Poses |
| --- | --- |
| 全身单人-性感系 | 80 |
| 上半身单人 | 80 |
| 全身单人-标准系 | 73 |
| 双人互动 | 55 |

26 action categories (站姿 / 趴卧 / 坐姿 / 跪立・四肢着地 / 贴脸系 …). Category and pose names are fully translated to Chinese; the original Japanese is kept in the `catJp` / `nameJp` fields.

```
data/zh-dict.csv  # Japanese→Chinese dictionary (323 entries)
poses/
├── img/        # full size 900×1200 WebP (104 MB, 1439 files) — shipped
├── thumbs/     # 300×400 thumbnails — not versioned, generated on demand
├── custom/     # your own imported poses (not versioned)
└── index.json  # index, shipped
```

The images live in the repository, so a clone is all you need. Full-size images ship as WebP (q95) rather than PNG: 1439 files cost 343 MB as PNG and 104 MB as WebP, with PSNR 50.9 dB — indistinguishable at 2.3× zoom.

Thumbnails cost the repository nothing: when `poses/thumbs/` is empty, the node renders one from the full-size image on first request and writes it to disk, then serves it from the browser cache. 57 ms each, and the gallery lazy-loads only what is in view.

You only need this command if you replace or add built-in images and want to regenerate the index:

```bash
python tools/build_pose_db.py "D:\path\to\pose-db-01"
```

The script reads `data/poses.csv`, rebuilds `poses/index.json` and translates names through `data/zh-dict.csv`. The index is re-read on mtime change, so no restart is needed.

---

## Importing your own poses

Click **Import** in the tool row, **drag images onto the panel**, or copy an image and press **Ctrl+V** over the canvas — all three open an import dialog. Confirm it and the files land in `poses/custom/`, merged into the index on scan — no rebuild, no restart.

| Field | Purpose |
| --- | --- |
| Name | Display name (defaults to the filename). Several images sharing one name are numbered automatically |
| Category | Pick an existing one or type a new one |
| Angle | Whether the image is 正面 / 俯视 / 仰视 / 侧面 / 斜侧 |

- **One file = one angle**; same name + different angle = one pose with several views, merged into a single cell
- Same name + same angle never overwrites: it is stored as "name (2)" and both images are kept
- Dropdowns refresh in place after an import: 固定选中 auto-selects the new image and switches to an angle it has; random modes just add it to the pool
- **Right-click a custom thumbnail to delete it** — every angle of that pose is removed (confirmation first, deletion is permanent)
- Imported poses join the series **我的姿态** and sort first; display names live in `meta.json`, so renaming breaks old workflows that stored the old name

---

## Companion plugin

### Want more? Install [ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes)

This plugin does one thing: bring the pose library into the canvas. The companion **ComfyUI-GuliNodes** is an efficiency node pack for Chinese-language workflows — **38 nodes, zero extra dependencies**, no conflicts.

| What you want | What GuliNodes has |
| --- | --- |
| The canvas is a mess, nodes don't line up | Toolbar: colour, align, equal width/height, auto spacing, batch tidy |
| Always computing how 1024×1536 aligns to 8 | `GG 图像宽高` / `GG Latent` |
| Batch crop, resize, grade, compare | `GG 图像裁剪` / `GG 图像缩放` / `GG 图像调整` / `GG 色彩校正` |
| Prompts are hard work | `GG 提示词增强qwen2.1` / `GG 提示词优化qwen2.1` |
| VRAM maxed out, models not unloading | `GG 内存清理` |

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/guliacer/ComfyUI-GuliNodes.git
```

Look for the **GG** or **GuliNodes** category in the right-click menu (**GG 姿态库** is this plugin's node and lives under **GuliPoses**).

> Division of labour: GuliPoses decides "which pose", GuliNodes makes "the pipeline smooth".

---

## Changelog

### v1.0.0 — 2026-10-29

First public release. The repository ships the complete library — `git clone` or the Release archive is all you need.

**Picking and UI**

- Three sampling modes: Fixed / whole-library random / scoped random; parameters appear only where they apply.
- Fully Chinese UI: parameter names, output name, series / category / pose names (all 288 + 26 translated).
- A single 姿态图 output and no seed — click a thumbnail to lock the pose you drew.
- Random modes re-draw on every queue; Fixed uses the cache.

**Importing your own poses**

- Three entry points — **Import**, drag-and-drop, `Ctrl+V` — open the import dialog with name / category / angle.
- Same name with a different angle merges into one pose; same name and same angle is stored as "name (2)".
- Imported images flow into the existing five dropdowns, so the node keeps the same parameters and old workflows still open.

**Fixes**

- "Clicking Import does nothing": the import and random buttons used to share a class name, and the random handler overwrote the import button's click handler.
- "The node keeps shrinking itself": the gallery now absorbs whatever height the node has; switching modes / angles / filters no longer rewrites the node size.

**Size and performance**

- The library ships as WebP: 1439 images went from 343 MB to 104 MB, taking the repository from 370 MB to 105 MB.
- Thumbnails are no longer committed: rendered on first request, saving 1439 files.

**Compatibility**

- Old workflows open as-is: leftover output slots are trimmed on load, the missing `seed` value is ignored.
- Aligned with ComfyUI-GuliNodes: node name `GG 姿态库`, category `GuliPoses`.

---

## Acknowledgements

> **Both the idea and the assets behind this project come from the repository below.**
>
> **[anhao/ai-pose-gallery-zh](https://github.com/anhao/ai-pose-gallery-zh)**
> Chinese edition of an AI pose reference gallery · 288 sets / 1439 source images · fully localised · zero-dependency static gallery

- **Idea**: its web gallery — filterable by series / category / angle, with a lightbox and keyboard navigation — is where "bring this into a ComfyUI node" started.
- **Data**: this plugin's `poses/index.json` maps one-to-one onto it — 288 poses, 1439 images, 4 series, 26 categories, 5 angles.
- **Chinese dictionary**: `data/zh-dict.csv` comes from its `data/translations.csv`; every Chinese category and pose name in the node comes from that table.

Original source: **ギア** ([@giaaibusi](https://x.com/giaaibusi)) · <https://ai-pose-gallery.pages.dev/> · Chinese edition maintained by Anhao ([@anhao_ai](https://x.com/anhao_ai))

> Copyright of the images and source data belongs to the original author, ギア. This plugin only provides local indexing and in-canvas browsing and claims no rights over the images. If the author believes this project infringes their rights, please open an issue and the content will be removed immediately.

Companion plugin: [guliacer/ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes) · Framework: [ComfyUI](https://github.com/comfyanonymous/ComfyUI)

---

## License and disclaimer

- The **code** is released under **MIT**, see [LICENSE](LICENSE); that licence **does not cover** the images and source data under `poses/`.
- The library contains **adult-oriented pose references** (some category names use sexual terminology). Intended for artistic creation, pose reference and technical study only. Not for minors.
- This project is not affiliated with any of the source repositories above; it is a personal learning and tooling exercise.
