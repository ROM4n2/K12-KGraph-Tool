# -*- coding: utf-8 -*-
"""
K12-KGraph 完整数据集下载 + 格式转换脚本
==========================================
功能：
  1. 从 HuggingFace 下载完整 K12-KGraph 数据集（图谱 + 题库 + 训练QA）
  2. 自动检测代理、尝试国内镜像，失败时回退到官方源
  3. 保存原始 JSON/JSONL 文件到 D:\Code\data\
  4. 自动转换为 CSV 格式，可直接被 index.html 工具加载

使用方法：
  在终端执行：python download_k12_data.py

代理设置（如果挂了VPN/代理）：
  在脚本最下方的"配置区"填入代理地址，例如：
      HTTP_PROXY  = "http://127.0.0.1:7890"
      HTTPS_PROXY = "http://127.0.0.1:7890"
"""

import os
import sys
import json
import time

# ============================================================
# 配置区（按需修改）
# ============================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HF_DATASET = "lhpku20010120/K12-KGraph"

# 代理设置：如果挂了代理/VPN 请取消注释并填上端口（常见端口：7890/7897/10809/1080）
# HTTP_PROXY  = "http://127.0.0.1:7890"
# HTTPS_PROXY = "http://127.0.0.1:7890"
HTTP_PROXY = None
HTTPS_PROXY = None

# ============================================================
# 工具函数：代理检测
# ============================================================
def detect_proxy():
    """自动检测系统代理设置，返回代理字典或 None"""
    # 先检查已有环境变量
    for key in ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"]:
        val = os.environ.get(key)
        if val:
            print(f"  ✓ 检测到系统代理：{key}={val}")
            return {"http": val, "https": val}

    # 检查脚本配置区的手動代理
    if HTTP_PROXY or HTTPS_PROXY:
        proxy = {"http": HTTP_PROXY or "", "https": HTTPS_PROXY or ""}
        print(f"  ✓ 使用手动配置代理：{proxy}")
        return proxy

    # 尝试常见代理端口（Clash/V2Ray/Nginx 等）
    common_ports = [7890, 7897, 7891, 10809, 1080, 10808, 8080, 20170, 20171]
    import socket
    for port in common_ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            result = s.connect_ex(("127.0.0.1", port))
            s.close()
            if result == 0:
                proxy_url = f"http://127.0.0.1:{port}"
                print(f"  ✓ 探测到本地代理端口：{port}")
                return {"http": proxy_url, "https": proxy_url}
        except:
            continue

    print("  ℹ 未检测到代理（如需请在配置区手工填写端口）")
    return None


# ============================================================
# 第一步：下载数据集
# ============================================================
def download_via_datasets_lib(proxy):
    """尝试用 datasets 库下载（启用重试）"""
    from datasets import load_download_config
    from datasets.utils.file_utils import http_user_agent

    # 设置代理到环境变量
    if proxy:
        os.environ["HTTP_PROXY"] = proxy.get("http", "")
        os.environ["HTTPS_PROXY"] = proxy.get("https", "")

    # 下载源（镜像优先）
    endpoints = [
        ("国内镜像 hf-mirror", "https://hf-mirror.com"),
        ("官方源 huggingface", "https://huggingface.co"),
    ]

    last_error = None
    for endpoint_name, endpoint_url in endpoints:
        os.environ["HF_ENDPOINT"] = endpoint_url
        print(f"\n  使用 {endpoint_name}：{endpoint_url}")

        try:
            from datasets import load_dataset
            print("  [1/3] 下载知识图谱（train split）...")
            kg = load_dataset(HF_DATASET, split="train", download_config={
                "max_retries": 3,
                "resume_download": True,
            })
            print(f"    ✓ 图谱：{len(kg)} 条")

            print("  [2/3] 下载题库（bench split）...")
            bench = load_dataset(HF_DATASET, name="bench", split="test")
            print(f"    ✓ 题库：{len(bench)} 道")

            print("  [3/3] 下载训练QA（train split）...")
            train = load_dataset(HF_DATASET, name="train", split="train")
            print(f"    ✓ 训练QA：{len(train)} 条")

            return kg, bench, train

        except Exception as e:
            last_error = e
            print(f"    ✗ 失败：{str(e)[:120]}")
            continue

    raise last_error


