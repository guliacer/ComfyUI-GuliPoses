// 端到端验证：随机模式连跑两次都必须真的执行（没有 seed 了，靠 IS_CHANGED 强制重跑），
// 每次都要回传 picked 让画廊跳到抽中的姿态；固定模式则应该正常命中缓存。
//
// 前置：起一个隔离实例（不要动用户正在跑的 8188）
//   python -s ComfyUI/main.py --port 8189 --cpu --disable-all-custom-nodes \
//     --whitelist-custom-nodes ComfyUI-GuliPoses --disable-auto-launch
//
// 运行：
//   COMFY_PORT=8189 node tools/verify/queue-roundtrip.mjs
//
// 期望：widgets 只剩 5 个（无 seed / 无 control_after_generate）、outputs 只剩 1 个；
//      随机两次都 executed 且 picked 齐全、徽标两次都更新；固定两次第二次命中缓存。

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

// 建节点 + SaveImage 并连线
await page.evaluate(() => {
	const picker = window.LiteGraph.createNode("GuliPosePicker");
	window.app.graph.add(picker);
	picker.pos = [80, 40];
	const save = window.LiteGraph.createNode("SaveImage");
	window.app.graph.add(save);
	save.pos = [600, 120];
	picker.connect(0, save, 0);
});
await page.waitForTimeout(2500);

// 结构：参数与输出都应该只剩必要的
const shape = await page.evaluate(() => {
	const n = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
	return {
		title: n.title,
		category: n.constructor.category ?? n.category,
		widgets: n.widgets.map((w) => w.name),
		outNames: n.outputs.map((o) => o.name ?? o.label),
		outCount: n.outputs.length,
	};
});

// 监听执行事件：只有真的执行了才会有 executed 消息。
// ComfyUI 把节点返回的 ui 数据合进 detail.output，所以 picked 在 detail.output.picked。
await page.evaluate(() => {
	const a = window.api ?? window.app?.api;
	window.__execs = [];
	a.addEventListener("executed", (e) => {
		const d = e.detail ?? {};
		window.__execs.push({ node: d.node, picked: d.output?.picked ?? null });
	});
});

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

const stage = () =>
	page.evaluate(() => {
		const host = document.querySelector('[data-testid="dom-widgets"]');
		return {
			badge: host.querySelector(".gp-badge")?.textContent,
			stale: host.querySelector(".gp-stage").dataset.stale,
			src: host.querySelector(".gp-stage img")?.getAttribute("src"),
		};
	});

const takeExecs = () =>
	page.evaluate(() => {
		const list = window.__execs.slice();
		window.__execs = [];
		return list;
	});

const runOnce = async () => {
	await page.evaluate(() => window.app.queuePrompt(0, 1));
	await page.waitForTimeout(2600);
	return { execs: await takeExecs(), stage: await stage() };
};

const out = { shape };

// 随机模式：连跑两次，两次都必须执行并回传
await setW("模式", "范围内随机");
await setW("筛选系列", "双人互动");
await setW("筛选分类", "全部");
await page.waitForTimeout(400);
out.before = await stage();

out.random1 = await runOnce();
out.random2 = await runOnce();

// 固定模式：同一张图连跑两次，第二次应命中缓存（无 executed 消息）
await setW("模式", "固定选中");
await page.waitForTimeout(400);
out.fixed1 = await runOnce();
out.fixed2 = await runOnce();

out.counter = await page.evaluate(() => {
	const host = document.querySelector('[data-testid="dom-widgets"]');
	return {
		foot: host.querySelector(".gp-count").textContent,
		on: host.querySelectorAll('.gp-cell[data-on="1"]').length,
		height: Math.round(window.app.graph._nodes.find((x) => x.type === "GuliPosePicker").size[1]),
	};
});

console.log(JSON.stringify({ out, errs: errs.slice(0, 3) }, null, 2));
await browser.close();
