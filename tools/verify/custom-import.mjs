// 端到端验证：自定义姿态（poses/custom/）的整套闭环。
//
// 覆盖：上传接口落盘 + 索引合并 + 缩略图/原图可读 + 路径穿越防护、
//      点「导入」真的弹出选文件框（曾因按钮 onclick 被随机逻辑覆盖而失效）、
//      导入对话框里改名称 / 分类 / 视角、同名不同视角合并成一个姿态、
//      剪贴板粘贴导入、随机按钮没被弄坏、下拉框就地刷新（不刷新页面）、
//      右键删除（多视角一起删）、删完退回内置库。
//
// 前置：起一个隔离实例（不要动用户正在跑的 8188）
//   python -s ComfyUI/main.py --port 8189 --cpu --disable-all-custom-nodes \
//     --whitelist-custom-nodes ComfyUI-GuliPoses --disable-auto-launch
//
// 运行：
//   COMFY_PORT=8189 node tools/verify/custom-import.mjs
//
// 脚本会把测试图传上去又删掉，跑完 poses/custom/ 应恢复原样。

import fs from "node:fs/promises";
import path from "node:path";
import pw from "file:///C:/Users/Admin/.workbuddy-ai/binaries/node/workspace/node_modules/playwright-core/index.js";

const { chromium } = pw;

const PORT = process.env.COMFY_PORT ?? "8189";
const BASE = `http://127.0.0.1:${PORT}`;
const EXE = "C:/Users/Admin/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe";
const DIR = process.env.TEST_IMG_DIR || "C:/Users/Admin/AppData/Local/Temp/guli-test";
const NAMES = ["我的测试姿态 01.png", "我的测试姿态 02.png"];
const FILES = NAMES.map((name) => path.join(DIR, name));
const CUSTOM_LABEL = "我的姿态 · ";
const HOST = '[data-testid="dom-widgets"]';

const out = {};
const fails = [];
const check = (name, ok, detail) => {
	if (!ok) fails.push(detail === undefined ? name : `${name}: ${JSON.stringify(detail)}`);
	out[name] = ok;
};

const getIndex = async () => (await fetch(`${BASE}/guliposes/index.json`)).json();

async function upload(files, meta) {
	const form = new FormData();
	if (meta) form.append("meta", JSON.stringify(meta));
	for (const file of files) {
		const buf = await fs.readFile(file);
		form.append("images", new Blob([buf], { type: "image/png" }), path.basename(file));
	}
	const res = await fetch(`${BASE}/guliposes/custom/upload`, { method: "POST", body: form });
	return { status: res.status, body: await res.json() };
}

const remove = async (names) => {
	const res = await fetch(`${BASE}/guliposes/custom/delete`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ names }),
	});
	return res.status;
};

/** 把所有自定义图删干净，保证起点是纯内置库。 */
async function cleanAll() {
	const db = await getIndex();
	const names = [];
	for (const pose of db.poses.filter((p) => p.root === "custom")) {
		for (const entry of Object.values(pose.angles || {})) if (entry?.img) names.push(entry.img);
	}
	if (names.length) await remove(names);
	return names.length;
}

// 上一次跑崩了留下的残渣先清掉
await cleanAll();
const clean = await getIndex();
check("起点是内置库", clean.poses.length === 288, clean.poses.length);
check("起点没有自定义系列", !clean.series.some((s) => s.name === "我的姿态"), clean.series.map((s) => s.name));

// ---------- 1. 接口层 ----------
const up = await upload([FILES[0]]);
check("上传返回 200", up.status === 200, up.status);
check("上传落盘 1 张", up.body.saved?.length === 1, up.body);
check("回传落盘文件名", up.body.saved?.[0] === "我的测试姿态 01.png", up.body.saved);
check("回传姿态 no（供前端跳转）", up.body.nos?.[0] === "custom/我的测试姿态 01", up.body.nos);

