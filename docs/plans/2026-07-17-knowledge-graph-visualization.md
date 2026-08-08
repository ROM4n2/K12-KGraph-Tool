# 知识图谱可视化（Phase 2）实施计划

> **For agentic workers:** 本计划为单文件 HTML 项目（无构建、无 pytest），TDD 任务结构**不适用**。每个任务的验证端为"浏览器打开 index.html → 上传 CSV → 视觉/控制台检查"，已在每任务末尾以 **✅ 验证** 形式给出具体操作步骤。任务粒度按功能切分，每任务一次脚本区级改动，完成后 commit。

**Goal:** 将 `AppData` 中已加载的知识图谱数据渲染为可交互的 Cytoscape.js 网络图，支持按关系着色、拖拽缩放、点击节点查看详情、多布局切换。

**Architecture:** 在现有 `index.html` 的 `#cy` 容器上初始化 Cytoscape 实例，复用 `AppData.nodes/edges/relations` 数据源；通过 `relations→颜色` 映射实现边着色；通过 `cy.on('tap')` 事件 + 右侧详情面板实现节点信息展示；通过 `cy.layout().run()` 实现布局切换。

**Tech Stack:** 原生 JS + Cytoscape.js 3.26（已 CDN 引入）+ Tailwind CSS

## Global Constraints

- **单文件交付**：所有代码写入 `D:\Code\K12-KGraph-Tool\index.html`，不新增文件
- **无构建/无框架**：仅原生 JS + CDN 库（Cytoscape.js / Tailwind / Papaparse 已引入）
- **数据源复用**：直接读取 `AppData.nodes`（Map）、`AppData.edges`（Array）、`AppData.relations`（Set），不重新解析
- **深色主题**：节点文字、背景、面板配色与现有 slate-900 深色风格统一
- **性能**：10,685 节点 + 23,278 边，需启用 Cytoscape 的 `hideEdgesOnViewport` / `textureOnViewport` 优化，初始布局用 `grid`（最快），力导向 `cose` 作为可选项
- **版本标记**：完成后将 `APP_VERSION` 从 `v0.1.0 · Phase 1` 更新为 `v0.2.0 · Phase 2`
- **Git 提交**：每任务一次 commit，message 格式 `feat(phase2): <功能描述>`
- **验证环境**：Chromium 内核（Edge/Chrome），双击 `index.html` 打开

---

## 文件结构总览

仅修改一个文件：`D:\Code\K12-KGraph-Tool\index.html`

涉及改动的代码区段（按现有行号）：
- **L232** `<div id="cy">` — 移除 hidden，设为可见容器
- **L260-266** `AppData` — 新增 `cy: null` 字段存 Cytoscape 实例
- **L277** `APP_VERSION` — 更新版本号
- **L554-595** `handleGraphFile` — 解析成功后调用图谱渲染
- **新增** `initCytoscape()` — 初始化 Cytoscape 实例
- **新增** `renderGraph()` — 将 AppData 注入 cy 并布局
- **新增** `buildRelationColorMap()` — 关系→颜色映射
- **新增** `bindNodeEvents()` — 点击节点详情面板
- **新增** `initLayoutSwitcher()` — 布局切换控件
- **新增** 右侧详情面板 HTML（主内容区）
- **新增** 布局切换按钮组 HTML（顶部工具栏）

---

## Task 1：Cytoscape 容器可见化 + 实例初始化

**目标：** 让 `#cy` 容器可见，并在 AppData 中预留 `cy` 字段，初始化一个空 Cytoscape 实例。

**修改：**
- `index.html` L232：移除 `class="hidden"`，改为 `class="flex-1"`（占满主内容区）
- `index.html` L260-266：`AppData` 新增 `cy: null` 字段
- `index.html` 在 `<!-- ===== 5. CSV 解析函数 ===== -->` 之前新增 `<!-- ===== 9. Cytoscape 图谱引擎 ===== -->` 脚本区，写入 `initCytoscape()` 函数

