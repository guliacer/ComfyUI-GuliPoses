import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_NAME = "GuliFacePicker";
// 画廊高度不写死：跟随节点高度（用户拉多高，画廊就多高）。
// 这三个常量用来算「除画廊以外占掉多少」，实测口径见 AGENTS.md：
// 固定选中 696 = 586 画廊 + 110 外框，其中 110 = 38（标题栏+内边距）+ 3 行 × 24。
const GALLERY_HEIGHT = 586; // 默认画廊高度（440 宽 / 固定选中时的量值）
const MIN_GALLERY_H = 240; // 再拉矮也不会比这个更小
const NODE_CHROME_H = 38; // 标题栏 + 节点内边距
const PARAM_ROW_H = 24; // 一个参数行：widget 20 + 间距 4

const MODE_FIXED = "固定选中";
const MODE_RANDOM_ALL = "全库随机";
const MODE_RANDOM_FILTERED = "范围内随机";
const ALL = "全部";

const CSS = `
.gp-root{
  --gp-bg:var(--comfy-menu-bg,#1e2128);
  --gp-panel:var(--comfy-input-bg,#12141a);
  --gp-fg:var(--input-text,#e6e8ee);
  --gp-dim:var(--descrip-text,#96a0b0);
  --gp-line:var(--border-color,#39404d);
  --gp-ac:#4f8cff;
  box-sizing:border-box;height:100%;position:relative;display:flex;flex-direction:column;gap:6px;padding:6px;
  background:var(--gp-bg);color:var(--gp-fg);border-radius:6px;overflow:hidden;
  font:12px/1.35 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
}
.gp-root *{box-sizing:border-box}
/* 预览区高度不写死：由 layoutStage() 按节点剩余高度算出来，跟随节点高度放大。
   flex:0 0 auto 让内联 height 生效，栅格仍用 flex:1 吃掉剩下空间。 */
.gp-stage{position:relative;flex:0 0 auto;display:flex;align-items:center;justify-content:center;
  background:#fff;border:1px solid var(--gp-line);border-radius:8px;overflow:hidden}
.gp-stage-img{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.gp-stage-img img{max-width:100%;max-height:100%;object-fit:contain;display:block}
.gp-stage[data-stale="1"] .gp-stage-img{opacity:.4}
.gp-stage .gp-empty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#8b93a1;font-size:12px}
.gp-badge{position:absolute;left:6px;top:6px;z-index:2;padding:2px 7px;border-radius:5px;
  background:rgba(14,16,20,.72);color:#fff;font-size:11px;letter-spacing:.02em;pointer-events:none}
/* 预览区底部的缩放滑块：拖节点变高时滑块还在，手动也能调预览占画廊的比例 */
.gp-stage-ctrl{position:absolute;left:6px;right:6px;bottom:6px;z-index:2;display:flex;align-items:center;gap:6px;
  background:rgba(14,16,20,.5);border-radius:6px;padding:3px 8px;backdrop-filter:blur(2px)}
.gp-stage-ctrl[hidden]{display:none}
.gp-stage-ctrl span{flex:0 0 auto;color:#fff;font-size:11px;opacity:.85;pointer-events:none}
.gp-stage-range{flex:1 1 auto;min-width:0;height:14px;accent-color:var(--gp-ac);cursor:pointer}
.gp-stage-range::-webkit-slider-thumb{accent-color:var(--gp-ac)}
.gp-angles{display:flex;gap:4px}
.gp-abtn{flex:1;height:26px;border-radius:6px;border:1px solid var(--gp-line);
  background:var(--gp-panel);color:var(--gp-fg);font-size:12px;cursor:pointer;padding:0;transition:.12s}
.gp-abtn:hover{border-color:var(--gp-ac)}
.gp-abtn[data-on="1"]{background:var(--gp-ac);border-color:var(--gp-ac);color:#fff}
.gp-tools{display:flex;gap:4px}
.gp-tools select,.gp-tools input{height:26px;border-radius:6px;border:1px solid var(--gp-line);
  background:var(--gp-panel);color:var(--gp-fg);font-size:12px;padding:0 6px;min-width:0}
.gp-tools select{flex:0 0 92px}
.gp-tools input{flex:1 1 auto}
.gp-tools input::placeholder{color:var(--gp-dim)}
.gp-tools input:focus,.gp-tools select:focus{outline:1px solid var(--gp-ac);outline-offset:-1px}
.gp-btn{flex:0 0 auto;height:26px;padding:0 9px;border-radius:6px;border:1px solid var(--gp-line);
  background:var(--gp-panel);color:var(--gp-fg);font-size:12px;cursor:pointer}
.gp-btn:hover{border-color:var(--gp-ac)}
.gp-grid{flex:1 1 auto;min-height:0;overflow-y:auto;display:grid;gap:4px;padding:6px;
  grid-template-columns:repeat(auto-fill,minmax(58px,1fr));grid-auto-rows:max-content;align-content:start;
  background:var(--gp-panel);border-radius:8px;border:1px solid var(--gp-line)}
.gp-grid::-webkit-scrollbar{width:8px}
.gp-grid::-webkit-scrollbar-thumb{background:#3c4351;border-radius:4px}
.gp-cell{position:relative;aspect-ratio:3/4;border-radius:5px;overflow:hidden;cursor:pointer;
  background:#fff;border:1px solid transparent}
.gp-cell img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.gp-cell:hover{border-color:var(--gp-ac)}
.gp-cell[data-on="1"]{border-color:var(--gp-ac);box-shadow:0 0 0 2px rgba(79,140,255,.4)}
.gp-foot{flex:0 0 auto;display:flex;justify-content:space-between;gap:8px;color:var(--gp-dim);font-size:11px}
.gp-promo{flex:0 0 auto;display:flex;justify-content:flex-end;align-items:center;gap:3px;
  font-size:11px;line-height:1.1;color:var(--gp-fg);opacity:.55;padding:0 2px 1px;transition:opacity .12s}
.gp-promo:hover{opacity:.95}
.gp-promo a{color:inherit;text-decoration:none;cursor:pointer;border-bottom:1px dotted transparent;
  transition:color .12s,border-color .12s}
.gp-promo a:hover{color:var(--gp-ac);border-bottom-color:var(--gp-ac)}
.gp-msg{flex:1;display:flex;align-items:center;justify-content:center;color:var(--gp-dim);padding:12px;text-align:center}
.gp-root[data-drop="1"] .gp-grid{outline:2px dashed var(--gp-ac);outline-offset:-4px}
.gp-root[data-busy="1"] .gp-grid,.gp-root[data-busy="1"] .gp-imp{opacity:.5;pointer-events:none}
.gp-root[data-busy="1"] .gp-dlg-box{opacity:.55;pointer-events:none}
.gp-dlg{position:absolute;inset:0;z-index:6;display:flex;align-items:center;justify-content:center;
  padding:8px;background:rgba(8,10,14,.6)}
.gp-dlg[hidden]{display:none}
.gp-dlg-box{box-sizing:border-box;width:100%;max-height:100%;overflow:auto;display:flex;flex-direction:column;
  gap:8px;padding:10px;background:var(--gp-bg);border:1px solid var(--gp-line);border-radius:8px;
  box-shadow:0 10px 28px rgba(0,0,0,.5)}
.gp-dlg-box *{box-sizing:border-box}
.gp-dlg-head{display:flex;align-items:center;justify-content:space-between;font-size:12px;font-weight:600}
.gp-dlg-x{border:0;background:transparent;color:var(--gp-fg);opacity:.55;font-size:15px;line-height:1;
  padding:2px 5px;cursor:pointer;border-radius:4px}
.gp-dlg-x:hover{opacity:1}
.gp-dlg-pick{display:flex;align-items:center;gap:6px}
.gp-dlg-pick button{flex:0 0 auto;height:26px;padding:0 9px;border-radius:6px;border:1px solid var(--gp-line);
  background:var(--gp-panel);color:var(--gp-fg);font-size:12px;cursor:pointer}
.gp-dlg-pick button:hover{border-color:var(--gp-ac)}
.gp-dlg-count{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:11px;color:var(--gp-fg);opacity:.55}
.gp-dlg-preview{height:118px;display:flex;align-items:center;justify-content:center;overflow:hidden;
  background:#fff;border:1px solid var(--gp-line);border-radius:6px;color:#8b93a1;font-size:12px}
.gp-dlg-preview img{max-width:100%;max-height:100%;object-fit:contain;display:block}
.gp-dlg-row{display:flex;align-items:center;gap:6px;font-size:12px}
.gp-dlg-row > span{flex:0 0 32px;color:var(--gp-fg);opacity:.7}
.gp-dlg-row input,.gp-dlg-row select{flex:1 1 auto;min-width:0;height:26px;border-radius:6px;
  border:1px solid var(--gp-line);background:var(--gp-panel);color:var(--gp-fg);font-size:12px;padding:0 6px}
.gp-dlg-row input::placeholder{color:var(--gp-fg);opacity:.4}
.gp-dlg-row input:focus,.gp-dlg-row select:focus{outline:1px solid var(--gp-ac);outline-offset:-1px}
.gp-dlg-row input:disabled{opacity:.55}
.gp-dlg-hint{min-height:15px;font-size:11px;line-height:1.35;color:var(--gp-fg);opacity:.55}
.gp-dlg-bulk{font-size:11px;line-height:1.4;color:var(--gp-fg);opacity:.45}
.gp-dlg-foot{display:flex;justify-content:flex-end;gap:6px}
.gp-dlg-foot button{height:26px;padding:0 14px;border-radius:6px;border:1px solid var(--gp-line);
  background:var(--gp-panel);color:var(--gp-fg);font-size:12px;cursor:pointer}
.gp-dlg-foot button:hover{border-color:var(--gp-ac)}
.gp-dlg-foot .gp-dlg-ok{background:var(--gp-ac);border-color:var(--gp-ac);color:#fff}
.gp-dlg-foot .gp-dlg-ok:hover{filter:brightness(1.08)}
.gp-dlg-foot button:disabled{opacity:.5;cursor:default}
`;

