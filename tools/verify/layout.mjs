// 布局体检：确认加了推荐行之后，画廊没有溢出、栅格还有可用高度、链接可点。
//
// 运行：COMFY_PORT=8189 node tools/verify/layout.mjs
// 期望：overflow 为 0（scrollHeight 不超过 clientHeight）、grid 高度 > 200、promo 可见且 href 正确。

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

const measure = () =>
	page.evaluate(() => {
		const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
		const host = document.querySelector('[data-testid="dom-widgets"]');
		const root = host.querySelector(".gp-root");
		const grid = host.querySelector(".gp-grid");
		const promo = host.querySelector(".gp-promo");
		const link = host.querySelector(".gp-promo-link");
		const r = root.getBoundingClientRect();
		const p = promo?.getBoundingClientRect();
		return {
			node: n.size.map((v) => Math.round(v)),
			rootClient: root.clientHeight,
			rootScroll: root.scrollHeight,
			overflow: root.scrollHeight - root.clientHeight,
			gridH: Math.round(grid.clientHeight),
			gridScroll: grid.scrollHeight,
			stageH: Math.round(host.querySelector(".gp-stage").clientHeight),
			footH: Math.round(host.querySelector(".gp-foot").clientHeight),
			promoH: p ? Math.round(p.height) : null,
			promoInRoot: p ? p.bottom <= r.bottom + 0.5 : false,
			promoText: promo?.textContent?.replace(/\s+/g, " ").trim(),
			promoHref: link?.getAttribute("href"),
			promoColor: link ? getComputedStyle(link).color : null,
			cells: host.querySelectorAll(".gp-cell").length,
			rowsVisible: Math.floor(grid.clientHeight / (host.querySelector(".gp-cell")?.getBoundingClientRect().height || 1)),
		};
	});

const out = { default: await measure() };

// 窄一点，确认推荐行不会把布局挤坏
await page.evaluate(() => {
	const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
	n.setSize([360, n.computeSize()[1]]);
	window.app.graph.setDirtyCanvas(true, true);
});
await page.waitForTimeout(600);
out.narrow = await measure();

await page.evaluate(() => {
	const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
	n.setSize([440, n.computeSize()[1]]);
	window.app.graph.setDirtyCanvas(true, true);
});
await page.waitForTimeout(600);

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

console.log(JSON.stringify({ out, errs: errs.slice(0, 3) }, null, 2));
await browser.close();
