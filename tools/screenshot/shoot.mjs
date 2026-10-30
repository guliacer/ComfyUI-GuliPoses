import { chromium } from "playwright-core";

/*
 * 用无头浏览器打开本机 ComfyUI，把某个 Guli 节点摆到画布上截成 PNG。
 *
 *   npm i playwright-core
 *   node shoot.mjs GuliGarmentPicker ../docs/screenshots/node-garment.png 620 900
 *   python trim.py ../docs/screenshots/node-garment.png
 *
 * 需要 ComfyUI 正在跑（默认 http://127.0.0.1:8188）。
 */

// 把 Guli 节点画到画布上并截图（贴近内容裁剪，不留节点底部空白）。
// 关键点：
//  1. 节点宽度由画廊 widget 的 computeSize 决定，默认 210，要顶到 W 才是宽面板；
//  2. y 小于 ~110 会被 ComfyUI 顶部菜单压住；
//  3. 节点底部有一块为输出槽预留的空白 —— 量出推广行的实际底边，把节点高度收到那里；
//  4. headless 页面久不活动会弹 Reconnecting，拍照前藏掉。
// 本机 chromium 路径；换机器时改这里，或装完整 playwright 后删掉这行
const EXE = process.env.CHROME_PATH || "C:/Users/Admin/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe";
const [NODE, OUT, Ws, Hs] = [process.argv[2], process.argv[3], Number(process.argv[4]), Number(process.argv[5])];
const PX = 100, PY = 140, M = 12;

const b = await chromium.launch({ executablePath: EXE, headless: true });
// deviceScaleFactor 放在 newPage 的配置里不生效（实测输出还是 1x），必须走 context
const ctx = await b.newContext({ viewport: { width: Ws + 120, height: Hs + 320 }, deviceScaleFactor: 2 });
const p = await ctx.newPage();
await p.goto("http://127.0.0.1:8188/", { waitUntil: "domcontentloaded", timeout: 60000 });
await p.waitForFunction(() => window.app?.graph && window.LiteGraph, null, { timeout: 60000 });

await p.evaluate(({ NODE, Ws, Hs, PX, PY }) => {
  window.app.graph.clear();
  const n = window.LiteGraph.createNode(NODE);
  n.pos = [PX, PY];
  window.app.graph.add(n);
  window.app.canvas.ds.scale = 1;
  window.app.canvas.ds.offset = [0, 0];
  return new Promise((done) =>
    setTimeout(() => {
      const g = n.widgets.find((w) => w.name === "gulipose_gallery");
      if (g) g.computeSize = () => [Ws, Math.max(220, n.size[1] - 210)];
      n.setSize([Ws, Hs]);
      window.app.canvas.ds.offset = [0, 0];
      window.app.canvas.setDirty(true, true);
      setTimeout(done, 400);
    }, 500)
  );
}, { NODE, Ws, Hs, PX, PY });

await p.waitForFunction(
  () => {
    const imgs = [...document.querySelectorAll("img")].filter((i) => /\/guli(poses|garments|faces)\//.test(i.src));
    return imgs.length >= 8 && imgs.every((i) => i.complete && i.naturalWidth > 0);
  },
  null, { timeout: 40000 }
).catch(() => console.log("WARN 等图超时"));

// 预览调小一点，多露几行缩略图
await p.evaluate(() => {
  const r = document.querySelector(".gp-stage-range");
  if (!r) return;
  r.value = "34";
  r.dispatchEvent(new Event("input", { bubbles: true }));
});
await p.addStyleTag({ content: ".toast,.p-toast,.comfy-toast{display:none!important}" });
await p.evaluate(() => {
  for (const el of document.querySelectorAll("body *")) {
    if (el.children.length === 0 && /Reconnecting|连接中|重连/i.test(el.textContent || "")) {
      const box = el.closest("div");
      if (box) box.style.display = "none";
    }
  }
});
await p.waitForTimeout(1200);

// 把节点高度收到「最后一行内容 + 10px」，底部不再留空白，也就不会框进画布工具条
const real = await p.evaluate(({ PY }) => {
  const n = window.app.graph._nodes[0];
  const promo = document.querySelector(".gp-promo");
  if (promo) {
    const need = Math.ceil(promo.getBoundingClientRect().bottom - PY + 10);
    if (need > 300 && need < n.size[1]) n.setSize([n.size[0], need]);
  }
  window.app.canvas.setDirty(true, true);
  return { w: Math.round(n.size[0]), h: Math.round(n.size[1]) };
}, { PY });
await p.waitForTimeout(900);

const fin = await p.evaluate(() => {
  const n = window.app.graph._nodes[0];
  return { w: Math.round(n.size[0]), h: Math.round(n.size[1]) };
});
await p.screenshot({ path: OUT, clip: { x: PX - M, y: PY - M, width: fin.w + M * 2, height: fin.h + M * 2 } });
console.log(`${NODE}: 裁剪 ${fin.w + M * 2}x${fin.h + M * 2}（节点 ${fin.w}x${fin.h}，收高 ${real.h}->${fin.h}）`);
await b.close();
