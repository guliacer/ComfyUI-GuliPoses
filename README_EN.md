# ComfyUI-GuliPoses

<p align="center">
  <a href="docs/showcase.html"><img src="docs/screenshots/node-pose.png" alt="GG Pose Library" width="248"></a>
  <a href="docs/showcase.html"><img src="docs/screenshots/node-garment.png" alt="GG Garment Library" width="248"></a>
  <a href="docs/showcase.html"><img src="docs/screenshots/node-face.jpg" alt="GG Face Library" width="248"></a>
</p>

<p align="center"><sub>GG Pose Library 288 sets × 5 angles ｜ GG Garment Library 1405 outfits ｜ GG Face Library 44 faces — <a href="docs/showcase.html">click any image for the full-screen preview ↗</a></sub></p>

[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom__nodes-4f8cff)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](#license)
[![Poses](https://img.shields.io/badge/pose%20library-288%20sets%20%C2%B7%201439%20images-ff6b6b)](#data)
[![Garments](https://img.shields.io/badge/garment%20library-1405%20sets%20%C2%B7%206%20types-9b6bff)](#data)
[![Faces](https://img.shields.io/badge/face%20library-44%20images%20%C2%B7%20single%20angle-22c55e)](#data)

**Browse reference libraries inside the node, pick one, get an image.**

288 pose sets × 5 angles, 1405 outfits, 44 faces — pick in the gallery and the image goes straight into ControlNet / Depth / Lineart / IP-Adapter.

> Your imported images live in `ComfyUI/user/default/guliposes/`, outside the plugin folder — upgrades never touch them.

中文 · English

---

## Features

| Capability | Notes |
| --- | --- |
| No leaving the canvas | Thumbnail grid sits in the node; one click selects, columns follow node width |
| Three picking modes | Fixed pick for exact reproduction, library-wide random, range random |
| Random results are visible | The node jumps to what it actually picked; click a thumbnail to lock it, no seeds |
| Import your own images | Button, drag-and-drop, or `Ctrl+V`; set name / category / angle |
| Chinese UI, zero deps | Only ComfyUI's bundled PIL / numpy / torch |

---

## Installation

```bash
cd ComfyUI/custom_nodes
git clone --depth 1 https://github.com/guliacer/ComfyUI-GuliPoses.git
```

No git? Grab the [Release archive](https://github.com/guliacer/ComfyUI-GuliPoses/releases/latest) (~263 MB) and extract it into `custom_nodes/`.

Already on an older version with your own images inside the plugin folder? **Don't delete the folder and reinstall** — upgrade like this:

```bash
python tools/upgrade.py full --from ComfyUI-GuliPoses-v1.2.3.zip --purge
```

Restart ComfyUI → right-click the canvas → **GuliPoses** → **GG 姿态库**. All images ship with the repo (~270 MB); later `git pull`s only fetch code.

---

## Nodes

All three share the same structure, only the library differs. Parameters are Chinese, output is one `IMAGE`, category is `GuliPoses`.

| Node | Node ID | Library | Angles | Output |
| --- | --- | --- | --- | --- |
| GG 姿态库 | `GuliPosePicker` | 288 pose sets × 5 angles (1439 images, 4 series / 26 categories) | front / high / low / side / diag / random | `900×1200` |
| GG 服装库 | `GuliGarmentPicker` | 1405 outfits (6 types / 20 categories) | front only (control hidden) | `1366×2048` |
| GG 脸模库 | `GuliFacePicker` | 44 faces, extendable | front only (control hidden) | RGB |

### Shared parameters

| Parameter | Active in | Notes |
| --- | --- | --- |
| 模式 (mode) | all | fixed pick / library-wide random / range random |
| 姿态 / 服装 / 脸模 | fixed pick | entries of the current library |
| 视角 (angle) | all | 6 options for poses; single-angle libraries only show「正面」 |
| 筛选系列 (series) | range random | all + series of the current library |
| 筛选分类 (category) | range random | all + categories of the current library |

- No `seed`; the node does not take part in sampling. Parameters show/hide by mode, `widgets_values` order stays fixed.
- Node height is yours: drag it taller and the gallery shows more rows; switching modes never snaps it back.
- One image out; code and name are shown on the gallery badge.

### Library differences

- **Garment**: six series by outfit type — skirt 440 / dress 391 / pants 293 / innerwear·home 200 / top 58 / swimwear 23, with 20 sub-categories. The original season is kept in `season`, so the search box still finds「春」「派对」and English keywords (`pleated`, `denim`).
- **Face**: 44 by default, only a subset adapted. Want more? Drop images into `face/png/` under the user data folder; they are converted to WebP and the index is rebuilt on load.

---

## Picking modes

| Mode | Draws from | Use it for |
| --- | --- | --- |
| Fixed pick | exact「姿态」+「视角」 | you know the pose, or need to reproduce a result |
| Library-wide random | all 288 poses | batch exploration |
| Range random | intersection of series × category | a themed batch that still varies |

- Series/category are ignored in library-wide mode; the dropdown greys out.
- An empty combination does not error — it **silently widens** (series only, then whole library). The「候选 N 个」counter at the bottom shows the real pool.
- Random modes re-roll on every queue (`IS_CHANGED`, never cached); fixed pick uses the cache. To keep a result, click its thumbnail — mode switches to fixed pick and both pose and angle are written into the workflow.

---

## Gallery

The lower half of the node is a hand-drawn DOM gallery, six layers top to bottom:

| Layer | Content | Action |
| --- | --- | --- |
| Preview | current selection, badge `code · category · angle` | — |
| Angle bar | front / high / low / side / diag | one click swaps the whole grid |
| Tool row | series · search ·「导入」·「随机」 | filter / search / import / pick within view |
| Grid | columns follow node width, last row auto-balances | click to select |
| Footer | candidate count, current mode | — |
| Recommend | one line pointing at ComfyUI-GuliNodes | opens the repo |

- 「随机」picks within the **currently visible** range and switches to fixed pick — it pins that image into the workflow.
- If the preview is outside the current candidates (you just changed a filter), it dims and the badge gains a「上次 · 」prefix — that is the previous run, not an error.
- Pose codes repeat across series (`P001` exists in four), so the dropdown carries the series prefix.

---

## Data

**288 pose sets × 5 angles = 1439 images** (`full_sexy_P018` has no「仰视」; that angle falls back to front).

| Series | Poses |
| --- | --- |
| 全身单人-性感系 | 80 |
| 上半身单人 | 80 |
| 全身单人-标准系 | 73 |
| 双人互动 | 55 |

26 action categories, all names translated to Chinese with the Japanese original kept in `catJp` / `nameJp`.

### Garment library

**1405 outfits × single angle = 1405 images.** The source library was organised by season, so finding one pleated skirt meant four tabs — it is now organised by garment type: the first level picks the series, the second is the sub-type (length / cut / material).

| Series | Outfits | Sub-categories |
| --- | --- | --- |
| Skirt | 440 | mini 207 / pleated 114 / regular 82 / midi 37 |
| Dress | 391 | mini 247 / regular 94 / midi 40 / long 10 |
| Pants | 293 | long 182 / denim 68 / shorts 38 / wide 3 / jumpsuit 2 |
| Innerwear·home | 200 | set 173 / loungewear 27 |
| Top | 58 | knit 40 / shirt 13 / coat 3 / camisole 2 |
| Swimwear | 23 | swimwear |

- Classification looks only at the main garment keyword: `dress` → dress, `skirt` → skirt, otherwise pants; coats, bags and shoes never decide the first level.
- 14 outfits had the main keyword missing entirely; after checking each image they are pinned in `OVERRIDES` in `tools/garment_classify.py` (6 satin gowns → dress·long, 8 wide / straight / jumpsuit → pants).
- The original season stays in `season` (spring 213 / summer 254 / autumn 244 / winter 253 / innerwear 199 / party 48 / swimwear 54 / sexy 140) and is still searchable.

### Face library

**44 faces × single angle = 44 images**, all under the category「脸模」. Source images are PNG, converted to WebP.

It is a "parallel library" like garments: same index schema, gallery and import/delete logic, only the folder, angle set and source images differ. Adding a library = one entry in `pose_db.LIB_DIRS` + one `build_*_db.py` + one `GuliXxxPicker`.

### Layout

**Bundled assets live inside the plugin, your own assets live outside it** — upgrades only touch the plugin folder.

```
<plugin> ComfyUI/custom_nodes/ComfyUI-GuliPoses/
data/zh-dict.csv  # JP→ZH dictionary
inbox/            # ★ inbox: drop image packs here, imported on startup
poses/            # pose library · img/ thumbs/ index.json
garment/          # garment library · same
faces/            # face library · same; png/ is deprecated, keeps only a guide

<ComfyUI>/user/default/guliposes/   # ★ your assets, never touched by upgrades
├── inbox/           # second inbox, the safest one
├── pose/custom/     # imported images + meta.json + thumbs/
├── pose/png/        # conversion source: raw images go here
├── garment/…  face/…
```

- Images are WebP (q95), not PNG: same 1439 files, 343 MB as PNG vs 104 MB as WebP.
- `<lib>/png/` is only a conversion source; the index reads WebP from `img/`. Converted output being overwritten is fine — your source images stay put and are re-converted on next start.
- Thumbnails are not shipped; an empty `thumbs/` is filled on first request (57 ms each), then served from browser cache.

Rebuild indexes only if you replaced or added bundled images:

```bash
python tools/build_pose_db.py "D:\path\to\pose-db-01"     # pose
python tools/build_garment_db.py "…\服装1407"              # garment
python tools/build_face_db.py [--clean]                   # face, --clean removes source PNGs
```

---

## Upgrades never delete your images

Your material lives in **`ComfyUI/user/default/guliposes/`**; the plugin folder only holds bundled images (overwritten on upgrade, rebuildable).

| What | Where |
| --- | --- |
| Imported images + display name / category | `user/default/guliposes/<lib>/custom/` |
| Raw images added in bulk | `user/default/guliposes/<lib>/png/` |
| Converted output, thumbnails, bundled index | inside the plugin, rebuildable |

Material left in old in-plugin locations is copied on startup (copy only, originals kept, `meta.json` merged):

```bash
python tools/userdata.py info      # how many files in each location
python tools/userdata.py migrate   # copy to the new location, keep originals
python tools/userdata.py move      # copy, then delete originals
python tools/userdata.py backup    # zip it
python tools/userdata.py prune     # list orphan thumbnails, --apply to delete
```

Move it off C: with `setx GULIPOSES_DATA_DIR "W:\AI\guliposes-data"`, then restart. Resolution order: env var → ComfyUI user dir → in-plugin `userdata/`.

### One-command upgrade

```bash
python tools/upgrade.py check                       # images left in old spots, un-drained inboxes
python tools/upgrade.py protect                     # copy only, originals untouched
python tools/upgrade.py protect --purge             # copy, verify, then delete originals
python tools/upgrade.py full --from gg-v1.2.3.zip   # protect + full replacement
```

`--from` accepts a zip or an extracted folder. It does five things in order: snapshot → move material (`meta.json` merged) → drain inboxes → per-file sha256 verify (refuses to delete originals on any difference) → align the plugin tree (`.git`, `.workbuddy*`, `inbox`, `dist` untouched).

Build your own release package:

```bash
python tools/pack_release.py            # → dist/ComfyUI-GuliPoses-v<version>.zip
python tools/pack_release.py --list     # manifest only
```

No `.git`, no `__pycache__`, and **no user material** (`custom/`, `png/` images and `meta.json` are excluded) — safe to hand to someone else.

---

## Import your own images

Click「导入」, drag images onto the panel, or press `Ctrl+V` on the canvas — all three open the import dialog. Images land in `user/default/guliposes/pose/custom/` and join the index on the next scan; no rebuild, no restart.

| Field | Purpose |
| --- | --- |
| Name | display name (defaults to filename); shared names get numbered |
| Category | pick an existing one or type a new one |
| Angle | front / high / low / side / diag |

- **One file = one angle**; same name + different angle merges into one entry, same name + same angle is saved as「名称 (2)」— nothing is overwritten.
- After import the node selects the new image and switches to an angle it actually has; random modes just add it to the pool.
- **Right-click a custom thumbnail to delete**, removing every angle of that pose (with confirmation).
- Everything lands in series「我的姿态」, sorted first; display names live in `meta.json`.

---

## Bulk import

No clicking through hundreds of files. Drop them into the **inbox** and restart ComfyUI:

```
ComfyUI/custom_nodes/ComfyUI-GuliPoses/inbox/
├── pose/      → pose library, series「我的姿态」
├── garment/   → garment library
├── face/      → face library
└── the root also works, treated as poses
```

- **Accepted**: single images, whole folders (recursive), zip archives (any nesting).
- **Not touched**: everything else (readme, txt, psd) stays where it is.
- Drained files are **moved**, not copied; skip the restart with `python tools/import_batch.py --scan`.

**Multi-angle detection**: a filename ending in `front` / `side` / `high` / `low` / `diag` (or the Chinese equivalents, separators `_` `-` space `·`) has the suffix stripped and same-named files merged into one multi-angle pose. Single-angle libraries still strip the suffix but keep the angle at front.

| Inbox location | Notes |
| --- | --- |
| `custom_nodes/ComfyUI-GuliPoses/inbox/` | convenient, **but a delete-and-reinstall upgrade removes un-drained files** |
| `ComfyUI/user/default/guliposes/inbox/` | outside the plugin, safest |

| Command | Purpose |
| --- | --- |
| `python tools/import_batch.py --scan` | drain both inboxes |
| `python tools/import_batch.py "D:\pack" --lib garment` | import a path directly (folder or zip) |
| `--cat name` | category to use, default「自定义」 |

---

## Companion plugin

This plugin only moves a pose library into the canvas. **[ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes)** is a Chinese-workflow utility collection — 38 nodes, zero extra dependencies, no conflicts.

| You want | GuliNodes has |
| --- | --- |
| Tidy the canvas, align nodes | toolbar: colour, align, equal size, auto spacing, batch tidy |
| Get 1024×1536 to line up to 8 | `GG 图像宽高` / `GG Latent` |
| Batch crop, resize, colour | `GG 图像裁剪` / `GG 图像缩放` / `GG 色彩校正` |
| Prompt writing | `GG 提示词增强qwen2.1` / `GG 提示词优化qwen2.1` |
| Free VRAM, unload models | `GG 内存清理` |

```bash
cd ComfyUI/custom_nodes && git clone https://github.com/guliacer/ComfyUI-GuliNodes.git
```

Look for the **GG** or **GuliNodes** category in the right-click menu (this plugin lives under **GuliPoses**).

---

## Changelog

### v1.2.3 — 2026-10-30

- Added the garment library (1405 outfits / 6 types) and face library (44 faces); three nodes now.
- Garment library regrouped by outfit type instead of season.
- User material moved to `user/default/guliposes/`; upgrades no longer overwrite it.
- Old in-plugin material migrates on startup; `meta.json` is merged, not replaced.
- New inbox: drop packs into `inbox/`, restart, imported — folders and zip included.
- Angle suffixes in filenames are detected and same-named files merge into multi-angle poses.
- New `upgrade.py`: move material first, verify, then replace the tree.
- New `pack_release.py`: builds the release zip without user material.
- New `userdata.py` and `import_batch.py` management scripts.
- Startup log now flushes, so redirected logs show it too.
- Fixed `meta.json` being overwritten during migration and orphan thumbnails after deletion.

### v1.0.0 — 2026-10-29

- First release: pose library with 288 sets × 5 angles, pick inside the gallery.
- Three picking modes: fixed pick / library-wide random / range random.
- Import your own images (button / drag-and-drop / `Ctrl+V`).
- Bundled images switched to WebP, repository 370 MB → 105 MB.
- Thumbnails no longer shipped, generated on first browse.

---

## Credits

Library and Chinese data come from **[anhao/ai-pose-gallery-zh](https://github.com/anhao/ai-pose-gallery-zh)**: `poses/index.json` maps one-to-one (288 sets / 1439 images / 4 series / 26 categories / 5 angles), and `data/zh-dict.csv` comes from its `data/translations.csv`.

Original source: **ギア** ([@giaaibusi](https://x.com/giaaibusi)) · <https://ai-pose-gallery.pages.dev/> · Chinese edition maintained by Anhao ([@anhao_ai](https://x.com/anhao_ai))

> Images and original data remain the property of their author. This plugin only indexes them locally and browses them inside the canvas, claiming no rights over the images. If the author objects, open an issue and the content will be removed.

Companion: [guliacer/ComfyUI-GuliNodes](https://github.com/guliacer/ComfyUI-GuliNodes) · Framework: [ComfyUI](https://github.com/comfyanonymous/ComfyUI)

---

## License

- The **code** is MIT, see [LICENSE](LICENSE); that licence **does not** cover the images and source data under `poses/`.
- The library contains **adult-oriented content**: the sexy pose series and the sexy / innerwear / swimwear garment series are for artistic creation, pose and outfit reference, and technical study only. Not for minors.
- This project is not affiliated with any of the source repositories above.
