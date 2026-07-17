# K12 知识图谱学习工具

> 纯前端离线运行的 K12 知识图谱可视化与刷题学习工具 —— 双击 `index.html` 即可使用，无需后端、无需安装。

## ✨ 功能特性

- **知识图谱可视化**：Cytoscape.js 渲染知识点网络图，不同关系类型用不同颜色线条
- **本地数据加载**：支持上传 CSV 三元组（head/relation/tail）和题库 CSV
- **学习功能**：知识点搜索高亮、前置知识路径、掌握度标记（未学/已学/薄弱/已掌握）
- **刷题模块**：选择题作答、自动判分、错题本自动收录、错题关联知识点跳转
- **体验优化**：拖拽缩放、明暗主题切换、图谱导出为图片

## 🚀 快速开始

### 方式一：直接使用（推荐）

1. 双击 `index.html` 用浏览器（Edge/Chrome）打开
2. 左侧边栏上传两个 CSV 文件：
   - `data/k12-kgraph.csv` —— 知识图谱三元组
   - `data/k12-bench.csv` —— 题库
3. 开始使用！

### 方式二：从原始数据重新生成

```bash
# 1. 从 HuggingFace 下载完整数据集
python scripts/download_k12_data.py

# 2. 转换为 CSV
python scripts/convert_to_csv.py
```

## 📁 项目结构

```
K12-KGraph-Tool/
├── index.html              # 主程序（单文件，全部代码内嵌）
├── data/
│   ├── k12-kgraph.csv      # 知识图谱三元组（23,278 条 / 9 种关系 / 10,685 节点）
│   └── k12-bench.csv       # 题库（23,638 道题 / 9 个子任务）
├── scripts/
│   ├── download_k12_data.py  # 从 HuggingFace 下载原始数据集
│   └── convert_to_csv.py     # 将原始数据转为 CSV 格式
├── .gitignore
└── README.md
```

## 📊 数据集

数据来源：[K12-Dataset](https://github.com/haolpku/K12-Dataset)（北京大学 梁浩团队，CC BY-NC-SA 4.0）

| 数据 | 规模 |
|------|------|
| 知识图谱 | 10,685 节点 / 23,278 边 / 9 种关系类型 |
| 题库 | 23,640 道多选题（5 类任务 × 9 个子任务） |
| 学科 | 数学 · 物理 · 化学 · 生物 |

9 种关系类型：`is_a` · `prerequisites_for` · `relates_to` · `verifies` · `tests_concept` · `tests_skill` · `appears_in` · `leads_to` · `is_part_of`

## 🛠️ 技术栈

- 原生 JavaScript + HTML + CSS（无框架、无打包）
- [Tailwind CSS](https://tailwindcss.com/)（CDN）—— 界面美化
- [Cytoscape.js](https://js.cytoscape.org/)（CDN）—— 图谱可视化
- [PapaParse](https://www.papaparse.com/)（CDN）—— CSV 解析
- 数据存储：浏览器 localStorage（学习进度、错题记录）

## 📄 许可证

- 数据集：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)（源自 K12-Dataset）
- 工具代码：MIT