def download_via_hf_hub(proxy):
    """备选：用 huggingface_hub 库下载原始文件"""
    print("\n  切换到 huggingface_hub.snapshot_download 下载原始文件...")
    if proxy:
        os.environ["HTTP_PROXY"] = proxy.get("http", "")
        os.environ["HTTPS_PROXY"] = proxy.get("https", "")

    from huggingface_hub import snapshot_download

    # 只用国内镜像
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    local_dir = os.path.join(DATA_DIR, "_hf_cache")
    print(f"  下载到临时目录：{local_dir}")

    path = snapshot_download(
        repo_id=HF_DATASET,
        repo_type="dataset",
        local_dir=local_dir,
        max_workers=2,
        resume_download=True,
    )
    print(f"  ✓ 下载完成：{path}")
    return path


def load_from_local_cache(local_dir):
    """从 huggingface_hub 本地缓存中解析出数据集"""
    print("\n  从本地缓存解析数据...")
    import glob

    # huggingface 缓存结构下找数据文件
    files = []
    for ext in ["*.json", "*.jsonl", "*.parquet", "*.arrow"]:
        files.extend(glob.glob(os.path.join(local_dir, "**", ext), recursive=True))

    if not files:
        raise FileNotFoundError(f"本地缓存目录中未找到数据文件：{local_dir}")

    print(f"  找到 {len(files)} 个数据文件")
    for f in files[:10]:
        print(f"    - {os.path.basename(f)} ({os.path.getsize(f)/1024:.0f} KB)")

    # 尝试用 datasets 从本地文件加载
    from datasets import load_dataset
    kg = load_dataset("json", data_files=os.path.join(local_dir, "**/*train*.json*"), split="train") \
        if any("train" in f for f in files) else None
    # 简化：直接把找到的 jsonl 读出来
    return files


def download_datasets():
    """主下载函数：依次尝试多种方式"""
    print(f"\n{'='*50}")
    print("检测网络环境...")
    print(f"{'='*50}")
    proxy = detect_proxy()

    # 方式一：datasets 库
    print(f"\n{'='*50}")
    print("方式一：尝试 datasets 库下载")
    print(f"{'='*50}")
    try:
        return download_via_datasets_lib(proxy)
    except Exception as e:
        print(f"\n  datasets 库下载失败：{str(e)[:100]}")

    # 方式二：huggingface_hub 原始文件
    print(f"\n{'='*50}")
    print("方式二：尝试 huggingface_hub 下载原始文件")
    print(f"{'='*50}")
    try:
        local_dir = download_via_hf_hub(proxy)
        # 加载本地文件
        files = load_from_local_cache(local_dir)
        # 直接读取文件做转换
        return load_files_to_memory(local_dir)
    except Exception as e:
        print(f"\n  huggingface_hub 下载也失败：{str(e)[:100]}")

    # 全部失败：给出手动指南
    print_manual_guide()
    sys.exit(1)


def load_files_to_memory(local_dir):
    """从本地缓存目录读取数据到内存，返回 (kg, bench, train) 兼容格式"""
    import glob

    # 把文件当纯 JSON/JSONL 读入，封装成类似 datasets 的 list[dict]
    result = {}

    for pattern, key in [("*train*", "kg"), ("*bench*", "bench"), ("*test*", "bench"), ("*sft*", "train")]:
        files = glob.glob(os.path.join(local_dir, "**", pattern + ".json"), recursive=True) + \
                glob.glob(os.path.join(local_dir, "**", pattern + ".jsonl"), recursive=True)
        if files:
            rows = []
            for f in files:
                with open(f, "r", encoding="utf-8") as fh:
                    if f.endswith(".jsonl"):
                        rows.extend(json.loads(line) for line in fh if line.strip())
                    else:
                        data = json.load(fh)
                        rows.extend(data if isinstance(data, list) else [data])
            result[key] = rows
            print(f"  ✓ {key}：从 {len(files)} 个文件读入 {len(rows)} 条")

    if "kg" not in result:
        raise FileNotFoundError("未在缓存中找到知识图谱数据文件")

    return result.get("kg"), result.get("bench", []), result.get("train", [])


