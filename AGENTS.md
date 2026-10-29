# AGENTS.md

给在本仓库工作的 AI 与开发者。**动手前先读本文件**；新增或修改功能前先过「二、设计自检」。
本文件与 `ComfyUI-GuliNodes/AGENTS.md` 同源，规则能共用就共用，本项目另有出入的地方写在对应条目里。

## 一、项目与落位

把白模（3D mannequin 线稿）姿态图库搬进画布：一个节点 **GG 姿态库**（`GuliPosePicker`，分类 `GuliPoses`），
节点内画廊选姿态与视角，只输出一张图。定位是**轻量、中文友好、零额外 Python 依赖**。

| 位置 | 职责 |
| --- | --- |
| `__init__.py` | 插件入口，只导入映射并声明 `WEB_DIRECTORY`，**不写逻辑**（路由在 `api_routes` 导入时自注册） |
| `nodes.py` | 节点定义、三种取图模式、`IS_CHANGED` 缓存策略、`ui.picked` 回传 |
| `pose_db.py` | 索引缓存、候选池与回退链、视角解析、缺图回退 |
| `api_routes.py` | 索引 / 缩略图 / 原图的只读路由，加自定义姿态的上传与删除，全部带路径穿越防护 |
| `web/` | 前端扩展，文件名一律 `gg-<功能>.js` |
| `poses/img/` | 内置原图，1439 张 900×1200 **WebP**（约 104 MB），**随仓库分发** |
| `poses/thumbs/` | 画廊缩略图，**不入库**——缺失时由 `pose_db.ensure_thumb()` 用原图现生成 |
| `poses/index.json` | 索引，**随仓库分发**；`img` 字段记实际落盘的扩展名 |
| `poses/custom/` | 用户自己导入的姿态图，**不入版本库**；缩略图由插件生成在 `custom/thumbs/`，名称 / 分类 / 视角记在 `custom/meta.json` |
| `data/zh-dict.csv` | 日→中对照表，重建索引时需要 |
| `tools/` | `build_pose_db.py` 建索引、`optimize_library.py` 转 WebP；`tools/verify/*.mjs` 无头验证 |

- 节点 ID `GuliPosePicker` 稳定且唯一，改动会断旧工作流。
- 显示名用**中文**，统一 `GG ` 前缀（与 GuliNodes 的 `GG 图像宽高` 等一致）。
- 分类统一 `GuliPoses`。
- 新增前端扩展放 `web/`，`app.registerExtension({ name: "ComfyUI.GGPoses.<功能>" })`。

### 图库资源（`poses/`）

- **原图用 WebP，不用 PNG**。同一批白模线稿，PNG 要 343 MB，WebP q95 只要 104 MB（实测 PSNR 50.9 dB、最大像素差 8/255、放大 2.3 倍看不出差别）。仓库体积直接决定 clone 体验，这条不要退回 PNG。转换用 `tools/optimize_library.py`，`--dry-run` 可先估算。
- **缩略图不入库**。1439 张缩略图能从原图算出来，没必要让每个人下载。`pose_db.ensure_thumb(thumb_name)` 在文件缺失时用原图现生成（同 stem 不同后缀，`xxx.webp` → `xxx.jpg`），走临时文件 + `uuid` 后缀 + 原子 `replace`，并发请求同一张不会读到半个 JPEG。实测 288 张全部现场生成 2.8 s / 单张 57 ms，浏览器懒加载只取可视区。
- **索引的 `img` 字段必须写实际存在的文件名**。`build_pose_db.py` 的 `resolve_img()` 按 `.webp` → `.png` → `.jpg` 顺序找，找到哪个写哪个；`nodes.py` 用 `Image.open()` 读，WebP 与 PNG 走同一条路径，不需要分支。
- 改图库格式后要重跑 `build_pose_db.py`，否则索引还指着旧扩展名，画廊与节点都会 404。

### 自定义姿态库（`poses/custom/`）

