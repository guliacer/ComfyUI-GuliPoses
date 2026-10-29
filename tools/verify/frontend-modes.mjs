// 前端三模式交互验证：筛选交集、仅分类、全库随机锁死下拉、序列化重开恢复。
//
// 前置：起一个隔离实例（不要动用户正在跑的 8188）
//   python -s ComfyUI/main.py --port 8189 --cpu --disable-all-custom-nodes \
//     --whitelist-custom-nodes ComfyUI-GuliPoses --disable-auto-launch
//
// 运行：
//   COMFY_PORT=8189 node tools/verify/frontend-modes.mjs
//
// 期望：intersection 6 格 / categoryOnly 29 格 / randomAll.locked true / restored 20 格。

import pw from "file:///C:/Users/Admin/.workbuddy-ai/binaries/node/workspace/node_modules/playwright-core/index.js";
const { chromium } = pw;

const PORT = process.env.COMFY_PORT ?? "8189";
const SHOT = process.env.SHOT ?? "";
const EXE = "C:/Users/Admin/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe";

const browser = await chromium.launch({ executablePath: EXE, headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 1100 }, deviceScaleFactor: 2 });
const errs = [];
page.on("pageerror", (e) => errs.push(`PAGEERROR: ${e.message}`));

await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "networkidle" });
await page.waitForFunction(() => !!window.app?.graph);
await page.evaluate(() => {
	const n = window.LiteGraph.createNode("GuliPosePicker");
	window.app.graph.add(n);
	n.pos = [120, 40];
});
await page.waitForTimeout(2600);

const setW = (name, value) =>
	page.evaluate(
		([name, value]) => {
			const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
			const w = n.widgets.find((x) => x.name === name);
			w.value = value;
			w.callback?.(value);
		},
		[name, value],
	);

const snap = () =>
	page.evaluate(() => {
		const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
		const host = document.querySelector('[data-testid="dom-widgets"]');
		const val = (name) => n.widgets.find((w) => w.name === name)?.value;
		return {
			mode: val("模式"),
			series: val("筛选系列"),
			cat: val("筛选分类"),
			cells: host.querySelectorAll(".gp-cell").length,
			foot: host.querySelector(".gp-count").textContent,
			hint: host.querySelector(".gp-hint").textContent,
			seriesSel: host.querySelector(".gp-series").value,
			locked: host.querySelector(".gp-series").disabled,
		};
	});

const out = {};
// 有效交集：双人互动 + 贴脸系
await setW("模式", "范围内随机");
await setW("筛选系列", "双人互动");
await setW("筛选分类", "贴脸系");
await page.waitForTimeout(400);
out.intersection = await snap();

// 只有分类：全部系列 + 站姿
await setW("筛选系列", "全部");
await setW("筛选分类", "站姿");
await page.waitForTimeout(400);
out.categoryOnly = await snap();

// 全库随机时筛选锁死
await setW("模式", "全库随机");
await page.waitForTimeout(300);
out.randomAll = await snap();

// 序列化 → 重开
await setW("模式", "范围内随机");
await setW("筛选系列", "全身单人-性感系");
await setW("筛选分类", "趴卧");
await page.waitForTimeout(300);
const wf = await page.evaluate(() => window.app.graph.serialize());
const restored = await page.evaluate(async (g) => {
	await window.app.loadGraphData(g);
	await new Promise((r) => setTimeout(r, 2500));
	const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
	const host = document.querySelector('[data-testid="dom-widgets"]');
	const val = (name) => n.widgets.find((w) => w.name === name)?.value;
	return {
		mode: val("模式"),
		series: val("筛选系列"),
		cat: val("筛选分类"),
		cells: host.querySelectorAll(".gp-cell").length,
		foot: host.querySelector(".gp-count").textContent,
		hint: host.querySelector(".gp-hint").textContent,
		seriesSel: host.querySelector(".gp-series").value,
	};
}, wf);

if (SHOT) {
	await page.screenshot({
		path: SHOT,
		clip: await page.evaluate(() => {
			const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
			const ds = window.app.canvas.ds;
			return { x: (n.pos[0] + ds.offset[0]) * ds.scale - 4, y: (n.pos[1] + ds.offset[1]) * ds.scale - 4, width: n.size[0] * ds.scale + 8, height: n.size[1] * ds.scale + 8 };
		}),
	});
}

console.log(JSON.stringify({ out, restored, errs: errs.slice(0, 3) }, null, 2));
await browser.close();