const afterOne = await getIndex();
const custom = afterOne.poses.filter((p) => p.root === "custom");
check("索引并入自定义姿态", custom.length === 1, custom.length);
check("自定义排在最前", afterOne.poses[0].root === "custom", afterOne.poses[0].no);
check("系列多出「我的姿态」", afterOne.series[0]?.name === "我的姿态", afterOne.series[0]);
check("分类是「自定义」", custom[0]?.cat === "自定义", custom[0]?.cat);
check("显示名取文件名", custom[0]?.label === `${CUSTOM_LABEL}我的测试姿态 01`, custom[0]?.label);
check("总数 288+1", afterOne.poses.length === 289, afterOne.poses.length);

const thumbRes = await fetch(`${BASE}/guliposes/custom/thumb/${encodeURIComponent(custom[0].angles.front.thumb)}`);
check("缩略图可读", thumbRes.status === 200 && thumbRes.headers.get("content-type").includes("jpeg"), {
	status: thumbRes.status,
	type: thumbRes.headers.get("content-type"),
});
const imgRes = await fetch(`${BASE}/guliposes/custom/img/${encodeURIComponent(custom[0].angles.front.img)}`);
check("原图可读", imgRes.status === 200, imgRes.status);
const evil = await fetch(`${BASE}/guliposes/custom/img/${encodeURIComponent("../../index.json")}`);
check("挡住路径穿越", evil.status === 404, evil.status);

// ---------- 2. 浏览器：点「导入」得真的弹出选文件框 ----------
const browser = await chromium.launch({ executablePath: EXE, headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 1100 }, deviceScaleFactor: 2 });
const errs = [];
page.on("pageerror", (e) => errs.push(`PAGEERROR: ${e.message}`));
page.on("dialog", (d) => d.accept());

await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.waitForFunction(() => !!window.app?.graph);
await page.evaluate(() => {
	const node = window.LiteGraph.createNode("GuliPosePicker");
	window.app.graph.add(node);
	node.pos = [60, 40];
});
await page.waitForTimeout(2500);

const snapshot = () =>
	page.evaluate(() => {
		const host = document.querySelector('[data-testid="dom-widgets"]');
		const node = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
		const poseWidget = node.widgets.find((w) => w.name === "姿态");
		const seriesWidget = node.widgets.find((w) => w.name === "筛选系列");
		const catWidget = node.widgets.find((w) => w.name === "筛选分类");
		return {
			poseValues: poseWidget.options?.values ?? [],
			poseValue: poseWidget.value,
			angleValue: node.widgets.find((w) => w.name === "视角")?.value,
			seriesValues: seriesWidget.options?.values ?? [],
			catValues: catWidget.options?.values ?? [],
			cells: host.querySelectorAll(".gp-cell").length,
			customCells: [...host.querySelectorAll(".gp-cell")].filter((c) => /^C\d{3}/.test(c.title)).length,
			foot: host.querySelector(".gp-count")?.textContent,
			stageSrc: host.querySelector(".gp-stage img")?.getAttribute("src"),
			badge: host.querySelector(".gp-badge")?.textContent,
			height: Math.round(node.size[1]),
		};
	});

const dlgState = () =>
	page.evaluate(() => {
		const host = document.querySelector('[data-testid="dom-widgets"]');
		const dlg = host.querySelector(".gp-dlg");
		const box = host.querySelector(".gp-dlg-box");
		return {
			open: !dlg.hidden,
			name: host.querySelector(".gp-dlg-name")?.value,
			cat: host.querySelector(".gp-dlg-cat")?.value,
			angle: host.querySelector(".gp-dlg-angle")?.value,
			angleOptions: [...host.querySelectorAll(".gp-dlg-angle option")].map((o) => o.value),
			count: host.querySelector(".gp-dlg-count")?.textContent,
			hint: host.querySelector(".gp-dlg-hint")?.textContent,
			hasPreview: !!host.querySelector(".gp-dlg-preview img"),
			overflow: box ? box.scrollHeight - box.clientHeight : -1,
		};
	});