function injectCSS() {
	if (document.getElementById("gulifaces-style")) return;
	const el = document.createElement("style");
	el.id = "gulifaces-style";
	el.textContent = CSS;
	document.head.append(el);
}

let dbPromise = null;
function loadDB() {
	if (!dbPromise) {
		dbPromise = api
			.fetchApi("/gulifaces/index.json")
			.then((res) => {
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				return res.json();
			})
			.catch((err) => {
				dbPromise = null;
				throw err;
			});
	}
	return dbPromise;
}

/** 图片地址：内置库走 /gulifaces/*，自定义库走 /gulifaces/custom/*。 */
function fileURL(pose, kind, name) {
	const base = pose && pose.root === "custom" ? "/gulifaces/custom" : "/gulifaces";
	return api.apiURL(`${base}/${kind}/${encodeURIComponent(name)}`);
}

/** 取某脸模在某角度下的图片名，缺图时回退到正面。 */
function fileFor(pose, angle, kind) {
	const entry = pose.angles[angle] ?? pose.angles.front;
	return entry ? entry[kind] : null;
}

function setup(node) {
	injectCSS();

	const w = (name) => node.widgets?.find((x) => x.name === name);
	const modeWidget = w("模式");
	const poseWidget = w("脸模");
	const angleWidget = w("视角");
	const seriesWidget = w("筛选系列");
	const catWidget = w("筛选分类");
	if (!modeWidget || !poseWidget || !angleWidget || !seriesWidget || !catWidget) return;

	const root = document.createElement("div");
	root.className = "gp-root";
	root.innerHTML = `
		<div class="gp-stage">
			<div class="gp-stage-img"><span class="gp-empty">载入脸模库…</span></div>
			<div class="gp-badge" hidden></div>
			<div class="gp-stage-ctrl" hidden>
				<span>预览</span>
				<input class="gp-stage-range" type="range" min="15" max="85" step="1" value="55"
					title="拖动调整预览图占节点高度的比例；拉高节点预览会跟着变大">
			</div>
		</div>
		<div class="gp-angles"></div>
		<div class="gp-tools">
			<select class="gp-series" title="按系列筛选"></select>
			<button class="gp-btn gp-imp" type="button"
				title="导入自己的脸模图（点这里选图，或按 Ctrl+V 粘贴、把图片拖进面板）">导入</button>
			<button class="gp-btn gp-shuffle" type="button" title="随机挑一个（切回固定选中）">随机</button>
		</div>
		<div class="gp-grid"></div>
		<div class="gp-foot"><span class="gp-count"></span><span class="gp-hint"></span></div>
		<div class="gp-promo">
			<span>需要画布整理 / 提示词增强？</span>
			<a class="gp-promo-link" href="https://github.com/guliacer/ComfyUI-GuliNodes"
				target="_blank" rel="noopener noreferrer"
				title="ComfyUI-GuliNodes — 38 个中文效率节点，零额外 Python 依赖">装 GuliNodes ↗</a>
		</div>
		<div class="gp-dlg" hidden>
			<div class="gp-dlg-box">
				<div class="gp-dlg-head">导入脸模图<button class="gp-dlg-x" type="button" title="关闭">×</button></div>
				<div class="gp-dlg-pick">
					<button class="gp-dlg-file" type="button">选择文件…</button>
					<button class="gp-dlg-clip" type="button" title="读系统剪贴板里的图片">从剪贴板</button>
					<span class="gp-dlg-count"></span>
				</div>
				<div class="gp-dlg-preview"></div>
				<label class="gp-dlg-row"><span>名称</span>
					<input class="gp-dlg-name" type="text" maxlength="60"></label>
				<label class="gp-dlg-row"><span>分类</span>
					<input class="gp-dlg-cat" type="text" maxlength="60" list="gp-cat-list"
						placeholder="选一个，或直接输入新分类"></label>
				<label class="gp-dlg-row"><span>视角</span>
					<select class="gp-dlg-angle"></select></label>
				<datalist id="gp-cat-list"></datalist>
				<div class="gp-dlg-hint"></div>
				<div class="gp-dlg-bulk">整包导入：把图片文件夹或 zip 丢进插件目录的 <b>inbox/face/</b>，重启 ComfyUI 自动入库（单角度库，文件名后缀会去掉）</div>
				<div class="gp-dlg-foot">
					<button class="gp-dlg-cancel" type="button">取消</button>
					<button class="gp-dlg-ok" type="button">导入</button>
				</div>
			</div>
		</div>`;

	const stage = root.querySelector(".gp-stage");
	const anglesBar = root.querySelector(".gp-angles");
	const seriesSel = root.querySelector(".gp-series");
	const grid = root.querySelector(".gp-grid");
	const countEl = root.querySelector(".gp-count");
	const hintEl = root.querySelector(".gp-hint");

	// 选图对话框不上屏，点「选择文件…」再叫出来
	const fileInput = document.createElement("input");
	fileInput.type = "file";
	fileInput.accept = "image/*";
	fileInput.multiple = true;
	fileInput.style.display = "none";
	root.append(fileInput);

	const importBtn = root.querySelector(".gp-imp");
	const shuffleBtn = root.querySelector(".gp-shuffle");
	const dlg = root.querySelector(".gp-dlg");
	const dlgBody = dlg.querySelector(".gp-dlg-box");
	const dlgName = dlg.querySelector(".gp-dlg-name");
	const dlgCat = dlg.querySelector(".gp-dlg-cat");
	const dlgCatList = dlg.querySelector("#gp-cat-list");
	const dlgAngle = dlg.querySelector(".gp-dlg-angle");
	const dlgPreview = dlg.querySelector(".gp-dlg-preview");
	const dlgCount = dlg.querySelector(".gp-dlg-count");
	const dlgHint = dlg.querySelector(".gp-dlg-hint");
	const dlgOk = dlg.querySelector(".gp-dlg-ok");

	const gallery = node.addDOMWidget("gulipose_gallery", "gulipose_gallery", root, {
		serialize: false,
		hideOnZoom: false,
		getMinHeight: () => MIN_GALLERY_H,
	});

	/** 除画廊外还占掉多少高度：标题栏 + 内边距 + 当前可见的参数行。 */
	function chromeHeight() {
		let rows = 0;
		for (const widget of node.widgets ?? []) {
			if (widget === gallery || widget.hidden) continue;
			rows += 1;
		}
		return NODE_CHROME_H + rows * PARAM_ROW_H;
	}

	// 画廊吃掉节点剩下的高度：拉高节点 → 画廊跟着变高 → 栅格多显示几行。
	// node.computeSize() 求和时又回到 node.size[1]，自洽，不会递归。
	gallery.computeSize = (width) => [
		width ?? node.size[0],
		Math.max(MIN_GALLERY_H, node.size[1] - chromeHeight()),
	];

	// ---------- 预览图尺寸：跟随节点高度 + 手动可调 ----------
	// previewFrac = 预览区占「非栅格剩余空间」的比例。节点拉越高，剩余空间越大，
	// 预览区就跟着越大（像其他图像节点那样）；滑块改 previewFrac 做手动微调。
	const PREVIEW_MIN = 120;
	let previewFrac = 0.55;
	const stageRange = stage.querySelector(".gp-stage-range");

	/** 算出预览区该多高：排除栅格与自身，其余兄弟（工具条/页脚/推广）高度相加，
	 *  再加 gap 与 padding，得到可用高度，再乘比例。不读栅格高度，避免反馈振荡。 */
	function layoutStage() {
		const avail = root.clientHeight;
		if (avail <= 0) return; // 还没上屏，等 ResizeObserver 再来
		let other = 0;
		for (const child of root.children) {
			if (child === stage || child === grid) continue;
			other += child.offsetHeight;
		}
		const gap = 6 * (root.children.length - 1);
		const pad = 12; // 6*2
		const usable = Math.max(0, avail - other - gap - pad);
		const h = Math.max(PREVIEW_MIN, Math.round(previewFrac * usable));
		stage.style.height = `${h}px`;
	}

	if (stageRange) {
		stageRange.value = Math.round(previewFrac * 100);
		stageRange.oninput = () => {
			previewFrac = Number(stageRange.value) / 100;
			layoutStage();
		};
	}

	// 节点被拖高/拖矮时 root 高度变化，重新分配预览高度。用 rAF 合并连续回调。
	let stageRaf = 0;
	if (typeof ResizeObserver !== "undefined") {
		new ResizeObserver(() => {
			cancelAnimationFrame(stageRaf);
			stageRaf = requestAnimationFrame(layoutStage);
		}).observe(root);
	}

	const st = {
		db: null,
		angle: "front",
		localSeries: "all",
		query: "",
		sel: null,
		stale: false,
		notice: "",
		lastCat: "", // 上次导入用的分类，下次打开对话框默认沿用
		cells: new Map(),
	};

	// ---------- 与节点原生控件同步 ----------
	const setWidget = (widget, value) => {
		if (widget.value === value) return;
		widget.value = value;
		widget.callback?.(value);
		// 程序化改值不会触发重绘，下拉框文字会停在旧值上
		node.graph?.setDirtyCanvas(true, true);
	};

	const isRandom = () => modeWidget.value !== MODE_FIXED;

	function viewSeriesKey() {
		if (!isRandom()) return st.localSeries === "all" ? null : st.localSeries;
		if (modeWidget.value === MODE_RANDOM_ALL) return null; // 全库随机忽略筛选
		const name = seriesWidget.value;
		return name === ALL ? null : (st.db.seriesByName.get(name)?.key ?? null);
	}

	function viewCategory() {
		return isRandom() ? catWidget.value : ALL;
	}

	/** 与后端 pose_db.pool() 同一套口径，用来显示候选数。 */
	function scopedPool() {
		const all = st.db.poses;
		if (modeWidget.value === MODE_RANDOM_ALL) return all;
		const skey = viewSeriesKey();
		const cat = viewCategory();
		if (skey) {
			const inSeries = all.filter((p) => p.series === skey);
			if (cat !== ALL) {
				const matched = inSeries.filter((p) => p.cat === cat);
				if (matched.length) return matched;
			}
			if (inSeries.length) return inSeries;
		}
		if (cat !== ALL) {
			const matched = all.filter((p) => p.cat === cat);
			if (matched.length) return matched;
		}
		return all;
	}

	// ---------- 参数按模式显隐 ----------
	// 固定选中：pose + angle
	// 全库随机：只剩 angle（系列与分类都被忽略）
	// 范围内随机：angle + 两个筛选
	const hiddenOrig = new Map();
	function showWidget(widget, on) {
		if (!widget) return;
		if (on) {
			if (!hiddenOrig.has(widget)) return;
			const orig = hiddenOrig.get(widget);
			if (orig) widget.computeSize = orig;
			else delete widget.computeSize;
			widget.hidden = false;
			hiddenOrig.delete(widget);
			return;
		}
		if (hiddenOrig.has(widget)) return;
		hiddenOrig.set(widget, widget.computeSize);
		// 高度归零是 litegraph 里隐藏 widget 的通行做法，节点也会跟着缩
		widget.computeSize = () => [0, -4];
		widget.hidden = true;
	}

	let lastVisKey = "";
	function applyVisibility() {
		const mode = modeWidget.value;
		const showPose = mode === MODE_FIXED;
		const showFilters = mode === MODE_RANDOM_FILTERED;
		// 单角度库（如脸模）没有角度维度：视角控件与角度按钮条不生效不展示
		const single = (st.db?.angles?.length ?? 0) <= 1;

		const key = `${showPose}|${showFilters}|${single}`;
		if (key === lastVisKey) return;
		lastVisKey = key;

		showWidget(poseWidget, showPose);
		showWidget(angleWidget, showPose && !single);
		showWidget(seriesWidget, showFilters);
		showWidget(catWidget, showFilters);

		// 参数行变了，但**不动节点高度**——用户拉过多大就是多大，不能因为切模式被吸回去。
		// 少掉的那几行自然由画廊吃掉（gallery.computeSize 按 node.size[1] 反算）。
		node.graph?.setDirtyCanvas(true, true);
	}

	function syncFromWidgets() {
		if (!st.db) return;
		const pose = st.db.byLabel.get(poseWidget.value);
		if (pose && pose !== st.sel) select(pose, false);
		const angle = st.db.labelToAngle.get(angleWidget.value);
		if (angle && angle !== st.angle) setAngle(angle, false);
		seriesSel.value = viewSeriesKey() ?? "all";
		renderGrid();
		applyVisibility();
	}

	for (const widget of [modeWidget, poseWidget, angleWidget, seriesWidget, catWidget]) {
		const orig = widget.callback;
		widget.callback = function (...args) {
			const r = orig?.apply(this, args);
			syncFromWidgets();
			return r;
		};
	}

	// ---------- 渲染 ----------
	function select(pose, writeWidgets) {
		st.sel = pose;
		if (writeWidgets) setWidget(poseWidget, pose.label);
		renderStage();
		markSelection();
	}

	function setAngle(angle, writeWidgets) {
		st.angle = angle;
		if (writeWidgets) setWidget(angleWidget, st.db.angleLabels[angle]);
		renderAngles();
		for (const [pose, cell] of st.cells) {
			const name = fileFor(pose, angle, "thumb");
			const img = cell.firstElementChild;
			if (name && img.getAttribute("src") !== fileURL(pose, "thumb", name)) {
				img.src = fileURL(pose, "thumb", name);
			}
		}
		renderStage();
	}

	function renderStage() {
		const pose = st.sel;
		const imgBox = stage.querySelector(".gp-stage-img");
		const badge = stage.querySelector(".gp-badge");
		const ctrl = stage.querySelector(".gp-stage-ctrl");
		if (!pose) {
			imgBox.innerHTML = `<span class="gp-empty">载入脸模库…</span>`;
			badge.hidden = true;
			ctrl.hidden = true;
			return;
		}
		const name = fileFor(pose, st.angle, "img");
		if (name) {
			imgBox.innerHTML = `<img src="${fileURL(pose, "img", name)}" draggable="false" alt="">`;
			badge.hidden = false;
			ctrl.hidden = false;
			const prefix = st.stale ? "上次 · " : "";
			// 单角度库没有「视角」可言，徽标里不再追加角度描述
			const anglePart = (st.db.angles?.length ?? 0) > 1 ? ` · ${st.db.angleLabels[st.angle]}` : "";
			badge.textContent = `${prefix}${pose.code} · ${pose.cat}${anglePart}`;
		} else {
			imgBox.innerHTML = `<span class="gp-empty">该角度缺图</span>`;
			badge.hidden = true;
			ctrl.hidden = true;
		}
		stage.dataset.stale = st.stale ? "1" : "0";
	}

	function renderAngles() {
		anglesBar.replaceChildren();
		// 单角度库：角度按钮条没有意义，直接隐藏
		if ((st.db?.angles?.length ?? 0) <= 1) { anglesBar.style.display = "none"; return; }
		anglesBar.style.display = "";
		for (const { key, label } of st.db.angles) {
			const btn = document.createElement("button");
			btn.type = "button";
			btn.className = "gp-abtn";
			btn.textContent = label;
			btn.dataset.on = key === st.angle ? "1" : "0";
			btn.onclick = () => setAngle(key, true);
			anglesBar.append(btn);
		}
	}

	function renderSeries() {
		seriesSel.replaceChildren();
		const all = document.createElement("option");
		all.value = "all";
		all.textContent = `全部 ${st.db.poses.length}`;
		seriesSel.append(all);
		for (const s of st.db.series) {
			const opt = document.createElement("option");
			opt.value = s.key;
			opt.textContent = `${s.short} ${s.count}`;
			seriesSel.append(opt);
		}
	}

	function matchesQuery(pose) {
		const q = st.query;
		if (!q) return true;
		return (
			pose.code.toLowerCase().includes(q) ||
			pose.name.toLowerCase().includes(q) ||
			pose.cat.toLowerCase().includes(q) ||
			pose.label.toLowerCase().includes(q)
		);
	}

	/** 随机模式下画廊直接显示候选池，保证「候选数」和格数一致。 */
	function visiblePoses() {
		if (!isRandom()) {
			const key = viewSeriesKey();
			const list = key ? st.db.poses.filter((p) => p.series === key) : st.db.poses;
			return list.filter(matchesQuery);
		}
		const pool = scopedPool();
		return st.query ? pool.filter(matchesQuery) : pool;
	}

	// 栅格列数：先按可用宽度算出最多能放几列；只在「末行会剩下一个」时才改排列，
	// 例如 7 张、上限 6 列 → 4 + 3，而不是 6 + 1。其余情况保持 CSS 的 auto-fill，
	// 这样筛选数量变化时缩略图尺寸不会跟着跳。
	const MIN_CELL = 58;
	const CELL_GAP = 4;
	const GRID_PAD = 6;
	let gridCols = 0; // 0 = 用 CSS auto-fill

	function layoutGridCols(count) {
		const inner = grid.clientWidth - GRID_PAD * 2;
		if (inner <= 0 || count <= 0) return; // 还没上屏，等 ResizeObserver 再来一次
		const maxCols = Math.max(1, Math.floor((inner + CELL_GAP) / (MIN_CELL + CELL_GAP)));
		let cols = 0;
		if (count > maxCols && count % maxCols === 1) {
			cols = Math.ceil(count / Math.ceil(count / maxCols));
		}
		if (cols === gridCols) return;
		gridCols = cols;
		grid.style.gridTemplateColumns = cols ? `repeat(${cols}, minmax(0, 1fr))` : "";
	}

	// 节点宽度变了要重新算列数，用 rAF 合并连续回调
	let gridRaf = 0;
	if (typeof ResizeObserver !== "undefined") {
		new ResizeObserver(() => {
			cancelAnimationFrame(gridRaf);
			gridRaf = requestAnimationFrame(() => {
				gridCols = -1; // 强制按新宽度重算
				layoutGridCols(st.cells.size);
			});
		}).observe(grid);
	}

	function renderGrid() {
		const list = visiblePoses();
		const lock = modeWidget.value === MODE_RANDOM_ALL;
		seriesSel.disabled = lock;
		seriesSel.title = lock ? "全库随机时忽略系列筛选" : "按系列筛选";
		const frag = document.createDocumentFragment();
		st.cells.clear();		for (const pose of list) {
			const cell = document.createElement("div");
			cell.className = "gp-cell";
			cell.title = `${pose.code} · ${pose.name}`;
			const img = document.createElement("img");
			img.loading = "lazy";
			img.decoding = "async";
			img.draggable = false;
			const name = fileFor(pose, st.angle, "thumb");
			if (name) img.src = fileURL(pose, "thumb", name);
			cell.append(img);
			cell.onclick = () => pickCell(pose);
			// 自定义脸模可以在这里反悔：右键删掉，内置库不提供删除
			if (pose.root === "custom") {
				cell.oncontextmenu = (e) => {
					e.preventDefault();
					e.stopPropagation();
					removePose(pose);
				};
			}
			st.cells.set(pose, cell);
			frag.append(cell);
		}
		grid.replaceChildren(frag);
		layoutGridCols(list.length);
		renderFoot(list.length);
		markSelection();
		layoutStage(); // 预览高度依赖节点剩余空间，每次重绘后重算

		// 随机模式下预览的可能是上一次的结果，不在候选范围里就压暗提示
		const stale = isRandom() && st.sel ? !scopedPool().includes(st.sel) : false;
		if (stale !== st.stale) {
			st.stale = stale;
			renderStage();
		}
	}

	function renderFoot(shown) {
		if (!isRandom()) {
			countEl.textContent = st.notice || `${shown} 张脸模 · 点击选择`;
			hintEl.textContent = MODE_FIXED;
			return;
		}
		countEl.textContent = st.notice || `候选 ${scopedPool().length} 个`;
		hintEl.textContent =
			modeWidget.value === MODE_RANDOM_ALL
				? "全库随机 · 每次抽一个"
				: `范围内随机 · ${seriesWidget.value} / ${catWidget.value}`;
	}

	function markSelection() {
		for (const [pose, cell] of st.cells) {
			cell.dataset.on = pose === st.sel ? "1" : "0";
		}
	}

	/** 随机模式下点缩略图 = 就要这一张，切回固定选中。 */
	function pickCell(pose) {
		if (isRandom()) setWidget(modeWidget, MODE_FIXED);
		select(pose, true);
	}

	// ---------- 导入 / 删除自定义脸模 ----------
	// 数据落在 poses/custom/，服务端扫目录时自动补进索引，不需要重建内置库。
	const IMAGE_NAME = /\.(png|jpe?g|webp|bmp)$/i;
	const CUSTOM_CAT = "自定义";
	let noticeTimer = null;

	function setNotice(text, ms = 5000) {
		st.notice = text || "";
		renderFoot(st.cells.size);
		clearTimeout(noticeTimer);
		if (text) noticeTimer = setTimeout(() => setNotice(""), ms);
	}

	function setBusy(on) {
		root.dataset.busy = on ? "1" : "0";
	}

	/** 是不是图：优先看 MIME，没有 MIME（剪贴板 / 拖拽偶尔如此）就看扩展名。 */
	function isImageFile(file) {
		if (!file) return false;
		return (file.type || "").startsWith("image/") || IMAGE_NAME.test(file.name || "");
	}

	const stemOf = (name) => String(name || "").replace(/\.[^.\\/]+$/, "").trim();

	// ---------- 导入对话框 ----------
	// 点「导入」不直接上传：先确认名称 / 分类 / 视角，多张图还能统一命名。
	let pending = [];
	let previewURL = "";

	function releasePreview() {
		if (previewURL) URL.revokeObjectURL(previewURL);
		previewURL = "";
		dlgPreview.replaceChildren();
	}

	function showPreview(file) {
		releasePreview();
		if (!file) {
			dlgPreview.textContent = "没有预览";
			return;
		}
		previewURL = URL.createObjectURL(file);
		const img = document.createElement("img");
		img.src = previewURL;
		img.alt = "";
		img.draggable = false;
		dlgPreview.append(img);
	}

	/** 分类候选：现有分类（去掉「全部」）。也可以直接输入新分类，不做限制。 */
	function fillCatOptions() {
		dlgCatList.replaceChildren();
		for (const cat of catWidget.options?.values ?? []) {
			if (cat === ALL) continue;
			const opt = document.createElement("option");
			opt.value = cat;
			dlgCatList.append(opt);
		}
	}

	function fillAngleOptions() {
		dlgAngle.replaceChildren();
		for (const { key, label } of st.db?.angles ?? []) {
			const opt = document.createElement("option");
			opt.value = key;
			opt.textContent = label;
			dlgAngle.append(opt);
		}
		dlgAngle.value = st.db?.angleLabels?.[st.angle] ? st.angle : "front";
		// 单角度库没有「视角」可言，导入对话框里直接隐藏视角一行
		const dlgAngleRow = dlgAngle.closest(".gp-dlg-row");
		if (dlgAngleRow) dlgAngleRow.hidden = (st.db?.angles?.length ?? 0) <= 1;
	}

	/** 同名的自定义脸模：用来提示这次是合并视角还是另起一个。 */
	function customByName(name) {
		if (!name) return null;
		return st.db?.poses.find((pose) => pose.root === "custom" && pose.name === name) ?? null;
	}

	function updateHint() {
		const total = pending.length;
		if (!total) {
			dlgHint.textContent = "";
			dlgOk.disabled = true;
			return;
		}
		dlgOk.disabled = false;
		const name = dlgName.value.trim();
		const multiAngle = (st.db?.angles?.length ?? 0) > 1;
		const angleLabel = multiAngle ? (st.db?.angleLabels?.[dlgAngle.value || "front"] ?? "正面") : "";
		if (!name) {
			dlgHint.textContent =
				total > 1 ? `${total} 张各用自己的文件名当脸模名` : "留空就用文件名当脸模名";
			return;
		}
		if (total > 1) {
			dlgHint.textContent = multiAngle
				? `${total} 张会依次命名「${name} 1」「${name} 2」…，视角都是${angleLabel}`
				: `${total} 张会依次命名「${name} 1」「${name} 2」…`;
			return;
		}
		const same = customByName(name);
		if (!same) {
			dlgHint.textContent = multiAngle ? `会新建脸模「${name}」· ${angleLabel}` : `会新建脸模「${name}」`;
			return;
		}
		if (same.angles[dlgAngle.value || "front"]) {
			dlgHint.textContent = multiAngle
				? `「${name}」已经有${angleLabel}了，这张会另存为「${name} (2)」`
				: `「${name}」已存在，这张会另存为「${name} (2)」`;
			return;
		}
		const count = Object.keys(same.angles || {}).length;
		dlgHint.textContent = `会作为「${name}」${multiAngle ? `的${angleLabel}视角` : ""}加入（原有 ${count} 个视角）`;
	}

	function openImport(files) {
		const list = Array.from(files || []).filter(isImageFile);
		if (!list.length) {
			setNotice("没识别到图片，支持 png / jpg / webp / bmp");
			return;
		}
		// 对话框已经开着（点了「选择文件…」换一批）：保留用户填过的名称与分类
		const reopen = !dlg.hidden;
		pending = list;
		fillCatOptions();
		if (!reopen) {
			fillAngleOptions();
			// 单张默认用文件名，多张留空（各用各的）
			dlgName.value = list.length === 1 ? stemOf(list[0].name) : "";
			dlgCat.value = st.lastCat || CUSTOM_CAT;
		}
		dlgCount.textContent = list.length > 1 ? `已选 ${list.length} 张` : list[0].name || "已选 1 张";
		showPreview(list[0]);
		dlg.hidden = false;
		updateHint();
		dlgName.focus();
		dlgName.select();
	}

	function closeImport() {
		dlg.hidden = true;
		pending = [];
		releasePreview();
		fileInput.value = "";
	}

	function confirmImport() {
		const list = pending.slice();
		if (!list.length) {
			closeImport();
			return;
		}
		const meta = {
			name: dlgName.value.trim(),
			cat: dlgCat.value.trim(),
			angle: dlgAngle.value || "front",
		};
		st.lastCat = meta.cat;
		closeImport();
		return uploadFiles(list, meta);
	}

	async function uploadFiles(files, meta = {}) {
		const list = Array.from(files || []).filter(isImageFile);
		if (!list.length) {
			setNotice("没识别到图片，支持 png / jpg / webp / bmp");
			return;
		}
		setBusy(true);
		setNotice(`导入中 ${list.length} 张…`, 60000);
		const form = new FormData();
		form.append("meta", JSON.stringify(meta));
		for (const file of list) form.append("images", file, file.name);
		try {
			const res = await api.fetchApi("/gulifaces/custom/upload", { method: "POST", body: form });
			const out = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(out?.error || `HTTP ${res.status}`);
			const saved = out.saved || [];
			const failed = out.failed || [];
			if (!saved.length) throw new Error(failed[0]?.error || "服务端没有存下任何图片");

			// 刚导入的图直接刷新进画廊（脸模库无搜索框）
			// 用服务端给的 no 跳转：显示名是用户填的，还可能在重名时被加了序号
			const pickNo = (out.nos || [])[0] || null;
			const db = await refresh(pickNo);
			// 新图只有导入时选的那个视角。画廊停在别的视角就会显示「该角度缺图」，
			// 所以这里跟着切到刚导入的视角，才叫「自动适配到位」。
			const picked = pickNo ? db?.byNo?.get(pickNo) : null;
			if (picked && !picked.angles[st.angle]) {
				const want = picked.angles[meta.angle] ? meta.angle : Object.keys(picked.angles)[0];
				if (want) setAngle(want, true);
			}
			setNotice(
				failed.length
					? `导入 ${saved.length} 张，${failed.length} 张失败（${failed[0].error}）`
					: `已导入 ${saved.length} 张到「我的脸模」`,
			);
		} catch (err) {
			setNotice(`导入失败：${err.message}`);
			console.error("[GG 脸模库] 导入失败：", err);
		} finally {
			setBusy(false);
			fileInput.value = "";
		}
	}

	/** 剪贴板里的图没有文件名，按「剪贴板 月日-时分」起一个，够辨认就行。 */
	function clipboardFile(blob, type) {
		const now = new Date();
		const pad = (n) => String(n).padStart(2, "0");
		const ext = (type.split("/")[1] || "png").replace("jpeg", "jpg");
		const stamp = `${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`;
		return new File([blob], `剪贴板 ${stamp}.${ext}`, { type });
	}

	async function pasteFromClipboard() {
		if (!navigator.clipboard?.read) {
			setNotice("这个浏览器不支持读剪贴板，直接按 Ctrl+V 粘贴");
			return;
		}
		try {
			const items = await navigator.clipboard.read();
			const files = [];
			for (const item of items) {
				const type = item.types.find((t) => t.startsWith("image/"));
				if (!type) continue;
				files.push(clipboardFile(await item.getType(type), type));
			}
			if (!files.length) {
				setNotice("剪贴板里没有图片");
				return;
			}
			openImport(files);
		} catch (err) {
			// 权限被拒 / 用户点了取消都走这里：改用 Ctrl+V
			setNotice("读不到剪贴板，直接按 Ctrl+V 粘贴");
			console.warn("[GG 脸模库] 剪贴板读取失败：", err);
		}
	}

	async function removePose(pose) {
		// 一张脸模可能有多个视角，每个视角一张文件，一起删掉
		const names = Object.values(pose.angles || {})
			.map((entry) => entry?.img)
			.filter(Boolean);
		if (!names.length) return;
		const extra = names.length > 1 ? `（连带 ${names.length} 张视角图）` : "";
		const ask = `从脸模库删除「${pose.name}」？${extra}\n原图会从 poses/custom 里移除，删掉就找不回来了。`;
		if (!window.confirm(ask)) return;
		setBusy(true);
		try {
			const res = await api.fetchApi("/gulifaces/custom/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ names }),
			});
			const out = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(out?.error || `HTTP ${res.status}`);
			await refresh(null);
			setNotice(`已删除 ${pose.name}`);
		} catch (err) {
			setNotice(`删除失败：${err.message}`);
			console.error("[GG 脸模库] 删除失败：", err);
		} finally {
			setBusy(false);
		}
	}

	// 「导入」和「随机」曾经共用同一个类名（gp-rnd），处理器又用 querySelector(".gp-rnd") 取，
	// 而「导入」在 DOM 里排在前面 → 它的 onclick 被随机逻辑覆盖，点导入变成随机抽一张。
	// 现在两个按钮各有独立类名，一律用上面取好的引用；gp-btn 只是共用样式，别拿它当选择器。
	importBtn.onclick = () => fileInput.click();
	shuffleBtn.onclick = () => {
		const list = visiblePoses();
		if (!list.length) return;
		pickCell(list[Math.floor(Math.random() * list.length)]);
	};

	fileInput.onchange = () => {
		const files = Array.from(fileInput.files || []);
		fileInput.value = ""; // 清掉，允许重复选同一个文件
		openImport(files);
	};

	dlg.querySelector(".gp-dlg-x").onclick = closeImport;
	dlg.querySelector(".gp-dlg-cancel").onclick = closeImport;
	dlg.querySelector(".gp-dlg-file").onclick = () => fileInput.click();
	dlg.querySelector(".gp-dlg-clip").onclick = () => pasteFromClipboard();
	dlgOk.onclick = () => confirmImport();
	dlgName.oninput = updateHint;
	dlgCat.oninput = updateHint;
	dlgAngle.onchange = updateHint;
	// 回车导入、Esc 关闭；中文输入法选字时的回车不算
	dlgBody.addEventListener("keydown", (e) => {
		if (e.key === "Enter" && !e.isComposing) {
			e.preventDefault();
			e.stopPropagation();
			confirmImport();
		} else if (e.key === "Escape") {
			e.preventDefault();
			e.stopPropagation();
			closeImport();
		}
	});
	// 点遮罩空白处关闭
	dlg.addEventListener("click", (e) => {
		if (e.target === dlg) closeImport();
	});

	// 复制图片后在画布上按 Ctrl+V 也能导入。焦点在输入框里时不动，让浏览器照常粘文字。
	function onPaste(e) {
		const target = e.target;
		if (target instanceof HTMLElement && target.closest("input,textarea")) return;
		const near =
			!dlg.hidden || node.is_selected || root.matches(":hover") || root.contains(document.activeElement);
		if (!near) return;
		const files = Array.from(e.clipboardData?.files || []).filter(isImageFile);
		if (!files.length) return;
		e.preventDefault();
		e.stopPropagation();
		openImport(files);
	}
	document.addEventListener("paste", onPaste);
	// 节点删掉后要摘掉全局监听，否则面板已经没了还在接粘贴
	const prevRemoved = node.onRemoved;
	node.onRemoved = function () {
		document.removeEventListener("paste", onPaste);
		return prevRemoved?.apply(this, arguments);
	};

	// 拖图片进面板 = 导入；拦在面板这一层，否则画布会把图当成节点素材吞掉
	const hasFiles = (e) => Array.from(e.dataTransfer?.types || []).includes("Files");
	let dragDepth = 0;
	root.addEventListener("dragenter", (e) => {
		if (!hasFiles(e)) return;
		e.preventDefault();
		dragDepth += 1;
		root.dataset.drop = "1";
	});
	root.addEventListener("dragover", (e) => {
		if (hasFiles(e)) e.preventDefault();
	});
	root.addEventListener("dragleave", () => {
		dragDepth = Math.max(0, dragDepth - 1);
		if (!dragDepth) root.dataset.drop = "0";
	});
	root.addEventListener("drop", (e) => {
		if (!e.dataTransfer?.files?.length) return;
		e.preventDefault();
		e.stopPropagation();
		dragDepth = 0;
		root.dataset.drop = "0";
		openImport(e.dataTransfer.files);
	});

	seriesSel.onchange = () => {
		const key = seriesSel.value;
		if (isRandom()) {
			const name = key === "all" ? ALL : (st.db.series.find((s) => s.key === key)?.name ?? ALL);
			setWidget(seriesWidget, name);
			renderGrid();
		} else {
			st.localSeries = key;
			renderGrid();
		}
	};

	// 脸模库条目只有编号、无中文名，按用户要求移除搜索框。

	// 推荐链接：拦住冒泡，否则按下时会顺手把节点拖走
	const promoLink = root.querySelector(".gp-promo-link");
	for (const ev of ["pointerdown", "mousedown", "click"]) {
		promoLink.addEventListener(ev, (e) => e.stopPropagation());
	}

	// 执行后把真正抽到的脸模同步到画廊，并写回 pose 下拉，切回固定选中时还能保留
	node.__gulifacesApply = (picked) => {
		if (!st.db || !picked) return;
		const pose = st.db.byNo.get(picked.no);
		if (!pose) return;
		select(pose, true);
		if (st.db.angleLabels[picked.angle]) {
			st.angle = picked.angle;
			renderAngles();
			renderStage();
		}
	};

	// ---------- 载入 / 刷新 ----------
	/** 下拉选项就地换掉：导入完不刷新页面也能选到新图。 */
	function setOptions(widget, values) {
		if (!widget || !values?.length) return;
		widget.options = widget.options || {};
		widget.options.values = values;
		if (!values.includes(widget.value)) widget.value = values[0];
	}

	function applyDB(db) {
		db.byLabel = new Map(db.poses.map((p) => [p.label, p]));
		db.byNo = new Map(db.poses.map((p) => [p.no, p]));
		db.labelToAngle = new Map(db.angles.map((a) => [a.label, a.key]));
		db.angleLabels = Object.fromEntries(db.angles.map((a) => [a.key, a.label]));
		db.seriesByName = new Map(db.series.map((s) => [s.name, s]));
		st.db = db;

		setOptions(poseWidget, db.poses.map((p) => p.label));
		setOptions(seriesWidget, [ALL, ...db.series.map((s) => s.name)]);
		// 分类按数量降序，与后端 pose_db.category_options() 同一口径
		const counts = new Map();
		for (const pose of db.poses) counts.set(pose.cat, (counts.get(pose.cat) || 0) + 1);
		const cats = [...counts.keys()].sort(
			(a, b) => counts.get(b) - counts.get(a) || a.localeCompare(b, "zh"),
		);
		setOptions(catWidget, [ALL, ...cats]);

		renderSeries();
		st.angle = db.labelToAngle.get(angleWidget.value) ?? "front";
		renderAngles();
	}

	/** 重新拉索引并重建画廊；pickNo 是导入后想立刻选中的那张。 */
	function refresh(pickNo) {
		dbPromise = null; // 丢掉缓存，向服务端要最新的
		return loadDB().then((db) => {
			applyDB(db);
			const keep = db.byLabel.get(poseWidget.value);
			const fresh = pickNo ? db.byNo.get(pickNo) : null;
			let target = keep || db.poses[0];
			let write = !keep;
			// 随机模式下不动用户的选择，新图只是进了候选池
			if (fresh && !isRandom()) {
				target = fresh;
				write = true;
			}
			if (target) select(target, write);
			seriesSel.value = viewSeriesKey() ?? "all";
			renderGrid();
			applyVisibility();
			return db;
		});
	}

	loadDB()
		.then((db) => {
			applyDB(db);
			const pose = db.byLabel.get(poseWidget.value);
			if (pose) select(pose, false);
			else if (db.poses.length) select(db.poses[0], true);
			seriesSel.value = viewSeriesKey() ?? "all";
			renderGrid();
			// 从工作流恢复时 mode 可能不是固定选中，按它收一遍参数
			applyVisibility();
		})
		.catch((err) => {
			root.innerHTML = `<div class="gp-msg">脸模库载入失败：${err.message}<br>请确认 ComfyUI 控制台里的报错。</div>`;
			console.error("[GG 脸模库]", err);
		});

	// 先按默认模式收一遍，避免刚拖出来时一排灰条
	applyVisibility();
	// 初始尺寸 = 默认画廊高度 + 当前可见的参数行。之后就交给用户：
	// 拉伸过的尺寸会被 ComfyUI 存进工作流，代码不再自动改高度。
	node.setSize([440, GALLERY_HEIGHT + chromeHeight()]);
}