def print_manual_guide():
    """全部失败时输出手动下载指南"""
    print(f"\n{'='*60}")
    print("❌ 自动下载全部失败")
    print(f"{'='*60}")
    print("""
┌──────────────────────────────────────────────────────────────┐
│  手动下载方案（推荐：挂代理 + 浏览器直连镜像站下载）           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  方法1：挂代理后重跑本脚本                                    │
│    ① 打开你的代理软件（Clash/V2Ray 等），确认已开启          │
│    ② 在脚本"配置区"填写代理端口：                            │
│         HTTP_PROXY  = "http://127.0.0.1:7890"               │
│         HTTPS_PROXY = "http://127.0.0.1:7890"               │
│    ③ 保存后重新运行：python download_k12_data.py             │
│                                                              │
│  方法2：浏览器手动下载 hf-mirror.com                          │
│    ① 访问 https://hf-mirror.com/datasets/lhpku20010120/      │
│       K12-KGraph                                             │
│    ② 进入 Files 标签，下载以下文件到 D:\Code\data\：         │
│       - train.jsonl / train.parquet  （知识图谱）            │
│       - test.jsonl  / test.parquet   （题库）                │
│    ③ 然后运行本脚本的"仅转换"模式（跳过下载）                │
│                                                              │
│  方法3：让我帮你直接用 curl 下载（提供命令行）                │
│    告诉我"帮我curl下载"，我生成一条条命令你复制粘贴即可      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
""")


# ============================================================
# 第二步：保存数据文件
# ============================================================
def save_raw_files(kg, bench, train):
    """将数据保存为统一格式的 JSON/JSONL 文件"""
    os.makedirs(DATA_DIR, exist_ok=True)

    # 统一封装：兼容 datasets.Dataset 对象 和 list[dict]
    def to_list(data):
        if data is None:
            return []
        if isinstance(data, list):
            return data
        try:
            return data.to_list() if hasattr(data, "to_list") else list(data)
        except:
            return list(data)

    kg_list = to_list(kg)
    bench_list = to_list(bench)
    train_list = to_list(train)

    kg_path = os.path.join(DATA_DIR, "k12-kgraph.json")
    bench_path = os.path.join(DATA_DIR, "k12-bench.jsonl")
    train_path = os.path.join(DATA_DIR, "k12-train.jsonl")

    print(f"\n保存知识图谱到：{kg_path}")
    with open(kg_path, "w", encoding="utf-8") as f:
        json.dump(kg_list, f, ensure_ascii=False)
    print(f"  ✓ {len(kg_list)} 条（{os.path.getsize(kg_path)/1024:.0f} KB）")

    print(f"\n保存题库到：{bench_path}")
    with open(bench_path, "w", encoding="utf-8") as f:
        for item in bench_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  ✓ {len(bench_list)} 道（{os.path.getsize(bench_path)/1024:.0f} KB）")

    print(f"\n保存训练QA到：{train_path}")
    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_list:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  ✓ {len(train_list)} 条（{os.path.getsize(train_path)/1024:.0f} KB）")

    return kg_path, bench_path, train_path