/**
 * 点面板上的「导入」，确认它真的把点击传给了 <input type=file>，再喂文件、等对话框。
 *
 * 断言用「input 收到 click」而不是 Playwright 的 filechooser 事件：无头 Chromium 里
 * filechooser 偶发不触发（同一份代码连跑会挂一遍），而 input.click() 有没有被调用是确定的。
 * 按钮 onclick 被随机逻辑覆盖时，正是这个 click 不会发生——这才是要守的那条线。
 */
async function importViaDialog(file, fill) {
	await page.evaluate(() => {
		window.__impClicks = 0;
		const input = document.querySelector('[data-testid="dom-widgets"] input[type="file"]');
		if (input && !input.__counted) {
			input.__counted = true;
			input.addEventListener("click", () => (window.__impClicks += 1), true);
		}
	});
	await page.click(`${HOST} .gp-imp`);
	await page.waitForTimeout(200);
	const clicks = await page.evaluate(() => window.__impClicks);
	check("点「导入」把点击传给了选文件框", clicks >= 1, clicks);

	await page.setInputFiles(`${HOST} input[type="file"]`, [file]);
	await page.waitForTimeout(350);
	const opened = await dlgState();
	if (fill) {
		if (fill.name !== undefined) await page.fill(`${HOST} .gp-dlg-name`, fill.name);
		if (fill.cat !== undefined) await page.fill(`${HOST} .gp-dlg-cat`, fill.cat);
		if (fill.angle !== undefined) await page.selectOption(`${HOST} .gp-dlg-angle`, fill.angle);
		await page.waitForTimeout(200);
	}
	return { opened, filled: await dlgState() };
}

out.beforeImport = await snapshot();
check("页面载入即看到已上传的那张", out.beforeImport.poseValues.some((v) => v === `${CUSTOM_LABEL}我的测试姿态 01`));

// 这一条是「点导入没反应」的回归：按钮被随机逻辑覆盖时，点击根本传不到选文件框
const first = await importViaDialog(FILES[1]);
check("选完图对话框自己打开", first.opened.open, first.opened);
check("名称默认取文件名", first.opened.name === "我的测试姿态 02", first.opened.name);
check("分类默认「自定义」", first.opened.cat === "自定义", first.opened.cat);
check("视角默认当前视角", first.opened.angle === "front", first.opened.angle);
check("视角只列五个具体角度", first.opened.angleOptions.join(",") === "front,high,low,side,diag", first.opened.angleOptions);
check("对话框里有预览", first.opened.hasPreview, first.opened.hasPreview);
check("对话框不撑出滚动条", first.opened.overflow <= 1, first.opened.overflow);

// ---------- 3. 自定义名称 / 分类 / 视角 ----------
await page.fill(`${HOST} .gp-dlg-name`, "我的角色");
await page.fill(`${HOST} .gp-dlg-cat`, "我的分类");
await page.selectOption(`${HOST} .gp-dlg-angle`, "side");
await page.waitForTimeout(200);
out.hintNew = (await dlgState()).hint;
check("新姿态提示会新建", /会新建姿态「我的角色」/.test(out.hintNew || ""), out.hintNew);

await page.click(`${HOST} .gp-dlg-ok`);
await page.waitForFunction(
	() => /已导入/.test(document.querySelector('[data-testid="dom-widgets"] .gp-count')?.textContent || ""),
	{ timeout: 8000 },
);
await page.waitForTimeout(600);
out.dlgClosed = await dlgState();
check("导入后对话框自动关闭", !out.dlgClosed.open, out.dlgClosed.open);