- **不进 `poses/img/`**：内置库随时可能被 `build_pose_db.py` 重建，用户数据必须分开；靠扫描合并，不写进 `index.json`。
- **不加节点参数**：导入是资源管理，结果直接落进既有的 `姿态` / `筛选系列` / `筛选分类` 下拉，参数仍是 5 个，旧工作流照常打开。**这条是设计基线，不要再改成「加一个自定义库参数」**。
- 一个文件 = **一个视角**，`root="custom"`、系列 `我的姿态`；显示名 / 分类 / 视角记在 `custom/meta.json`（`{文件名: {name, cat, angle}}`），**不要靠文件名编码这些信息**。
- **同名归并**：显示名相同 + 视角不同 = 同一个姿态的多个视角，合成一条记录；显示名相同 + 视角也相同 → 另起 `(2)` 后缀，**不覆盖、不丢图**。`label` / `no` 必须全局唯一（下拉与 `byLabel` 都按它索引），`no` 形如 `custom/<显示名>`。
- 扫描按「文件名+大小+修改时间」签名缓存；签名没变不重扫、不解码图片。`meta.json` 另按 mtime 缓存。导入/删除后把 `_custom_sig` 置 `None` 触发重扫。
- 缩略图由 `_make_thumb()` 生成（长边 320、透明铺白、JPEG 86），坏图跳过并在控制台报文件名。
- 文件名过 `safe_filename()`：去路径、去非法字符、补扩展名、躲 Windows 保留字、截 60 字符；删除走 `delete_custom()` 校验父目录，不接受任何相对路径。
- **导入接口一次收齐所有分片再落盘**：要先知道总张数，才能给「统一名称」自动补 `1 / 2 / 3` 序号。响应里带 `nos`（与 `saved` 一一对应），前端拿它跳转——显示名是用户填的，还可能在重名时被加序号，**不能从文件名反推 `no`**。
- **导入后要切到新图实际拥有的视角**：用户可能导入的是「侧面」，而画廊停在「正面」，不切就会显示「该角度缺图」。

## 二、动手前：设计自检（强制）

**适用范围**：新增节点、新增前端扩展、给节点加参数/选项/输出、重写已有能力。
**先过一遍下面 6 项并把结论说出来，再动代码。** 最常见的返工不是写错，而是「做出来了但本来不该做」。

1. **必要性**——已有能力换个用法能不能覆盖？是用户明确要求，还是「顺手加的」（顺手加的不做）？
2. **闭环**——后端 `pick`、前端交互、错误信息、文档四处都跟上了吗？空库 / 缺图 / 空候选集都想过吗？
   错误信息是中文且能说清「哪错了 + 怎么改」吗？新参数进旧工作流会不会回退默认？
3. **更优方案**——至少想两个再选一个。优先级：ComfyUI 原生机制 > 复用已有函数 > 新写前端补丁。
   **能用「把名字取成中文」解决的，就不要写显示层补丁**（见「三」）。
4. **中文参数**——显示名、参数名、选项值、输出名、分类、提示与错误信息一律中文（技术专名除外）。
5. **可简化**——参数越少越好：一个选择器能推导出来的不要暴露两个输入；选择器让某些输入失效时按「四」隐藏；默认值要能「不填也能用」。
6. **收尾**——同步中英双份 README（含更新记录）与致谢。

**结论指向「不做」或「改成改已有实现」时，这就是正确结果**，不要因为已经动手了就硬推下去。

## 三、命名与文案

- 用户可见的一切用中文：节点显示名、参数名、选项值、输出名、分类、tooltip、错误信息。
  技术专名保持原样（`IMAGE`、`Latent`、`PNG`、`lanczos` 等）。
