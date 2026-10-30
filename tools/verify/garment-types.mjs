// 服装库分类与旧名迁移验证：6 个类型 tab / 20 个二级分类 / 三代旧名都能就地换成新名。
//
// 前置：起一个隔离实例（不要动用户正在跑的 8188）
//   python -s ComfyUI/main.py --port 8189 --cpu --disable-all-custom-nodes \
//     --whitelist-custom-nodes ComfyUI-GuliPoses --disable-auto-launch
//
// 运行：
//   COMFY_PORT=8189 node tools/verify/garment-types.mjs
//
// 期望：
//   seriesSel  = ["全部","连衣裙","半身裙","裤装","上装","内衣·家居","泳装"]
//   catCount   = 21（20 个二级分类 + 「全部」），且不含「其它」
//   三个旧名都能迁移到当前名字：
//     「春 SPR-0001」    → 半身裙·迷你 SPR-0001   （走 labelOld）
//     「派对 PTY-0003」  → 连衣裙·长款 PTY-0003   （走 labelOld）
//     「其它 SUM-0192」  → 裤装·长裤 SUM-0192     （中间版名字，走编号兜底）

import pw from "file:///C:/Users/Admin/.workbuddy-ai/binaries/node/workspace/node_modules/playwright-core/index.js";
const { chromium } = pw;

const PORT = process.env.COMFY_PORT ?? "8189";
const EXE = "C:/Users/Admin/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe";

const browser = await chromium.launch({ executablePath: EXE, headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 1100 }, deviceScaleFactor: 2 });
const errs = [];
page.on("pageerror", (e) => errs.push(`PAGEERROR: ${e.message}`));

await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "networkidle" });
await page.waitForFunction(() => !!window.app?.graph);

// 建节点并等库加载完（1405 条要走一次 /guligarments/index.json）
await page.evaluate(() => {
	const n = window.LiteGraph.createNode("GuliGarmentPicker");
	window.app.graph.add(n);
	n.pos = [120, 40];
});
await page.waitForTimeout(3000);

// 第一层：系列下拉、分类下拉、卡片数
const shape = await page.evaluate(() => {
	const n = window.app.graph._nodes.find((x) => x.type === "GuliGarmentPicker");
	const host = document.querySelector('[data-testid="dom-widgets"]');
	const seriesSel = host.querySelector(".gp-series");
	const catWidget = n.widgets.find((w) => w.name === "筛选分类");
	const catValues = catWidget?.options?.values ?? [];
	return {
		seriesOptions: [...seriesSel.options].map((o) => o.value),
		seriesCount: seriesSel.options.length,
		catCount: catValues.length,
		catValues,
		hasOther: catValues.includes("其它") || [...seriesSel.options].some((o) => o.value === "其它"),
		cells: host.querySelectorAll(".gp-cell").length,
		foot: host.querySelector(".gp-count")?.textContent,
		valueNow: n.widgets.find((w) => w.name === "服装")?.value,
	};
});

// 第二层：旧工作流载入后的名字迁移
const wnames = await page.evaluate(() => {
	const n = window.app.graph._nodes.find((x) => x.type === "GuliGarmentPicker");
	return n.widgets.map((w) => w.name);
});

/** widgets_values 可能是数组（旧格式，按 widgets 顺序）或对象（新格式），两种都写对。 */
const setWidget = (node, name, value) => {
	if (Array.isArray(node.widgets_values)) {
		const i = wnames.indexOf(name);
		if (i >= 0) node.widgets_values[i] = value;
	} else if (node.widgets_values) {
		node.widgets_values[name] = value;
	}
};

const base = await page.evaluate(() => window.app.graph.serialize());
const baseNode = base.nodes.find((n) => n.type === "GuliGarmentPicker");

const cases = [
	["春 SPR-0001", "半身裙·迷你 SPR-0001"], // 第一代：季节名，走 labelOld
	["派对 PTY-0003", "连衣裙·长款 PTY-0003"], // 第一代：派对礼服，走 labelOld
	["其它 SUM-0192", "裤装·长裤 SUM-0192"], // 上一版中间名，走编号兜底
];

const migrated = [];
for (const [oldLabel, expect] of cases) {
	const graph = JSON.parse(JSON.stringify(base));
	const node = graph.nodes.find((n) => n.type === "GuliGarmentPicker");
	setWidget(node, "服装", oldLabel);
	const got = await page.evaluate(async (g) => {
		await window.app.loadGraphData(g);
		await new Promise((r) => setTimeout(r, 2200));
		const n = window.app.graph._nodes.find((x) => x.type === "GuliGarmentPicker");
		const host = document.querySelector('[data-testid="dom-widgets"]');
		const img = host.querySelector(".gp-stage img");
		const foot = host.querySelector(".gp-count")?.textContent ?? "";
		const serialized = window.app.graph.serialize();
		const sn = serialized.nodes.find((x) => x.type === "GuliGarmentPicker");
		const inArray = Array.isArray(sn.widgets_values);
		const idx = n.widgets.map((w) => w.name).indexOf("服装");
		return {
			label: n.widgets.find((w) => w.name === "服装")?.value,
			saved: inArray ? sn.widgets_values[idx] : sn.widgets_values?.["服装"],
			badge: host.querySelector(".gp-badge")?.textContent ?? "",
			src: img?.getAttribute("src") ?? "",
			cells: host.querySelectorAll(".gp-cell").length,
			picked: /选\s*\S+\s*\/\s*\d+/.exec(foot)?.[0] ?? foot.trim().slice(0, 24),
			stale: host.querySelector(".gp-stage")?.dataset?.stale,
		};
	}, graph);
	migrated.push({ from: oldLabel, expect, ok: got.label === expect && got.saved === expect, ...got });
}

const ok =
	shape.seriesCount === 7 &&
	!shape.hasOther &&
	shape.catCount === 21 &&
	migrated.every((m) => m.ok);

console.log(JSON.stringify({ ok, shape, migrated, errs: errs.slice(0, 3) }, null, 2));
await browser.close();
process.exit(ok ? 0 : 1);