**`initCytoscape()` 函数签名：**
```javascript
function initCytoscape() {
  const container = document.getElementById('cy');
  AppData.cy = cytoscape({
    container: container,
    elements: [],              // 初始空，由 renderGraph 注入
    style: buildGlobalStyle(), // 基础样式
    minZoom: 0.1,
    maxZoom: 5,
    wheelSensitivity: 0.3,
    // 性能优化：大数据集下隐藏视口外边
    hideEdgesOnViewport: true,
    textureOnViewport: true,
  });
  return AppData.cy;
}
```

**`buildGlobalStyle()` 返回 Cytoscape stylesheet 数组：**
```javascript
function buildGlobalStyle() {
  return [
    { selector: 'node', style: {
      'background-color': '#38bdf8',
      'label': 'data(label)',
      'color': '#e2e8f0',
      'font-size': '10px',
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'width': 18, 'height': 18,
      'border-width': 1, 'border-color': '#0ea5e9',
      'text-background-color': '#0f172a',
      'text-background-opacity': 0.8,
      'text-background-padding': 2,
    }},
    { selector: 'edge', style: {
      'width': 1.5,
      'curve-style': 'bezier',
      'target-arrow-shape': 'triangle',
      'target-arrow-color': '#94a3b8',
      'line-color': '#94a3b8',
      'opacity': 0.6,
    }},
    { selector: 'node:selected', style: {
      'border-width': 3, 'border-color': '#fbbf24',
      'width': 24, 'height': 24,
    }},
    { selector: 'node.highlight', style: {
      'border-width': 3, 'border-color': '#fbbf24',
      'background-color': '#fbbf24',
    }},
  ];
}
```

**✅ 验证：**
1. 双击 `index.html` 打开
2. 主内容区（欢迎卡片位置）应显示一个**深色空白画布**（Cytoscape 容器），不再显示欢迎卡片
3. 按 F12 打开控制台，输入 `AppData.cy` 应返回 Cytoscape 对象（不是 null/undefined）
4. 控制台无报错

**Commit：**
```bash
git add index.html
git commit -m "feat(phase2): 初始化 Cytoscape 容器与空实例"
```

---

## Task 2：关系类型→颜色映射

**目标：** 为 9 种关系类型各分配一种高对比度颜色，供边着色使用。

**修改：**
- 在 Task 1 的脚本区新增 `RELATION_COLORS` 常量 + `buildRelationColorMap()` 函数

**代码：**
```javascript
// 9 种关系类型配色（高对比度，深色背景可读）
const RELATION_COLORS = {
  'is_a':              '#38bdf8', // 青蓝
  'prerequisites_for': '#f59e0b', // 琥珀
  'relates_to':        '#a78bfa', // 紫
  'verifies':          '#34d399', // 翠绿
  'tests_concept':     '#fb7185', // 玫瑰
  'tests_skill':       '#f97316', // 橙
  'appears_in':        '#60a5fa', // 蓝
  'leads_to':          '#facc15', // 黄
  'is_part_of':        '#94a3b8', // 灰
};

/**
 * 根据 AppData.relations 动态构建 {relation: color} 映射
 * 未在预设中的关系类型自动分配备用色
 */
function buildRelationColorMap() {
  const colors = { ...RELATION_COLORS };
  const fallback = ['#e879f9', '#22d3ee', '#a3e635', '#fb923c', '#f472b6', '#2dd4bf', '#c084fc', '#fde047'];
  let fi = 0;
  for (const rel of AppData.relations) {
    if (!colors[rel]) {
      colors[rel] = fallback[fi % fallback.length];
      fi++;
    }
  }
  return colors;
}
```

**✅ 验证：**
1. 打开 `index.html`，F12 控制台输入 `buildRelationColorMap()`
2. 应返回一个对象，包含 9 个键（关系类型），每个值为 `#xxxxxx` 颜色串
3. 输入 `RELATION_COLORS['is_a']` 应返回 `'#38bdf8'`

**Commit：**
```bash
git add index.html
git commit -m "feat(phase2): 添加关系类型到颜色的映射表"
```

---

## Task 3：数据注入 + 渲染函数

**目标：** 实现 `renderGraph()`，将 `AppData.nodes/edges` 转换为 Cytoscape 元素并注入，边按关系着色。