- **参数名直接写成中文**（`模式` / `姿态` / `视角` / `筛选系列` / `筛选分类`），不要用英文标识符 + 显示层映射：
  ComfyUI 1.5x 前端的下拉框把 `widget.name` 直接画在按钮里，**不读 `widget.label` / `displayName`**。
  为这个写过「绘制期临时改 `name` 再还原」的补丁，属于能避免的复杂度，已删除。参数名中文同时让 `graphToPrompt()`
  的键、报错信息、第三方 API 调用全是中文，闭环一致。
- 同一概念跨插件用同一个词：与 GuliNodes 统一「视角」「系列」「分类」「模式」。
- 错误信息中文、可行动：说清哪里错了 + 怎么改，不要只抛原始异常。
- JS 用现代 ES module 写法，优先 `const` / `let`。
- 文件含中文与 Unicode，编辑时保持 UTF-8、换行 LF。

## 四、显示规则：不生效不展示

**原则（输入、输出都适用）**：节点只展示当前选择下真正生效的内容。
`pick()` 只在某个 `模式` 取值下才读的输入，对其它取值就是失效输入，必须隐藏。

当前口径（`applyVisibility()`）：

| 模式 | 露出 |
| --- | --- |
| 固定选中 | 模式 / 姿态 / 视角 |
| 全库随机 | 模式 / 视角 |
| 范围内随机 | 模式 / 视角 / 筛选系列 / 筛选分类 |

### 为什么这里是前端隐藏，而不是 `DynamicCombo`

GuliNodes 首选后端 `io.DynamicCombo`，本项目不适用：本节点含 **DOM 面板**、`IS_CHANGED` 与 `onExecuted` 联动，
且模式切换要同步重绘画廊——这些都必须由前端在同一时刻知道「现在是哪个模式」。所以照该文件「四」的例外分支走前端隐藏。

- 隐藏手法：`widget.computeSize = () => [0, -4]` + `widget.hidden = true`，原始 `computeSize` 存 Map 以便还原；
  收完之后 `node.setSize([w, node.computeSize()[1]])`。
- `applyVisibility()` 必须**幂等**、能在切换后重新同步、并对找不到的控件安全跳过；
  用 key 串（`showPose|showFilters`）去重，避免每次同步都重排节点。
- 三个调用点都不能少：`syncFromWidgets()` 末尾、`loadDB().then` 末尾（恢复工作流时模式可能不是固定）、`setup()` 末尾。
- 隐藏只影响绘制，`widgets_values` 的顺序与长度不变，提交与存档正常。

### 输出侧

- 只有一个输出 `姿态图`，**永远显示**，不做任何端口隐藏。
- **不要从 `node.outputs` 里删有效槽**：后端按 `origin_slot` 下标取 `cached.outputs[index]`，删下标会让后续端口错位。
- 旧工作流的兼容清理是唯一例外：历史上本节点有 `image / pose_name / pose_info` 三个槽，
  存档里的 `outputs` 数组会被 litegraph 原样恢复。`trimOutputs()` 只做「多余的尾巴从末尾往前摘」，
  始终保留下标 0，且包在 `try/catch` 里——清理失败不能连带把工作流打开搞崩。

## 五、前端红线

- 包装 LiteGraph / ComfyUI 原型方法时：**保存原函数、幂等安装、失败回退**。
  原型标记用 `__gpPosePatched`，实例标记用 `__guliposesApply`——**两者不能同名**，
  否则实例读 `this._xInstalled` 会顺着原型链拿到 `true`，整段逻辑被静默跳过。