// 本节点只有一个输出（脸模图）。旧工作流里存着 image / pose_name / pose_info 三个槽，
// litegraph 恢复时会照抄存档的 outputs 数组，于是画布上会多挂两个死输出——这里直接摘掉。
const OUTPUT_COUNT = 1;
function trimOutputs(node) {
	if ((node.outputs?.length ?? 0) <= OUTPUT_COUNT) return;
	while (node.outputs.length > OUTPUT_COUNT) {
		node.removeOutput(node.outputs.length - 1);
	}
	// 只补高、不压低：存档里的尺寸是用户拉出来的，不能因为摘了两个槽就被吸回去
	const need = node.computeSize()[1];
	if (node.size[1] < need) node.setSize([node.size[0], need]);
	node.graph?.setDirtyCanvas(true, true);
}

app.registerExtension({
	name: "ComfyUI.GGPoses.FaceGallery",
	beforeRegisterNodeDef(nodeType, nodeData) {
		if (nodeData.name !== NODE_NAME) return;
		// 同一原型只包一次；标记名和实例上的区别开，避免顺着原型链误判（见 AGENTS.md）
		if (nodeType.prototype.__gpFacePatched) return;
		nodeType.prototype.__gpFacePatched = true;

		const onNodeCreated = nodeType.prototype.onNodeCreated;
		nodeType.prototype.onNodeCreated = function () {
			const r = onNodeCreated?.apply(this, arguments);
			// 画廊装不上也不能影响节点本身可用：只告警，保留控件与输出
			try {
				setup(this);
			} catch (err) {
				console.error("[GG 脸模库] 画廊初始化失败，节点参数仍可用：", err);
			}
			return r;
		};

		// 打开旧工作流时，输出槽是存档带出来的，得在 configure 之后再收一遍
		const onConfigure = nodeType.prototype.onConfigure;
		nodeType.prototype.onConfigure = function () {
			const r = onConfigure?.apply(this, arguments);
			try {
				trimOutputs(this);
			} catch (err) {
				console.warn("[GG 脸模库] 清理多余输出槽失败：", err);
			}
			return r;
		};

		const onExecuted = nodeType.prototype.onExecuted;
		nodeType.prototype.onExecuted = function (message) {
			onExecuted?.apply(this, arguments);
			const picked = message?.picked?.[0];
			if (picked) this.__gulifacesApply?.(picked);
		};
	},
});