**修改：**
- 在脚本区新增 `renderGraph()` 函数
- 修改 `handleGraphFile`（L554-595）：在 `updateStats()` 之后调用 `renderGraph()`

**`renderGraph()` 函数：**
```javascript
function renderGraph() {
  if (!AppData.cy) initCytoscape();
  const cy = AppData.cy;
  const colorMap = buildRelationColorMap();

  // 清空旧数据
  cy.elements().remove();

  // 注入节点
  const nodeEls = [];
  for (const [id, node] of AppData.nodes) {
    nodeEls.push({ data: { id: id, label: node.label || id } });
  }
  cy.add(nodeEls);

  // 注入边（按关系着色）
  const edgeEls = [];
  for (const edge of AppData.edges) {
    edgeEls.push({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        relation: edge.relation,
        lineColor: colorMap[edge.relation] || '#94a3b8',
      }
    });
  }
  cy.add(edgeEls);

  // 应用边的动态颜色
  cy.style().selector('edge').style({
    'line-color': 'data(lineColor)',
    'target-arrow-color': 'data(lineColor)',
  }).update();

  // 初始布局（grid 最快，适合大数据集首次渲染）
  cy.layout({ name: 'grid', padding: 10, fit: true }).run();

  // 适应画布
  cy.fit(null, 30);

  console.log(`[Cytoscape] 渲染完成：${nodeEls.length} 节点 / ${edgeEls.length} 边`);
}
```

**修改 `handleGraphFile` 中的成功分支（在 `updateStats()` 之后加一行）：**
```javascript
        // UI 更新
        updateStats();
        renderGraph();                       // ← 新增：渲染图谱
        setUploadBadge('graph', 'success', file.name);
```

**✅ 验证：**
1. 打开 `index.html`，上传 `data/k12-kgraph.csv`
2. 画布上应出现**网格状排布**的节点（小圆点），10,685 个节点可能较密集但可见
3. 控制台输入 `AppData.cy.elements().nodes().length` 应返回 `10685`
4. 控制台输入 `AppData.cy.elements().edges().length` 应返回 `23278`
5. 控制台应打印 `[Cytoscape] 渲染完成：10685 节点 / 23278 边`
6. 鼠标滚轮可缩放，拖拽画布可平移

**Commit：**
```bash
git add index.html
git commit -m "feat(phase2): 实现 renderGraph 数据注入与初始网格布局"
```

---

## Task 4：点击节点详情面板

**目标：** 点击节点时，右侧弹出面板显示节点名称、关联边数、关系类型分布、掌握度标记。

**修改：**
- 主内容区 HTML：在 `#cy` 之后新增一个右侧浮动详情面板（默认隐藏）
- 脚本区新增 `bindNodeEvents()` 函数，监听 `tap` 事件
- 在 `initCytoscape()` 末尾调用 `bindNodeEvents()`

**详情面板 HTML（加在 `<div id="cy">` 之后）：**
```html
<!-- 节点详情面板（点击节点时显示） -->
<div id="nodePanel" class="absolute top-4 right-4 w-72 bg-slate-800/90 border border-slate-700 rounded-xl p-4 shadow-2xl backdrop-blur-sm hidden z-20">
  <div class="flex items-center justify-between mb-3">
    <h3 class="text-sm font-semibold text-brand-400">节点详情</h3>
    <button id="closeNodePanel" class="text-slate-400 hover:text-slate-200 text-lg leading-none">&times;</button>
  </div>
  <div class="space-y-2 text-sm">
    <div><span class="text-slate-400">名称：</span><span id="npName" class="text-slate-100 font-medium"></span></div>
    <div><span class="text-slate-400">ID：</span><span id="npId" class="text-slate-300 text-xs font-mono"></span></div>
    <div><span class="text-slate-400">关联边：</span><span id="npEdgeCount" class="text-emerald-400"></span></div>
    <div>
      <span class="text-slate-400">关系分布：</span>
      <div id="npRelations" class="mt-1 flex flex-wrap gap-1"></div>
    </div>
    <div class="pt-2 border-t border-slate-700">
      <span class="text-slate-400">掌握度：</span>
      <select id="npMastered" class="ml-2 bg-slate-700 text-slate-200 text-xs rounded px-2 py-1 border border-slate-600">
        <option value="none">未学</option>
        <option value="learning">已学</option>
        <option value="weak">薄弱</option>
        <option value="mastered">已掌握</option>
      </select>
    </div>
  </div>
</div>
```