# ============================================================
# 第三步：转换为 CSV（适配 index.html 工具）
# ============================================================
def convert_graph_to_csv(kg_path, output_path):
    """知识图谱 JSON → CSV 三元组（head, relation, tail）"""
    print(f"\n转换知识图谱为 CSV 三元组...")

    with open(kg_path, "r", encoding="utf-8") as f:
        kg_data = json.load(f)

    # 兼容多种数据结构
    edges = []
    if isinstance(kg_data, dict) and "edges" in kg_data:
        edges = kg_data["edges"]
    elif isinstance(kg_data, list):
        for record in kg_data:
            if isinstance(record, dict):
                if "edges" in record:
                    e = record["edges"]
                    edges.extend(e if isinstance(e, list) else [e])
                elif "source" in record and "target" in record:
                    edges.append(record)

    if not edges:
        print("  ⚠ 未找到边数据，跳过图谱 CSV")
        print(f"  数据结构预览：{str(kg_data)[:200]}")
        return None

    import csv
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["head", "relation", "tail"])
        for edge in edges:
            head = edge.get("source_name", edge.get("source", edge.get("head", "")))
            relation = edge.get("type", edge.get("relation", edge.get("edge_type", "")))
            tail = edge.get("target_name", edge.get("target", edge.get("tail", "")))
            if head and tail and relation:
                writer.writerow([head, relation, tail])

    row_count = sum(1 for _ in open(output_path, encoding="utf-8")) - 1
    print(f"  ✓ {row_count} 条三元组 → {output_path}")
    print(f"  文件大小：{os.path.getsize(output_path)/1024:.0f} KB")
    return output_path


def convert_bench_to_csv(bench_path, output_path):
    """题库 JSONL → CSV（question, optionA-D, answer, knowledge_point）"""
    print(f"\n转换题库为 CSV...")

    import csv
    with open(bench_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print("  ⚠ 题库文件为空")
        return None

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["question", "optionA", "optionB", "optionC", "optionD", "answer", "knowledge_point"])
        success, skip = 0, 0
        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                skip += 1; continue

            question = item.get("question", item.get("q", ""))
            options = item.get("options", item.get("option", {}))
            if isinstance(options, dict):
                optA = options.get("A", options.get("optionA", ""))
                optB = options.get("B", options.get("optionB", ""))
                optC = options.get("C", options.get("optionC", ""))
                optD = options.get("D", options.get("optionD", ""))
            elif isinstance(options, list) and len(options) >= 4:
                optA, optB, optC, optD = options[0], options[1], options[2], options[3]
            else:
                skip += 1; continue

            answer = item.get("answer", item.get("correct", ""))
            if isinstance(answer, list):
                answer = ",".join(answer)
            kp = item.get("knowledge_point", item.get("kp", item.get("node", "")))
            if isinstance(kp, list): kp = ";".join(kp)

            if question and optA and optB and optC and answer:
                writer.writerow([question, optA, optB, optC, optD, answer, kp])
                success += 1
            else:
                skip += 1

    print(f"  ✓ {success} 道题目 → {output_path}")
    if skip: print(f"  ⚠ 跳过 {skip} 条格式不符")
    print(f"  文件大小：{os.path.getsize(output_path)/1024:.0f} KB")
    return output_path


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("  K12-KGraph 完整数据集下载 + 格式转换")
    print("=" * 60)
    print(f"\n数据保存目录：{DATA_DIR}")

    # 1. 下载
    kg, bench, train = download_datasets()

    # 2. 保存原始文件
    kg_path, bench_path, train_path = save_raw_files(kg, bench, train)

    # 3. 转 CSV
    print(f"\n{'='*50}")
    print("转换为 CSV 格式（适配 index.html 工具）")
    print(f"{'='*50}")
    graph_csv = os.path.join(DATA_DIR, "k12-kgraph.csv")
    bench_csv = os.path.join(DATA_DIR, "k12-bench.csv")
    convert_graph_to_csv(kg_path, graph_csv)
    convert_bench_to_csv(bench_path, bench_csv)

    # 总结
    print(f"\n{'='*60}")
    print("✅ 全部完成！生成文件：")
    print(f"{'='*60}")
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.startswith("_"): continue
        fpath = os.path.join(DATA_DIR, fname)
        size = os.path.getsize(fpath) / 1024
        unit, size = ("MB", size/1024) if size >= 1024 else ("KB", size)
        print(f"  📄 {fname:<30s} {size:.1f} {unit}")

    print(f"\n📌 下一步：")
    print(f"   1. 打开 D:\\Code\\index.html")
    print(f"   2. 左侧边栏上传：")
    print(f"      图谱 CSV → D:\\Code\\data\\k12-kgraph.csv")
    print(f"      题库 CSV → D:\\Code\\data\\k12-bench.csv")


if __name__ == "__main__":
    main()