- **优先包装原型，不要挂到画布实例的自有属性上**（`app.canvas.drawNode = ...` 会遮蔽原型，让其它扩展的补丁静默失效）。
- 绘制期临时改控件值必须在 `finally` 里还原，且**还原用启动时记下的原值**，不要用「当前值」——嵌套绘制会把值弄脏。
- **面板高度由用户决定，代码不许改节点高度**。`gallery.computeSize` 反算：
  `[width ?? node.size[0], max(MIN_GALLERY_H, node.size[1] - chromeHeight())]`——
  画廊吃掉节点剩余高度，用户拉高节点画廊就变高、栅格多显示几行。
  `chromeHeight()` = 标题栏 + 内边距 + **当前可见**的参数行数 × 24，参数显隐切换后画廊自然接管多出来的空间。
  `node.computeSize()` 求和时会回到 `node.size[1]`，自洽、不递归。
  - **禁止在 `applyVisibility()` 里 `node.setSize(...)`**：曾经那里有一行「切模式后按 computeSize 收紧高度」，
    导致 900 高的节点一切「全库随机」就被吸回 672。用户拉过的尺寸要被记住，切模式、切视角、换筛选都不许动它。
  - `trimOutputs()` 同理**只补高不压低**：摘掉旧输出槽后只在 `node.size[1] < need` 时补，绝不往回缩。
  - 没有采用 GuliNodes 的 `gg-panel-fit.js` 闭环（那是为「量内容 → 定高」的多段面板写的），
    这里画廊是「吃满剩余高度」的单一弹性块，方向相反。**改动超出这个前提时要重新量**，
    判据是 `host.scrollHeight` 与容器 `clientHeight` 相等（`tools/verify/layout.mjs` 已经在测），
    以及拉伸后 `rootH` 必须真的变大（`tools/verify/mode-visibility.mjs` 顺带量高度不变）。
- 面板宽度只能跟着节点走：`computeSize` 第一个返回值是 `width ?? node.size[0]`，不要给独立最小宽度。
- **栅格按条数平均分布，别固定列数**：先按可用宽度算 `maxCols`，再用 `ceil(n / ceil(n / maxCols))` 反推列数。
  7 张、上限 6 列时排 4 + 3，而不是 6 + 1。数量不超过一屏时保持 CSS `auto-fill`（格子不被拉大）。
  列数要跟着宽度重算（`ResizeObserver` + `requestAnimationFrame` 合并）。
- **CSS 变量 + `[data-*]` 属性表达状态，不写内联颜色**。本插件自带 `--gp-*` 变量（回退到 `--comfy-*`），
  不依赖 GuliNodes 的 `gg-ui-design.js`——两个插件必须能单独安装。
  深色 / 浅色都要可读：次要文字用 `color:var(--gp-fg);opacity:.55`，不要用 `--gp-dim`（浅色主题下太淡）。
- 不要用全局轮询做高频重绘；`MutationObserver` / `ResizeObserver` 回调必须防抖或 rAF 合并，
  回调里禁止整文档 `querySelectorAll` 或读 `offsetHeight` 这类强制回流的操作。
- **按钮一律用各自独立的类名 + 提前取好的引用，禁止 `querySelector(".共用类名")`**。
  曾经「导入」和「随机」共用 `gp-rnd`，随机逻辑用 `root.querySelector(".gp-rnd")` 取，而「导入」在 DOM 里排在前面 →
  它的 `onclick` 被随机逻辑覆盖，**点「导入」实际在随机抽一张**，浏览器根本没收到 `input.click()`。
- **验证必须点真实按钮**。用 `page.setInputFiles()` 直接往 `<input type=file>` 塞文件会**绕过按钮**，
  上面那个 bug 因此整整漏测一轮。回归用 `page.waitForEvent("filechooser")` 配合 `page.click(".gp-imp")`。
- 面板内的浮层（导入对话框）用 `.gp-dlg` 绝对定位盖在 `.gp-root` 上，`.gp-root` 需要 `position:relative`；
  隐藏用 `[hidden]{display:none}` 配 `el.hidden = true`，不要只靠 `display:flex`。
- 拖拽与粘贴都要在面板这一层 `preventDefault + stopPropagation`，否则画布会把图当节点素材吞掉。
  `paste` 监听挂 `document` 时要加「选中本节点 / 指针在面板上 / 对话框开着」的门槛，并在 `node.onRemoved` 里摘掉。

## 六、依赖策略