**`bindNodeEvents()` 函数：**
```javascript
function bindNodeEvents() {
  const cy = AppData.cy;
  const panel = document.getElementById('nodePanel');

  // 点击节点 → 显示详情
  cy.on('tap', 'node', (evt) => {
    const node = evt.target;
    const nodeId = node.id();
    const nodeData = AppData.nodes.get(nodeId);

    // 高亮当前节点及其邻居
    cy.elements().removeClass('highlight');
    node.addClass('highlight');
    node.neighborhood('node').addClass('highlight');

    // 统计关联边
    const connectedEdges = node.connectedEdges();
    const relCount = {};
    connectedEdges.forEach(e => {
      const rel = e.data('relation');
      relCount[rel] = (relCount[rel] || 0) + 1;
    });

    // 填充面板
    document.getElementById('npName').textContent = nodeData ? nodeData.label : nodeId;
    document.getElementById('npId').textContent = nodeId;
    document.getElementById('npEdgeCount').textContent = connectedEdges.length;

    // 关系分布徽章
    const relContainer = document.getElementById('npRelations');
    const colorMap = buildRelationColorMap();
    relContainer.innerHTML = '';
    for (const [rel, count] of Object.entries(relCount)) {
      const badge = document.createElement('span');
      badge.className = 'text-xs px-1.5 py-0.5 rounded';
      badge.style.backgroundColor = (colorMap[rel] || '#94a3b8') + '30';
      badge.style.color = colorMap[rel] || '#94a3b8';
      badge.textContent = `${rel}(${count})`;
      relContainer.appendChild(badge);
    }

    // 掌握度
    const mastered = nodeData ? nodeData.mastered : 'none';
    document.getElementById('npMastered').value = mastered;

    // 显示面板
    panel.classList.remove('hidden');
  });

  // 点击空白 → 隐藏面板
  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      panel.classList.add('hidden');
      cy.elements().removeClass('highlight');
    }
  });

  // 关闭按钮
  document.getElementById('closeNodePanel').addEventListener('click', () => {
    panel.classList.add('hidden');
    cy.elements().removeClass('highlight');
  });

  // 掌握度变更 → 写入 AppData
  document.getElementById('npMastered').addEventListener('change', (e) => {
    const nodeId = document.getElementById('npId').textContent;
    const nodeData = AppData.nodes.get(nodeId);
    if (nodeData) {
      nodeData.mastered = e.target.value;
      persistToStorage();
    }
  });
}
```

**✅ 验证：**
1. 上传 CSV 渲染图谱后，**点击任意节点**
2. 右侧应弹出详情面板，显示：节点名称、ID、关联边数、关系类型彩色徽章、掌握度下拉框
3. 被点击节点及其邻居应**高亮**（黄色边框），其余节点淡化
4. 点击空白区域 → 面板隐藏，高亮清除
5. 切换掌握度下拉框后刷新页面，再点开同一节点 → 掌握度应保持（localStorage 持久化）

**Commit：**
```bash
git add index.html
git commit -m "feat(phase2): 添加节点详情面板与点击高亮交互"
```

---

## Task 5：布局切换控件

**目标：** 在画布顶部添加布局切换按钮组（网格 / 力导向 / 圆形），点击后重新布局。

**修改：**
- 主内容区 HTML：在 `#cy` 之前新增一个顶部工具栏（绝对定位，左上）
- 脚本区新增 `runLayout(name)` 函数
- 工具栏按钮绑定事件

