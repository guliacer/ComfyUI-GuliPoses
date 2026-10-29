// 参数按模式显隐的验证：每种模式下只应露出真正生效的控件，节点高度随之收缩。
//
// 运行：COMFY_PORT=8189 node tools/verify/mode-visibility.mjs
// 期望：
//   固定选中   → mode / pose / angle
//   全库随机   → mode / angle
//   范围内随机 → mode / angle / filter_series / filter_category
//   切视角（含随机视角）不应改变可见集合

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
		const visible = [];
		const hidden = [];
		for (const w of n.widgets) {
			const h = w.computeSize ? w.computeSize(440)[1] : 20;
			(w.hidden || h <= 0 ? hidden : visible).push(w.name);
		}
		return {
			mode: n.widgets.find((w) => w.name === "模式")?.value,
			angle: n.widgets.find((w) => w.name === "视角")?.value,
			visible,
			hidden,
			height: Math.round(n.size[1]),
			// 隐藏不影响提交，顺序和长度都不能变
			values: n.widgets_values?.length,
		};
	});

const out = {};
out.fixed = await snap();

await setW("模式", "全库随机");
await page.waitForTimeout(500);
out.randomAll = await snap();

await setW("模式", "范围内随机");
await page.waitForTimeout(500);
out.scoped = await snap();

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

await setW("模式", "固定选中");
await page.waitForTimeout(400);
await setW("视角", "随机视角");
await page.waitForTimeout(400);
out.fixedRandomAngle = await snap();

await setW("视角", "正面");
await page.waitForTimeout(400);
out.backToFixed = await snap();

// 序列化后重开：范围内随机应当仍然只露该露的
await setW("模式", "范围内随机");
await setW("筛选系列", "双人互动");
await page.waitForTimeout(300);
const wf = await page.evaluate(() => window.app.graph.serialize());
const restored = await page.evaluate(async (g) => {
	await window.app.loadGraphData(g);
	await new Promise((r) => setTimeout(r, 2500));
	const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
	const visible = [];
	const hidden = [];
	for (const w of n.widgets) {
		const h = w.computeSize ? w.computeSize(440)[1] : 20;
		(w.hidden || h <= 0 ? hidden : visible).push(w.name);
	}
	return { mode: n.widgets.find((w) => w.name === "模式")?.value, visible, hidden, height: Math.round(n.size[1]) };
}, wf);

console.log(JSON.stringify({ out, restored, errs: errs.slice(0, 3) }, null, 2));
await browser.close();
