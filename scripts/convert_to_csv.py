# -*- coding: utf-8 -*-
"""
K12-KGraph 数据 → CSV 转换脚本（纯标准库，无需 pip）
======================================================
功能：
  将 download_k12_data.py 下载的原始 JSON/JSONL 文件
  转换为 index.html 工具可直接加载的 CSV 格式

输入：D:\Code\data\ 下的原始文件
输出：D:\Code\data\k12-kgraph.csv（知识图谱三元组）
      D:\Code\data\k12-bench.csv（题库）

运行：python convert_to_csv.py
"""

import os
import sys
import json
import csv
import glob

# 强制 UTF-8 输出，解决 Windows GBK 控制台乱码问题
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def convert_graph_to_csv():
    """将全局知识图谱（nodes.json + edges.json）转为 CSV 三元组"""
    edges_path = os.path.join(DATA_DIR, "global_KG_edges.json")
    nodes_path = os.path.join(DATA_DIR, "global_KG_nodes.json")
    output_path = os.path.join(DATA_DIR, "k12-kgraph.csv")

    print("=" * 50)
    print("转换知识图谱 → CSV 三元组")
    print("=" * 50)

    # 加载节点，建立 id → name 映射
    print(f"\n加载节点文件：{nodes_path}")
    with open(nodes_path, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    id_to_name = {}
    for node in nodes:
        nid = node.get("id", "")
        name = node.get("name", "")
        if nid and name:
            id_to_name[nid] = name
    print(f"  ✓ 加载 {len(nodes)} 个节点，映射 {len(id_to_name)} 个名称")

    # 加载边
    print(f"\n加载边文件：{edges_path}")
    with open(edges_path, "r", encoding="utf-8") as f:
        edges = json.load(f)
    print(f"  ✓ 加载 {len(edges)} 条边")

    # 统计关系类型
    relation_types = set()

    # 写入 CSV（head=头节点名称, relation=关系类型, tail=尾节点名称）
    print(f"\n写入 CSV：{output_path}")
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["head", "relation", "tail"])

        mapped = 0
        unmapped = 0
        for edge in edges:
            source_id = edge.get("source", "")
            target_id = edge.get("target", "")
            relation = edge.get("type", "")

            # 优先用名称，其次用 id
            head = id_to_name.get(source_id, source_id)
            tail = id_to_name.get(target_id, target_id)
            relation_types.add(relation)

            if head and tail and relation:
                writer.writerow([head, relation, tail])
                if source_id in id_to_name and target_id in id_to_name:
                    mapped += 1
                else:
                    unmapped += 1

    file_size = os.path.getsize(output_path) / 1024
    print(f"  ✓ 写入 {mapped + unmapped} 条三元组")
    print(f"    - 成功映射名称：{mapped} 条")
    print(f"    - 保留 ID（未映射）：{unmapped} 条")
    print(f"    - 关系类型数：{len(relation_types)}")
    print(f"    - 关系类型：{sorted(relation_types)}")
    print(f"  文件大小：{file_size:.0f} KB")

    return output_path


def convert_bench_to_csv():
    """将所有 bench 文件合并转为一个 CSV"""
    output_path = os.path.join(DATA_DIR, "k12-bench.csv")
    bench_files = sorted(glob.glob(os.path.join(DATA_DIR, "bench_*.jsonl")))

    print(f"\n{'='*50}")
    print("转换题库 → CSV")
    print(f"{'='*50}")

    if not bench_files:
        print("  ⚠ 未找到 bench_*.jsonl 文件")
        return None

    print(f"\n找到 {len(bench_files)} 个题库文件：")
    for f in bench_files:
        print(f"  - {os.path.basename(f)}")

    with open(output_path, "w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["question", "optionA", "optionB", "optionC", "optionD", "answer", "knowledge_point"])

        total = 0
        success = 0
        skip = 0

        for bench_file in bench_files:
            # 从文件名提取任务类型（作为 knowledge_point 列的补充标签）
            task_label = os.path.basename(bench_file).replace("bench_", "").replace(".jsonl", "")

            with open(bench_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    total += 1
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        skip += 1
                        continue

                    question = item.get("question", item.get("q", ""))
                    options = item.get("options", item.get("option", {}))

                    # 解析选项（兼容 dict / list 两种格式）
                    if isinstance(options, dict):
                        optA = options.get("A", options.get("optionA", ""))
                        optB = options.get("B", options.get("optionB", ""))
                        optC = options.get("C", options.get("optionC", ""))
                        optD = options.get("D", options.get("optionD", ""))
                    elif isinstance(options, list) and len(options) >= 4:
                        optA, optB, optC, optD = options[0], options[1], options[2], options[3]
                    else:
                        skip += 1
                        continue

                    # 解析答案（兼容 "B" / ["B"] / "B,C"）
                    answer = item.get("answer", item.get("correct", ""))
                    if isinstance(answer, list):
                        answer = ",".join(answer)
                    answer = str(answer).upper()

                    # 关联知识点
                    kp = item.get("knowledge_point", item.get("kp", item.get("node", "")))
                    if isinstance(kp, list):
                        kp = ";".join(str(x) for x in kp)
                    kp = f"{task_label}|{kp}" if kp else task_label

                    if question and optA and optB and optC and answer:
                        writer.writerow([question, optA, optB, optC, optD, answer, kp])
                        success += 1
                    else:
                        skip += 1

    file_size = os.path.getsize(output_path) / 1024
    unit = "MB" if file_size >= 1024 else "KB"
    file_size = file_size / 1024 if file_size >= 1024 else file_size
    print(f"\n  ✓ 合并完成")
    print(f"    - 总记录数：{total}")
    print(f"    - 成功转换：{success}")
    print(f"    - 跳过格式不符：{skip}")
    print(f"  文件大小：{file_size:.1f} {unit}")

    return output_path


def main():
    print("=" * 60)
    print("  K12-KGraph → CSV 转换（纯标准库）")
    print("=" * 60)
    print(f"\n数据目录：{DATA_DIR}")

    # 检查原始文件是否存在
    if not os.path.exists(os.path.join(DATA_DIR, "global_KG_edges.json")):
        print("\n❌ 未找到原始数据文件，请先运行 download_k12_data.py 下载数据")
        return

    # 转换
    graph_csv = convert_graph_to_csv()
    bench_csv = convert_bench_to_csv()

    # 总结
    print(f"\n{'='*60}")
    print("✅ CSV 转换完成！")
    print(f"{'='*60}")
    print(f"\n生成文件：")
    for f in [graph_csv, bench_csv]:
        if f and os.path.exists(f):
            size = os.path.getsize(f) / 1024
            unit = "MB" if size >= 1024 else "KB"
            size = size / 1024 if size >= 1024 else size
            print(f"  📄 {os.path.basename(f):<30s} {size:.1f} {unit}")

    print(f"\n📌 下一步：")
    print(f"   1. 打开浏览器访问：{DATA_DIR.replace('data','index.html')}")
    print(f"   2. 左侧边栏上传：")
    print(f"      知识图谱 CSV → {graph_csv}")
    print(f"      题库 CSV     → {bench_csv}")
    print(f"   3. 开始使用！")


if __name__ == "__main__":
    main()