**工具栏 HTML（加在 `<div id="cy">` 之前）：**
```html
<!-- 图谱工具栏 -->
<div id="graphToolbar" class="absolute top-4 left-4 z-20 flex items-center gap-1 bg-slate-800/80 border border-slate-700 rounded-lg px-2 py-1.5 backdrop-blur-sm">
  <span class="text-xs text-slate-400 px-1">布局：</span>
  <button data-layout="grid" class="layout-btn px-2 py-1 text-xs rounded bg-brand-600/30 text-brand-400 border border-brand-600/40">网格</button>
  <button data-layout="cose" class="layout-btn px-2 py-1 text-xs rounded text-slate-300 hover:bg-slate-700/50">力导向</button>
  <button data-layout="circle" class="layout-btn px-2 py-1 text-xs rounded text-slate-300 hover:bg-slate-700/50">圆形</button>
  <button data-layout="concentric" class="layout-btn px-2 py-1 text-xs rounded text-slate-300 hover:bg-slate-700/50">同心圆</button>
  <span class="w-px h-4 bg-slate-600 mx-1"></span>
  <button id="fitBtn" class="px-2 py-1 text-xs rounded text-slate-300 hover:bg-slate-700/50" title="适应画布">⊡ 适应</button>
</div>
```

**`runLayout(name)` 函数：**
```javascript
function runLayout(name) {
  if (!AppData.cy) return;
  const cy = AppData.cy;
  const configs = {
    grid:       { name: 'grid',       padding: 10, fit: true },
    cose:       { name: 'cose',       padding: 30, fit: true, animate: true, animationDuration: 800,
                  randomize: false, componentSpacing: 80, nodeRepulsion: 800000 },
    circle:     { name: 'circle',     padding: 30, fit: true, animate: true, animationDuration: 500 },
    concentric: { name: 'concentric', padding: 30, fit: true, animate: true, animationDuration: 500,
                  concentric: (ele) => ele.degree(), levelWidth: () => 2 },
  };
  const cfg = configs[name] || configs.grid;
  cy.layout(cfg).run();

  // 更新按钮高亮
  document.querySelectorAll('.layout-btn').forEach(btn => {
    if (btn.dataset.layout === name) {
      btn.className = 'layout-btn px-2 py-1 text-xs rounded bg-brand-600/30 text-brand-400 border border-brand-600/40';
    } else {
      btn.className = 'layout-btn px-2 py-1 text-xs rounded text-slate-300 hover:bg-slate-700/50';
    }
  });
}
```

**事件绑定（在 `initCytoscape()` 末尾或 DOMContentLoaded 中）：**
```javascript
  // 布局切换
  document.querySelectorAll('.layout-btn').forEach(btn => {
    btn.addEventListener('click', () => runLayout(btn.dataset.layout));
  });
  document.getElementById('fitBtn').addEventListener('click', () => cy.fit(null, 30));
```

**✅ 验证：**
1. 上传 CSV 后，左上角应显示工具栏（网格/力导向/圆形/同心圆/适应）
2. 点击「力导向」→ 节点开始动画重组，约 1 秒后稳定为力导向布局
3. 点击「圆形」→ 节点重排为圆形
4. 点击「适应」→ 图谱自动缩放适应画布
5. 当前激活的布局按钮高亮为青蓝色

**Commit：**
```bash
git add index.html
git commit -m "feat(phase2): 添加布局切换控件（网格/力导向/圆形/同心圆）"
```

---

## Task 6：关系类型图例 + 性能优化

**目标：** 在画布底部添加 9 种关系的颜色图例；启用 Cytoscape 大数据优化选项。

**修改：**
- 主内容区 HTML：底部新增图例条（绝对定位，左下）
- `initCytoscape()` 中启用 `hideEdgesOnViewport`/`textureOnViewport`（Task 1 已加，此处确认）
- 脚本区新增 `renderLegend()` 函数，动态根据 `AppData.relations` 生成图例

**图例 HTML（加在工具栏之后、`#cy` 之内即可，绝对定位左下）：**
```html
<!-- 关系图例 -->
<div id="legendPanel" class="absolute bottom-4 left-4 z-20 bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 backdrop-blur-sm">
  <div class="text-xs text-slate-400 mb-1">关系类型</div>
  <div id="legendItems" class="flex flex-wrap gap-x-3 gap-y-1 max-w-md"></div>
</div>
```