const afterCustom = await getIndex();
const mine = afterCustom.poses.filter((p) => p.root === "custom");
const role = mine.find((p) => p.name === "我的角色");
check("索引里用了自定义名称", !!role, mine.map((p) => p.name));
check("分类记成「我的分类」", role?.cat === "我的分类", role?.cat);
check("视角记成侧面", !!role?.angles.side, Object.keys(role?.angles || {}));
check("同名文件没有覆盖原图", role?.angles.side?.img !== role?.angles.front?.img, role?.angles);

out.afterCustom = await snapshot();
check("下拉框就地多出新姿态（未刷新页面）", out.afterCustom.poseValues.includes(`${CUSTOM_LABEL}我的角色`));
check("固定模式自动选中新导入的那张", out.afterCustom.poseValue === `${CUSTOM_LABEL}我的角色`, out.afterCustom.poseValue);
check("分类下拉多出「我的分类」", out.afterCustom.catValues.includes("我的分类"), out.afterCustom.catValues);
check("视角跟着切到刚导入的侧面", out.afterCustom.angleValue === "侧面", out.afterCustom.angleValue);
check("预览切到自定义图", (out.afterCustom.stageSrc || "").includes("/guliposes/custom/img/"), out.afterCustom.stageSrc);
check("栅格多出 2 个自定义格", out.afterCustom.customCells === 2, out.afterCustom.customCells);
check("面板高度没被撑破", out.afterCustom.height === out.beforeImport.height, [
	out.beforeImport.height,
	out.afterCustom.height,
]);

// ---------- 4. 同名不同视角 → 合并成一个姿态 ----------
const second = await importViaDialog(FILES[1], { name: "我的角色", cat: "我的分类", angle: "front" });
out.hintMerge = second.filled.hint;
check("已有同名同分类时提示会合并视角", /会作为「我的角色」的正面视角加入/.test(out.hintMerge || ""), out.hintMerge);

await page.click(`${HOST} .gp-dlg-ok`);
await page.waitForFunction(
	() => /已导入/.test(document.querySelector('[data-testid="dom-widgets"] .gp-count')?.textContent || ""),
	{ timeout: 8000 },
);
await page.waitForTimeout(600);

const afterMerge = await getIndex();
const merged = afterMerge.poses.filter((p) => p.root === "custom");
const roleMerged = merged.find((p) => p.name === "我的角色");
check("合并后仍是一个姿态", merged.length === 2, merged.map((p) => p.name));
check("合并后有两个视角", Object.keys(roleMerged?.angles || {}).length === 2, Object.keys(roleMerged?.angles || {}));
check("两个视角各有一张图", new Set(Object.values(roleMerged?.angles || {}).map((a) => a.img)).size === 2);
out.afterMerge = await snapshot();
check("同名姿态在下拉里只出现一次", out.afterMerge.poseValues.filter((v) => v === `${CUSTOM_LABEL}我的角色`).length === 1);

// ---------- 5. 同名同视角 → 另存为新姿态，不丢图 ----------
const third = await importViaDialog(FILES[1], { name: "我的角色", angle: "front" });
out.hintDup = third.filled.hint;
check("同名同视角提示会另存一份", /另存为「我的角色 \(2\)」/.test(out.hintDup || ""), out.hintDup);
await page.click(`${HOST} .gp-dlg-ok`);
await page.waitForTimeout(1400);
const afterDup = await getIndex();
check("另存后多出一个姿态", afterDup.poses.filter((p) => p.root === "custom").length === 3, afterDup.poses.filter((p) => p.root === "custom").map((p) => p.name));

// 把它删掉，别影响后面的计数
const dupPose = afterDup.poses.find((p) => p.root === "custom" && p.name === "我的角色 (2)");
await remove(Object.values(dupPose.angles).map((a) => a.img));
await page.waitForTimeout(300);

