# ComfyUI-GuliPoses

<!-- Node showcase: swipe left/right (first slide is largest by default; arrows / drag to switch) -->
<div class="gp-showcase">
  <div class="gp-showcase-view">
    <div class="gp-showcase-track">
      <figure class="gp-showcase-slide">
        <img src="docs/screenshots/node-pose.png" alt="GG 姿态库" width="760">
        <figcaption>GG 姿态库 · 288 poses × 5 angles</figcaption>
      </figure>
      <figure class="gp-showcase-slide">
        <img src="docs/screenshots/node-garment.png" alt="GG 服装库" width="760">
        <figcaption>GG 服装库 · 1405 outfits</figcaption>
      </figure>
      <figure class="gp-showcase-slide">
        <img src="docs/screenshots/node-face.jpg" alt="GG 脸模库" width="760">
        <figcaption>GG 脸模库 · 44 face models</figcaption>
      </figure>
    </div>
  </div>
  <div class="gp-showcase-nav">
    <button type="button" class="gp-showcase-prev" aria-label="Previous">‹</button>
    <span class="gp-showcase-dots"></span>
    <button type="button" class="gp-showcase-next" aria-label="Next">›</button>
  </div>
</div>
<style>
.gp-showcase{max-width:780px;margin:0 auto 18px}
.gp-showcase-view{overflow:hidden;border:1px solid #e3e6ec;border-radius:12px;background:#fff}
.gp-showcase-track{display:flex;transition:transform .35s ease;touch-action:pan-y}
.gp-showcase-slide{flex:0 0 100%;margin:0;display:flex;flex-direction:column;align-items:center}
.gp-showcase-slide img{display:block;max-width:100%;max-height:560px;width:auto;height:auto;margin:0 auto}
.gp-showcase-slide figcaption{padding:6px 12px 10px;font-size:12px;color:#5b6470}
.gp-showcase-nav{display:flex;align-items:center;justify-content:center;gap:12px;padding:8px 0}
.gp-showcase-nav button{width:30px;height:30px;border-radius:50%;border:1px solid #d6dae1;background:#fff;color:#333;font-size:17px;line-height:1;cursor:pointer}
.gp-showcase-nav button:hover{border-color:#4f8cff;color:#4f8cff}
.gp-showcase-dots{display:flex;gap:6px}
.gp-showcase-dot{width:8px;height:8px;border-radius:50%;background:#c9ced6;border:0;padding:0;cursor:pointer}
.gp-showcase-dot.on{background:#4f8cff;width:20px;border-radius:4px}
</style>
<script>
(function(){
  document.querySelectorAll('.gp-showcase').forEach(function(root){
    var track=root.querySelector('.gp-showcase-track');
    if(!track) return;
    var n=track.children.length,i=0;
    var dots=root.querySelector('.gp-showcase-dots');
    var prev=root.querySelector('.gp-showcase-prev');
    var next=root.querySelector('.gp-showcase-next');
    var view=root.querySelector('.gp-showcase-view');
    for(var k=0;k<n;k++){(function(k){
      var b=document.createElement('button');b.type='button';b.className='gp-showcase-dot';
      b.setAttribute('aria-label','Slide '+(k+1));
      b.addEventListener('click',function(){go(k);});
      dots.appendChild(b);
    })(k);}
    function go(x){i=(x+n)%n;track.style.transform='translateX('+(-i*100)+'%)';
      for(var k=0;k<dots.children.length;k++){dots.children[k].className='gp-showcase-dot'+(k===i?' on':'');}}
    prev.addEventListener('click',function(){go(i-1);});
    next.addEventListener('click',function(){go(i+1);});
    var sx=0,dx=0,down=false;
    view.addEventListener('touchstart',function(e){sx=e.touches[0].clientX;dx=0;down=true;},{passive:true});
    view.addEventListener('touchmove',function(e){if(down)dx=e.touches[0].clientX-sx;},{passive:true});
    view.addEventListener('touchend',function(){if(down&&Math.abs(dx)>40)go(dx<0?i+1:i-1);down=false;});
    go(0);
  });
})();
</script>

<p align="center"><sub>Swipe / use the arrows · <a href="docs/showcase.html">full-screen preview ↗</a></sub></p>

[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom__nodes-4f8cff)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](#license-and-disclaimer)
[![Poses](https://img.shields.io/badge/pose%20library-288%20sets%20%C2%B7%201439%20images-ff6b6b)](#data)
[![Garments](https://img.shields.io/badge/garment%20library-1405%20sets%20%C2%B7%206%20types-9b6bff)](#data)
[![Faces](https://img.shields.io/badge/face%20library-44%20images%20%C2%B7%20single%20angle-22c55e)](#data)

**Browse a reference library inside a ComfyUI node, pick what you want, and wire it straight into your graph.**

A ComfyUI node for a library of mannequin (3D white-model line-art) pose references — **GG 姿态库** embeds 288 poses × 5 camera angles. Companion nodes **GG 服装库** (1405 outfits, single angle) and **GG 脸模库** (44 face models, single angle, extensible) bring their references into the same in-node gallery. All output an image that plugs directly into ControlNet / Depth / Lineart / IP-Adapter.

> **Your imported images live in `ComfyUI/user/default/guliposes/`, not inside the plugin — upgrades do not touch them.**
> Before upgrading from a version older than **v1.2.2**, do not just delete the folder and reinstall. Either use `git pull` / an overwrite-style install (they migrate automatically), or run `python tools/upgrade.py full --from <new.zip> --purge` — it copies the old material into `user/default/guliposes/`, snapshots it, then replaces the tree, and refuses to delete the originals if any checksum differs. See [Upgrading never deletes your images](#upgrading-never-deletes-your-images).

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

No git? Download the [Release archive](https://github.com/guliacer/ComfyUI-GuliPoses/releases/latest) (`ComfyUI-GuliPoses-v1.2.3.zip`, ~263 MB) and extract the `ComfyUI-GuliPoses` folder into `ComfyUI/custom_nodes/`.

Already running an older version with your own images inside the plugin folder? **Do not delete the folder and reinstall.** Upgrade from the archive with:

```bash
python tools/upgrade.py full --from ComfyUI-GuliPoses-v1.2.3.zip --purge
```

It moves your images into the user data folder first, snapshots them, then replaces the tree.

Restart ComfyUI, then right-click the canvas → **Add Node** → **GuliPoses** → **GG 姿态库**.

> The repository ships every image (~270 MB across pose / garment / face), so a clone is all you need. Later `git pull`s only fetch code changes.

---

## The nodes

All three nodes share the same structure — only the underlying library differs. Parameter names are already Chinese; each outputs a single `IMAGE` for ControlNet / Depth / Lineart / IP-Adapter. Category: `GuliPoses`.

| Node | Node ID | Library | Angles | Output |
| --- | --- | --- | --- | --- |
| GG 姿态库 | `GuliPosePicker` | 288 poses × 5 angles (1439 images, 4 series / 26 categories) | front / high / low / side / diag / random | 姿态图 `900×1200` |
| GG 服装库 | `GuliGarmentPicker` | 1405 outfits (6 types / 20 categories, single angle) | front (control auto-hidden) | 服装图 `1366×2048` |
| GG 脸模库 | `GuliFacePicker` | 44 face models (single angle, extensible) | front (control auto-hidden) | 脸模图 RGB |

### Common inputs

| Param | Active in | Notes |
| --- | --- | --- |
| 模式 | always | fixed / random-all / random-filtered |
| 姿态 / 服装 / 脸模 | fixed | entries of the current library |
| 视角 | always | 6 options for poses; single-angle libraries only "front", control auto-hidden |
| 筛选系列 | random-filtered | all + series of the current library |
| 筛选分类 | random-filtered | all + categories of the current library |

- No `seed`; the node does not sample.
- Inputs follow the mode; only active ones are drawn, `widgets_values` order is unchanged.
- Node height is yours: drag it taller and the gallery grows; switching modes never snaps it back.
- Outputs one image; code / name are on the gallery badge.

### Library differences

- **Garment**: 1405 outfits × single angle; grouped by **garment type** (skirts 440 / dresses 391 / trousers 293 / lingerie 200 / tops 58 / swimwear 23) with 20 sub-categories; the original season lives in `season`, so the search box still finds 春 or 派对, and English keywords work too (`pleated`, `denim`).
- **Face**: 44 bundled by default. The face source set is large and has duplicates, so **only a subset** is included; to get more, drop images (PNG is fine) into `faces/png/` — auto-converted to WebP and re-indexed at load, or run `python tools/build_face_db.py`.

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

### Garment library (GG 服装库)

**1405 outfits × single angle (front) = 1405 images**, grouped by **what the outfit actually is**. The source library is organised by season, which is useless when searching: to find one pleated skirt you had to open spring, summer, autumn and winter in turn. So the library is re-tagged by garment type — the top level drives the series tabs, the second level splits by length / cut / fabric.

| Series | Outfits | Sub-categories (count) |
| --- | --- | --- |
| 半身裙 (Skirts) | 440 | mini 207 / pleated 114 / regular 82 / midi 37 |
| 连衣裙 (Dresses) | 391 | mini 247 / regular 94 / midi 40 / maxi 10 |
| 裤装 (Trousers) | 293 | trousers 182 / jeans 68 / shorts 38 / wide-leg 3 / jumpsuits 2 |
| 内衣·家居 (Lingerie) | 200 | sets 173 / loungewear 27 |
| 上装 (Tops) | 58 | knit 40 / shirts 13 / jackets 3 / camisoles 2 |
| 泳装 (Swimwear) | 23 | swimwear |

Classification reads only the main garment in the English keywords: `dress` means a dress, `skirt` means a skirt, and only then do trousers count. Jackets, cardigans, bags and shoes are layers and never decide the top level — otherwise "knit cardigan + mini skirt" would land in tops. Two exceptions rely on the code prefix: `LNG-` is loungewear (its `shorts` are pyjama bottoms), and only part of `SWM-` actually carries the `swimsuit` keyword.

14 outfits have source keywords that dropped the main garment entirely and list only fabric and accessories (`satin gloves heels`, `grey pleated loafers bag`) — no rule can classify those. They were checked one by one against the pictures and pinned in the `OVERRIDES` table of `tools/garment_classify.py`: 6 satin floor-length gowns go to 连衣裙·长款, 8 wide-leg / straight / jumpsuit bottoms go to trousers. The keyword rules were deliberately not loosened for them — `pleated` usually means trouser pleats, and loosening it would pull ordinary trousers into skirts.

The original season is kept in the `season` field (spring 213 / summer 254 / autumn 244 / winter 253 / lingerie 199 / party 48 / swimwear 54 / sexy 140), so typing 春 or 派对 in the gallery search still filters that batch; the search box also matches English keywords, so `pleated` or `denim` finds them directly.

### Face library (GG 脸模库)

**44 images × single angle (front) = 44 images**, category `脸模`. Source images are PNG, converted to WebP. The face source set is large and has many duplicates, so **only a subset is bundled**. To get more, download images and drop them into the user data folder `face/png/` — they are auto-converted to WebP and the index is rebuilt at load time, or run `python tools/build_face_db.py`.

The face library is likewise a **parallel library**: it reuses the same index schema, gallery, and import/delete logic — only the directory, angle set (single angle) and source differ. Adding another library means one more entry in `pose_db.LIB_DIRS` + a matching `build_*_db.py` + a `GuliXxxPicker` node.

### Layout: what ships with the repo, what belongs to you

**Built-in assets live inside the plugin folder; your assets live outside it.** The split is deliberate — every upgrade path (`git pull`, delete-and-reunzip, ComfyUI-Manager update) only touches the plugin folder, never your data folder.

```
<plugin> ComfyUI/custom_nodes/ComfyUI-GuliPoses/
data/zh-dict.csv  # Japanese→Chinese dictionary (323 entries)
inbox/            # ★ drop image packs here, imported on startup (see "Bulk import")
├── pose/ · garment/ · face/
poses/            # pose library · built-in assets
├── img/            # full size 900×1200 WebP (104 MB, 1439 files)
├── thumbs/         # thumbnails — not versioned, generated on demand
└── index.json      # pose index
garment/          # garment library (sibling of poses/)
├── img/ · thumbs/ · index.json
faces/            # face library (sibling of poses/)
├── img/ · thumbs/ · index.json
└── png/            # deprecated, only a redirect note; images dropped here are ignored

<ComfyUI>/user/default/guliposes/    # ★ your assets, never touched by upgrades
├── 说明_README.txt
├── inbox/           # the second inbox (outside the plugin, upgrade-proof)
├── pose/custom/     # images imported from the node + meta.json + thumbs/
├── pose/png/        # conversion source: drop raw images (PNG/JPG/BMP) here
├── garment/…
└── face/…
```

The built-in images live in the repository, so a clone is all you need. Full-size images ship as WebP (q95) rather than PNG: 1439 files cost 343 MB as PNG and 104 MB as WebP, with PSNR 50.9 dB — indistinguishable at 2.3× zoom.

`<user>/…/<lib>/png/` is only a conversion source: at load time (or via `build_face_db.py`) those files are converted into the plugin's `img/*.webp`. So **losing the converted output to an upgrade is harmless** — your source images stay put and are converted again on the next start.

Thumbnails cost the repository nothing: when `thumbs/` is empty, the node renders one from the full-size image on first request and writes it to disk, then serves it from the browser cache. 57 ms each, and the gallery lazy-loads only what is in view.

You only need these commands if you replace or add built-in images and want to regenerate the index:

```bash
# Rebuild the pose index (reads data/poses.csv, translates through data/zh-dict.csv)
python tools/build_pose_db.py "D:\path\to\pose-db-01"

# Rebuild the garment index (reads the source 原始数据.json / 关键词表.csv, copies WebP into garment/img)
python tools/build_garment_db.py "C:\Users\Admin\Desktop\PS高速缓存\1407套服装穿搭\服装1407"

# Rebuild the face library: convert raw images in the user data face/png/ and write faces/index.json
python tools/build_face_db.py            # keep the original PNGs
python tools/build_face_db.py --clean    # delete the original PNGs after conversion
```

The scripts read the source data, rebuild each `index.json` and copy the images; the index is re-read on mtime change, so no restart is needed.

---

## Upgrading never deletes your images

Your images used to live in the plugin's `poses/custom/`, `garment/custom/`, `faces/custom/` and `faces/png/`. All three upgrade paths could wipe them:

| Upgrade method | What happened |
| --- | --- |
| `git pull` | git leaves untracked files alone, but `git clean -fd` / `git stash -u` removes them |
| Delete the folder and re-unzip | the whole directory is replaced — everything gone |
| ComfyUI-Manager update / reinstall | same as delete-and-reunzip, and it is the common path |

Since v1.2.2 all user assets live in **`ComfyUI/user/default/guliposes/`**, fully separate from the plugin source:

| Your data | Where it lives now |
| --- | --- |
| Images imported from the node + display names/categories (`meta.json`) | `user/default/guliposes/<lib>/custom/` |
| Raw images added in bulk (PNG / JPG / BMP) | `user/default/guliposes/<lib>/png/` |
| Converted output (`img/*.webp`), thumbnails, built-in indexes | inside the plugin — being overwritten is expected, all of it can be regenerated |

**Images you already imported with an older version**: on startup they are copied from the in-plugin `custom/` and `png/` into the new location (originals kept, never moved or deleted), and the log prints `已把 N 个用户素材搬到 …`. You can also run it by hand:

```bash
python tools/userdata.py info      # where the data is, how many files, how large
python tools/userdata.py migrate   # copy into the new location, keep the originals
python tools/userdata.py move      # copy, then delete the originals and clean up the folders
python tools/userdata.py backup    # zip it next to the user data folder
python tools/userdata.py backup --out D:/gg-backup.zip
python tools/userdata.py prune     # list orphan thumbnails whose source image is gone
python tools/userdata.py prune --apply   # actually delete them
```

Run `backup` before upgrading; if anything goes wrong, unzip it back over the user data folder.

**To relocate the data** (say, off a full C: drive), set `GULIPOSES_DATA_DIR` and restart ComfyUI:

```bash
# Windows (persistent user environment variable)
setx GULIPOSES_DATA_DIR "W:\AI\guliposes-data"
```

Resolution order: `GULIPOSES_DATA_DIR` → ComfyUI's user directory (`folder_paths.get_user_directory()`, falling back to `user/` two levels above `custom_nodes/<plugin>`) → in-plugin `userdata/` (last resort, already gitignored). The first line of `python tools/userdata.py info` shows the path actually in use.

### One command to upgrade: move the material out first, then replace the tree

`tools/upgrade.py` turns "protect first, overwrite later" into a single action:

1. **Snapshot** — user data plus everything left in the plugin's old locations, zipped into `user/default/guliposes/_backup/`;
2. **Move material** — files in the plugin's `custom/` and `png/` are copied into `user/default/guliposes/<lib>/`; `meta.json` is **merged**, so display names, categories and angles are not reset to defaults;
3. **Drain inboxes** — image packs that were never imported get imported now;
4. **Verify per file** — sha256 comparison; if anything is missing or differs, it **refuses to delete the originals**;
5. **Replace the tree** — the plugin directory is aligned to the new package (extra files removed, new ones added); `.git`, `.workbuddy*`, `inbox` and `dist` are never touched.

```bash
python tools/upgrade.py check                        # risk report: images left in old spots, un-drained inboxes
python tools/upgrade.py protect                      # copy only, originals untouched
python tools/upgrade.py protect --purge              # copy, verify, then delete the originals
python tools/upgrade.py full --from gg-v1.2.3.zip    # protect + full replacement
python tools/upgrade.py full --from gg-v1.2.3.zip --dry-run   # list what would be deleted / written
```

`--from` accepts a zip or an already-extracted plugin directory. Use `--purge` when you can: it empties the old in-plugin folders so future overwrites have nothing to lose.

Building a release package:

```bash
python tools/pack_release.py            # → dist/ComfyUI-GuliPoses-v<version>.zip
python tools/pack_release.py --list     # list the manifest only
python tools/pack_release.py --deflate  # compress (text shrinks a lot, images are already WebP)
```

The package excludes `.git`, `.workbuddy*`, `__pycache__` — and **your material**: everything under `custom/` and `png/` plus `meta.json` is left out, so it is safe to hand to someone else.

---

## Importing your own poses

Click **Import** in the tool row, **drag images onto the panel**, or copy an image and press **Ctrl+V** over the canvas — all three open an import dialog. Confirm it and the files land in `user/default/guliposes/pose/custom/` (outside the plugin, survives upgrades), merged into the index on scan — no rebuild, no restart.

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

## Bulk import: just drop the folder in

Clicking Import a hundred times is not a workflow. The plugin root has an **inbox** — drop things in, restart ComfyUI, and they are in the library:

```
ComfyUI/custom_nodes/ComfyUI-GuliPoses/inbox/
├── pose/        → pose library, series 我的姿态
├── garment/     → garment library, series 我的服装
├── face/        → face library, series 我的脸模
└── (dropping straight into the inbox root also works — it goes to poses, and the log says so)
```

- **Accepted**: single images, whole folders (searched recursively), zip archives — nested folders inside a zip are fine
- **Ignored**: anything else (readme, txt, psd) stays exactly where it is, nothing is deleted
- **When it runs**: on ComfyUI startup; or immediately with `python tools/import_batch.py --scan`
- **Moved, not copied**: after processing the inbox is empty — the images now live in the library
- Want to pick the library without making a subfolder: `python tools/import_batch.py "D:\pack" --lib garment`

**Angles are detected from the filename.** Trailing angle markers are stripped and same-named files merge into one multi-view pose:

```
poseA_front.png + poseA_side.png + poseA_high.png
        ↓
"poseA" — one pose, 3 angles
```

Accepted: `front` / `side` / `high` / `low` / `diag`, plus the Chinese 正面 / 侧面 / 俯视 / 仰视 / 斜侧. Separators `_`, `-`, space and `·` all work. The garment and face libraries are single-angle: the suffix is still stripped (so display names don't keep a useless `_side`), and the angle simply becomes front.

**There are two inboxes and both are drained**:

| Location | Trade-off |
| --- | --- |
| `custom_nodes/ComfyUI-GuliPoses/inbox/` | convenient, right in the plugin folder — **but an upgrade (delete-and-reinstall) that happens before it is drained will take it with it** |
| `ComfyUI/user/default/guliposes/inbox/` | outside the plugin, upgrades never touch it — the safe one |

Both are drained at the same time and never overwrite each other (collisions get a numeric suffix). Once imported, everything lives in `user/default/guliposes/<lib>/custom/` and stays there.

| Command | What it does |
| --- | --- |
| `python tools/import_batch.py --scan` | drain both inboxes |
| `python tools/import_batch.py "D:\pack" --lib garment` | import a path directly, no inbox involved |
| `python tools/import_batch.py "D:\pack.zip" --lib pose` | same, zip accepted |
| `--cat 分类名` | category to store under, defaults to 自定义 |

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

### v1.2.3 — 2026-10-30

**Bulk import: drop an image pack into the inbox and it lands in the library.**

- New `inbox/pose|garment|face/` at the plugin root: single images, whole folders (recursive) and zip archives all work. Drained on startup, and the sources are **moved**, not copied. Non-image files are left untouched.
- A second inbox lives in the user data folder (`user/default/guliposes/inbox/`); both are drained on every start. Upgrades cannot touch the second one, so use it when you want to be safe.
- Trailing angle markers in filenames are detected (`front` / `side` / `high` / `low` / `diag` and the Chinese equivalents) and same-named files merge into one multi-view pose. The garment and face libraries are single-angle: the suffix is stripped but the angle stays front.
- Manual entry point `tools/import_batch.py`: `--scan` drains the inboxes, or pass a path with `--lib` and `--cat`.
- Copying images straight into `custom/` works too — without a `meta.json` entry the display name and angle are inferred from the filename.
- **Fixed `meta.json` being overwritten during migration**: the old location's metadata is now **merged** into the new one (new location wins on conflicts) instead of replacing it, which used to keep the images but silently reset every display name, category and angle.
- The import dialog in all three nodes now has a line pointing at the inbox for bulk imports.
- Startup messages now go through a single helper with `flush=True`: the old bare `print` was block-buffered whenever ComfyUI's stdout was redirected to a log file, so the "inbox: N images imported" line only landed on disk when the process exited.
- **New `tools/upgrade.py`**: one command runs "snapshot → move material (`meta.json` merged) → drain inboxes → per-file sha256 verify → replace the plugin tree". When verification finds a difference it refuses `--purge`; `.git`, `.workbuddy*`, `inbox` and `dist` are excluded from the replacement. `--dry-run` previews the file operations.
- **New `tools/pack_release.py`**: builds the release zip, excluding `.git`, `.workbuddy*`, `__pycache__`, `userdata/` and user material (images and `meta.json` under `custom/` and `png/`). `__init__.py` now exposes `__version__` for the package name.

### v1.2.2 — 2026-10-30

**Your own images moved out of the plugin folder, so upgrades no longer delete them.** Imported images used to sit in `poses/custom/`, `garment/custom/`, `faces/custom/` and `faces/png/` inside the plugin — `git clean`, delete-and-reunzip and manager updates could all wipe them.

- User assets now live in **`ComfyUI/user/default/guliposes/<lib>/custom/`** (imported images + `meta.json`) and **`…/<lib>/png/`** (raw images added in bulk). Built-in assets (`img/`, `thumbs/`, `index.json`) stay inside the plugin; being overwritten on upgrade is expected.
- On startup the old in-plugin `custom/` and `png/` are **copied** into the new location — originals are kept, never moved or deleted — and the log prints `已把 N 个用户素材搬到 …`. Old plugin versions read the old path, new ones read the new path, so both keep working and a rollback starts with data intact.
- New `tools/userdata.py`: `info` shows locations and file counts, `migrate` copies, `move` copies then deletes originals, `backup` produces a zip.
- New `GULIPOSES_DATA_DIR` environment variable to relocate user data (e.g. off a full C: drive).
- `faces/png/` now only holds a redirect note; images dropped there are ignored. `_raw_pending` / `auto_build` read raw images from the user data `png/`, so even if converted output inside the plugin is overwritten, the sources survive and are reconverted on the next start.
- Migration and `tools/userdata.py` both go through `pose_db.custom_dir()` / `raw_dir()`, so adding a library only needs one `LIB_DIRS` entry — no path edits elsewhere.

### v1.2.1 — 2026-10-30

**Garment library re-tagged by garment type.** It used to be split into eight season series, so finding one pleated skirt meant opening spring, summer, autumn and winter in turn — and the "春" prefix said nothing about what you were looking at.

- Six top-level types: skirts 440 / dresses 391 / trousers 293 / lingerie & loungewear 200 / tops 58 / swimwear 23; 20 sub-categories (mini / midi / maxi / pleated / jeans / shorts / wide-leg / jumpsuits / sets …).
- Rules live in `tools/garment_classify.py` and only read the main garment keyword; jackets and accessories never decide the top level. `LNG-` is forced to lingerie (its `shorts` are pyjama bottoms), and `SWM-` entries without the `swimsuit` keyword are treated as regular summer outfits.
- 14 outfits have keywords that dropped the main garment entirely (`satin gloves heels`, `grey pleated loafers bag`). Each one was checked against its picture and pinned in the `OVERRIDES` table: 6 satin gowns → 连衣裙·长款, 8 wide-leg / straight / jumpsuit bottoms → trousers. The rules were not loosened for them, because `pleated` usually means trouser pleats and loosening it would pull ordinary trousers into skirts.
- `find_pose()` now also extracts the code (`SPR-0001`) from any label and looks the entry up by `code`. When a label has been renamed more than once, the middle version matches neither the current label nor `labelOld` — the code still resolves it.
- `tools/retag_garment.py` re-applies the rules: dry-run by default, `--apply` to write, and it backs up to `.workbuddy-ai/backup-<date>/` first. `tools/build_garment_db.py` now calls the same module, so rebuilding never falls back to seasons.
- The original season is kept in `season` (spring 213 / summer 254 / autumn 244 / winter 253 / lingerie 199 / party 48 / swimwear 54 / sexy 140) — typing 春 or 派对 in the gallery search still filters those; the search box also matches English keywords, so `pleated` and `denim` work.
- `label` changed from `春 SPR-0001` to `半身裙·迷你 SPR-0001`. **Existing workflows need no manual re-pick**: on load, the gallery matches the stored name against `labelOld` and rewrites the widget in place, so the parameter box, the prompt and the saved file all carry the new value. Stale `筛选系列 / 筛选分类` values (`春`, `穿搭`) fall back to `全部` instead of erroring.
- The three node screenshots were retaken on the current UI (the garment one shows `半身裙·迷你 SPR-0001`), and the carousel captions were updated.
- Removed two undecodable bundled images (`SPR-0014`, `SPR-0159` — `Image.load()` raised `could not create decoder object`), 1407 → 1405 outfits.

### v1.2.0 — 2026-10-30

Added the **GG 脸模库** node and auto-conversion of raw images (PNG by default) into the plugin format.

- New node `GuliFacePicker` (display name **GG 脸模库**), same structure as the garment library (single angle, front), 44 bundled face models; the 视角 control is hidden per "don't show inactive inputs".
- New `face` library in `pose_db`; route prefix `/gulifaces/*`. `faces/` is a sibling of `poses/` and `garment/` at the plugin root.
- **Auto-conversion**: `pose_db.auto_build()` scans `faces/png/` (also `faces/` and `faces/img/`), converts PNG (and other formats) to WebP (quality 95, original size) and rebuilds `faces/index.json`; drop images into `faces/png/` and restart ComfyUI. Existing indexes are checked too — new images in `png/`, or WebPs added/removed in `img/`, trigger a rebuild without running any script.
- Auto-built indexes record `imgSig` (file count + newest mtime of `img/`) and rebuild only when it changes. The hand-curated pose/garment indexes have no such field, so their metadata is never overwritten.
- New `tools/build_face_db.py`: manual conversion + index build; `--clean` deletes the original PNGs after conversion.
- Docs note that the face source set is large and only a subset is bundled; download more into `faces/png/`.
- Frontend `web/gg-face-gallery.js` mirrors the garment gallery (dedicated marks `__gpFacePatched` / `__gulifacesApply`).

### v1.1.0 — 2026-10-30

Added the **GG 服装库** node, bringing a garment / outfit reference library into the canvas.

**Multi-library architecture**

- The backend `pose_db` is now an instantiable library (`lib`): `pose` = pose library, `garment` = garment library; the parameterless functions stay as pose shortcuts, so the pose node has zero regressions.
- Routes are isolated by library prefix: `/guliposes/*` (pose) and `/guligarments/*` (garment), each with its own directory and path-traversal protection.
- New node `GuliGarmentPicker` (display name **GG 服装库**) shares the same picking logic as `GuliPosePicker`, differing only in the underlying library.
- Frontend `web/gg-garment-gallery.js` is a twin of the pose gallery, parameterised by node name / route prefix; single-angle libraries (garment) auto-hide the 视角 control and the angle button bar per the "don't show what doesn't apply" rule.

**Garment data**

- 1407 outfits (single angle, front) across eight series: Spring 215 / Summer 254 / Autumn 244 / Winter 253 / Lingerie 199 / Party 48 / Swimwear 54 / Sexy 140.
  (Re-tagged by garment type in v1.2.1: 6 types / 20 categories; the original season stays in `season`.)
- Source images are ~1366×2048 WebP, shipped to `garment/img/` (sibling of `poses/`, at the plugin root); the index is generated by `tools/build_garment_db.py` from the source (原始数据.json + 关键词表.csv), with series names force-mapped to Chinese.
- Supports the same interactions: import your own images, right-click delete, series filter / random (the garment gallery has no search box).

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
- The library contains **adult-oriented content**: the pose library's sexy series and the garment library's sexy / lingerie / swimwear series all involve adult themes. Intended for artistic creation, pose / outfit reference and technical study only. Not for minors.
- This project is not affiliated with any of the source repositories above; it is a personal learning and tooling exercise.