**`renderLegend()` 函数：**
```javascript
function renderLegend() {
  const container = document.getElementById('legendItems');
  const colorMap = buildRelationColorMap();
  container.innerHTML = '';
  for (const rel of AppData.relations) {
    const item = document.createElement('span');
    item.className = 'text-xs flex items-center gap-1';
    item.innerHTML = `<span class="inline-block w-3 h-1.5 rounded" style="background:${colorMap[rel] || '#94a3b8'}"></span><span class="text-slate-300">${rel}</span>`;
    container.appendChild(item);
  }
}
```

**在 `renderGraph()` 末尾调用 `renderLegend()`：**
```javascript
  cy.fit(null, 30);
  renderLegend();                      // ← 新增
  console.log(`[Cytoscape] 渲染完成：...`);
```

**性能优化补充（在 `initCytoscape()` 的 cytoscape() 配置中确认已有）：**
```javascript
    hideEdgesOnViewport: true,    // 拖拽时隐藏视口外边
    textureOnViewport: true,      // 视口移动时用纹理替代重绘
    motionBlur: false,            // 关闭运动模糊
```

**✅ 验证：**
1. 上传 CSV 后，底部左侧应显示 9 种关系的彩色图例（颜色与图中边颜色一致）
2. 快速拖拽画布时画面流畅，无明显卡顿
3. 缩放时节点/边响应正常

**Commit：**
```bash
git add index.html
git commit -m "feat(phase2): 添加关系图例与大数据渲染性能优化"
```

---

## Task 7：欢迎卡片逻辑调整 + 版本号更新

**目标：** 有数据时隐藏欢迎卡片、显示图谱；无数据时仍显示欢迎卡片。版本号更新为 Phase 2。

**修改：**
- `APP_VERSION`（L277）：`v0.1.0 · Phase 1` → `v0.2.0 · Phase 2`
- `renderGraph()` 开头：隐藏欢迎卡片
- 新增 `checkWelcomeVisibility()` 函数，在页面加载时根据是否有数据决定显示欢迎卡片还是图谱
- `handleGraphFile` 成功分支：调用 `checkWelcomeVisibility()`

**`checkWelcomeVisibility()` 函数：**
```javascript
function checkWelcomeVisibility() {
  const welcome = document.getElementById('welcomeCard');
  const cyDiv = document.getElementById('cy');
  const hasData = AppData.nodes.size > 0;
  if (hasData) {
    welcome.classList.add('hidden');
    cyDiv.classList.remove('hidden');
    cyDiv.classList.add('flex-1');
  } else {
    welcome.classList.remove('hidden');
    cyDiv.classList.add('hidden');
  }
}
```

**在 `renderGraph()` 最开头加：**
```javascript
  // 有数据 → 隐藏欢迎卡片，显示图谱
  document.getElementById('welcomeCard').classList.add('hidden');
  const cyDiv = document.getElementById('cy');
  cyDiv.classList.remove('hidden');
  cyDiv.classList.add('flex-1');
```

**✅ 验证：**
1. 首次打开（未上传数据）→ 显示欢迎卡片，画布空白
2. 上传图谱 CSV → 欢迎卡片消失，显示图谱
3. 底部状态栏版本号显示 `v0.2.0 · Phase 2`
4. 导航「知识图谱」按钮可点击切换（如有实现）

**Commit：**
```bash
git add index.html
git commit -m "feat(phase2): 欢迎卡片逻辑调整与版本号更新为 v0.2.0"
```

---

## 最终集成验证（全部任务完成后执行）

1. **打开** `index.html`，初始显示欢迎卡片
2. **上传** `data/k12-kgraph.csv` → 图谱渲染，节点可见，控制台打印 `10685 节点 / 23278 边`
3. **上传** `data/k12-bench.csv` → 题目数更新为 23638
4. **点击节点** → 右侧面板显示详情，高亮邻居
5. **切换布局** → 力导向/圆形/网格/同心圆均正常
6. **查看图例** → 底部 9 种关系颜色正确
7. **拖拽缩放** → 流畅无卡顿
8. **刷新页面** → 数据从 localStorage 恢复（如已实现持久化读取）
9. **控制台无报错**

---

## 执行顺序

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7
```

每个任务完成后 commit，全部完成后 push 到 GitHub：
```bash
git push origin master
```