// ---------- 6. 剪贴板粘贴导入 ----------
await page.evaluate(() => {
	const node = window.app.graph._nodes.find((x) => x.type === "GuliPosePicker");
	node.is_selected = true; // 真实使用里点一下节点就会选中
});
await page.evaluate(
	() =>
		new Promise((resolve) => {
			const canvas = document.createElement("canvas");
			canvas.width = 300;
			canvas.height = 400;
			const ctx = canvas.getContext("2d");
			ctx.fillStyle = "#9099a8";
			ctx.fillRect(0, 0, 300, 400);
			ctx.fillStyle = "#ffffff";
			ctx.fillRect(90, 60, 120, 280);
			canvas.toBlob((blob) => {
				const dt = new DataTransfer();
				dt.items.add(new File([blob], "剪贴板测试.png", { type: "image/png" }));
				document.dispatchEvent(
					new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }),
				);
				resolve();
			}, "image/png");
		}),
);
await page.waitForTimeout(400);
out.clip = await dlgState();
check("Ctrl+V 能打开导入对话框", out.clip.open, out.clip.open);
check("剪贴板图默认名取文件名", out.clip.name === "剪贴板测试", out.clip.name);
check("剪贴板图也有预览", out.clip.hasPreview, out.clip.hasPreview);
await page.click(`${HOST} .gp-dlg-ok`);
await page.waitForTimeout(1400);
const afterClip = await getIndex();
check("剪贴板图进了库", afterClip.poses.filter((p) => p.root === "custom").some((p) => p.name === "剪贴板测试"));

// ---------- 7. 随机按钮没被弄坏 ----------
const beforeShuffle = (await snapshot()).poseValue;
for (let i = 0; i < 12; i++) {
	await page.click(`${HOST} .gp-shuffle`);
	await page.waitForTimeout(90);
}
out.afterShuffle = await snapshot();
check("点「随机」会换一个姿态", out.afterShuffle.poseValue !== beforeShuffle, [beforeShuffle, out.afterShuffle.poseValue]);
check("随机后仍是固定选中", out.afterShuffle.poseValue.length > 0);

// ---------- 8. 随机模式也要认自定义姿态 ----------
// 页脚这时还挂着「已导入」提示（5 秒），等它过期再读候选数
await page.waitForTimeout(5200);
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

await setW("模式", "范围内随机");
await setW("筛选系列", "我的姿态");
await page.waitForTimeout(700);
out.scoped = await snapshot();
check("范围内随机能圈到自定义姿态", out.scoped.foot === "候选 3 个", out.scoped.foot);
check("候选数与格数一致", out.scoped.cells === 3, out.scoped.cells);

await setW("模式", "全库随机");
await page.waitForTimeout(700);
out.allRandom = await snapshot();
check("全库随机含自定义姿态", out.allRandom.foot === "候选 291 个", out.allRandom.foot);

await setW("模式", "固定选中");
await page.waitForTimeout(500);

// ---------- 9. 右键删掉「我的测试姿态 01」 ----------
// 自定义姿态的编号按文件名排序，不一定是 C001，所以按名字找格子
await page.evaluate(() => {
	const cell = [...document.querySelectorAll(".gp-cell")].find((c) => c.title.includes("我的测试姿态 01"));
	cell.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, button: 2 }));
});
await page.waitForTimeout(1600);

out.afterDelete = await snapshot();
check("删掉的图从下拉里消失", !out.afterDelete.poseValues.includes(`${CUSTOM_LABEL}我的测试姿态 01`));
check("删掉的图从栅格消失", out.afterDelete.customCells === 2, out.afterDelete.customCells);
check("删除有中文提示", /已删除 我的测试姿态 01/.test(out.afterDelete.foot || ""), out.afterDelete.foot);

await browser.close();

// ---------- 10. 清场 ----------
await cleanAll();
const fin = await getIndex();
check("清完退回内置库", fin.poses.length === 288, fin.poses.length);
check("清完没有自定义系列", !fin.series.some((s) => s.name === "我的姿态"));

console.log(JSON.stringify({ out, fails, errs: errs.slice(0, 3) }, null, 2));
process.exit(fails.length ? 1 : 0);