维持**零额外 Python 依赖**：只用 ComfyUI 环境自带的 `torch`、`PIL`、`numpy`。
不要引入 `cv2`、`kornia`、`mediapipe` 之类重包。前端无构建步骤，直接 ES module。

## 七、出处与致谢

- **`anhao/ai-pose-gallery-zh` 是灵感 + 数据双来源，用户明确要求「不能缺失」**，任何改 README 都要保留。
- 上游链条：`anhao/ai-pose-gallery-zh`（中文镜像 + 中文对照表）→ 原作者 ギア（`@giaaibusi` / `ai-pose-gallery.pages.dev`）。
- 图片与原始数据著作权归 ギア，本插件只做本地索引与画布内浏览；`LICENSE` 的 MIT 只覆盖代码。
- 借鉴外部实现要写进致谢表：**来源名称 + URL + 实际参考的功能**，三类引用别混——
  桥接（运行时调外部）、适配（基于已有实现改造）、思路参考（形态受启发、源码重写）。

## 八、文档

- `README.md` 与 `README_EN.md` **逐节对齐**，改一份必须同步另一份。
- 用户可感知的改动写进 `README.md` 的「更新记录」；只写结果（行为、参数、错误信息、兼容性），不写实现过程。
- 数字口径固定：**288 组姿态 / 1439 张图 / 4 系列 / 26 分类 / 5 视角**。
  上游仓库简介写的「1439 组 / 2878 张」是把文件数当组数了，不要照抄。

## 九、验证

- Python：`python -m py_compile nodes.py pose_db.py api_routes.py __init__.py`
- JS：`node --check web/gg-pose-gallery.js`
- 独立导入（不启动 ComfyUI）：`importlib` 载入包 → 打印 `NODE_CLASS_MAPPINGS`、`INPUT_TYPES()` 键名、
  `IS_CHANGED` 两种返回值。确认没把 `__init__` 写成必须依赖 `PromptServer` 才能导入。
- 起**隔离实例**再跑（不要动用户正在用的 8188）：

  ```bash
  python -s ComfyUI/main.py --port 8189 --cpu --disable-all-custom-nodes \
    --whitelist-custom-nodes ComfyUI-GuliPoses --disable-auto-launch
  ```

  ```bash
  COMFY_PORT=8189 node tools/verify/frontend-modes.mjs    # 筛选交集 / 仅分类 / 全库随机锁下拉 / 序列化恢复
  COMFY_PORT=8189 node tools/verify/queue-roundtrip.mjs   # 随机两次都重抽、固定第二次命中缓存、picked 回传
  COMFY_PORT=8189 node tools/verify/layout.mjs            # 无溢出、栅格高度、推荐行可见
  COMFY_PORT=8189 node tools/verify/mode-visibility.mjs   # 各模式可见控件与节点高度
  COMFY_PORT=8189 node tools/verify/custom-import.mjs     # 导入闭环（点导入弹框 / 名称分类视角 / 同名合并 / 剪贴板 / 右键删除 / 清场复原）
  ```

- 改到工具行或面板布局时要重量：`layout.mjs` 之外再量 `.gp-tools` 的 `getBoundingClientRect().height`
  与 `scrollWidth - clientWidth`，判断有没有换行或溢出（440 宽下工具行应保持 23px 一行）。
- **凡是「显示效果」的验证，一律以截图为准**。读 JS 对象的 `label` / `name` 只能证明数据对，
  证明不了画布上画的是什么——本项目中文化曾因此误判通过一轮。
- **服务端对 ≠ 画布对**：`/object_info` 返回 `output:["IMAGE"]` 时画布仍可能挂着 3 个输出槽（存档带出来的）。
  两边都要查。
- 清场：验证完停 8189、删临时目录；不要 kill 用户的 8188。

## 十、工作方式

- 先读相关文件，再改代码。
- 保持改动聚焦，不做无关格式化。
- 不要删除用户已有改动。
- 改完按「九、验证」跑一遍再交付；跑不过就如实说，不要报「已完成」。
