"""
采购风险看板 - 构建脚本

完整流程：
1. 数据采集：扫描源 Markdown 文件，增量转换为 HTML + JSON 元数据
2. 构建索引：汇总所有元数据生成 dist/index.json
3. 复制模板：将 index.html 模板复制到 dist/

使用方法：
  set PYTHONIOENCODING=utf-8
  python build.py
"""

import json
import os
import re
import shutil
import glob
from datetime import datetime
from collections import defaultdict

import markdown

# ── 路径配置 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "index.html")
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
ALERTS_DIR = os.path.join(DIST_DIR, "alerts")
REPORTS_DIR = os.path.join(DIST_DIR, "reports")

ALERT_SOURCE_DIR = "/home/hughxmwen/workspace/supplier_discover/output"
REPORT_SOURCE_DIR = "/home/hughxmwen/workspace/supplier_analysis/output"


# ── 工具函数 ──────────────────────────────────────────────
def md_to_html_fragment(md_text):
    """将 Markdown 转为 HTML 内容片段（不包裹 html/head/body）"""
    return markdown.markdown(md_text, extensions=["tables"])


def get_mtime(path):
    """获取文件修改时间"""
    return os.path.getmtime(path)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 第一步：数据采集 ──────────────────────────────────────
def collect_alerts():
    """扫描预警快报源目录，增量处理新增/变更的快报"""
    print("  [1/4] 采集预警快报...")

    os.makedirs(ALERTS_DIR, exist_ok=True)

    source_files = glob.glob(os.path.join(ALERT_SOURCE_DIR, "采购风险预警快报_*.md"))
    if not source_files:
        print("    未找到预警快报源文件")
        return

    processed = 0
    for src in sorted(source_files):
        # 从文件名提取日期: 采购风险预警快报_20260401.md → 2026-04-01
        fname = os.path.basename(src)
        m = re.search(r"_(\d{8})\.md$", fname)
        if not m:
            continue

        date_str = datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%d")
        dest_html = os.path.join(ALERTS_DIR, f"{date_str}.html")
        dest_json = os.path.join(ALERTS_DIR, f"{date_str}.json")

        # 增量判断：源文件比目标文件新才处理
        if os.path.exists(dest_html) and os.path.exists(dest_json):
            if get_mtime(src) <= max(get_mtime(dest_html), get_mtime(dest_json)):
                print(f"    跳过: {date_str}（未变更）")
                continue

        # 读取 Markdown → 转换为 HTML 片段
        with open(src, "r", encoding="utf-8") as f:
            md_text = f.read()
        html_content = md_to_html_fragment(md_text)

        # 写入 HTML（纯内容片段，不含 html/head/body）
        with open(dest_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 写入 JSON 元数据
        # dateLabel 格式：2026年4月1日（无前导零）
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_label = f"{dt.year}年{dt.month}月{dt.day}日"
        write_json(dest_json, {
            "date": date_str,
            "dateLabel": date_label,
            "file": f"alerts/{date_str}.html",
        })

        processed += 1
        print(f"    处理: {date_str}")

    print(f"    预警快报: 扫描 {len(source_files)} 个源文件，新增/更新 {processed} 个")


def collect_reports():
    """扫描采购报告源目录，按供应商分组取最新，增量处理新增/变更的报告"""
    print("  [2/4] 采集采购报告...")

    os.makedirs(REPORTS_DIR, exist_ok=True)

    source_files = glob.glob(os.path.join(REPORT_SOURCE_DIR, "*采购风险分析报告*.md"))
    if not source_files:
        print("    未找到采购报告源文件")
        return

    # 按供应商-产品分组，每组取最新日期
    groups = defaultdict(list)
    for src in source_files:
        fname = os.path.basename(src)
        # 文件名格式: 供应商_产品_采购风险分析报告_YYYYMMDD_HHMMSS.md
        m = re.match(r"(.+?)_(.+?)_采购风险分析报告_(\d{8})(?:_\d+)?\.md$", fname)
        if not m:
            continue
        supplier, product, date_raw = m.group(1), m.group(2), m.group(3)
        file_id = f"{supplier}-{product}"
        dt = datetime.strptime(date_raw, "%Y%m%d")
        groups[file_id].append({
            "src": src,
            "supplier": supplier,
            "product": product,
            "date": dt,
            "date_raw": date_raw,
        })

    # 每组取最新
    latest = {}
    for file_id, items in groups.items():
        items.sort(key=lambda x: x["date"], reverse=True)
        latest[file_id] = items[0]

    processed = 0
    for file_id, info in sorted(latest.items()):
        dest_html = os.path.join(REPORTS_DIR, f"{file_id}.html")
        dest_json = os.path.join(REPORTS_DIR, f"{file_id}.json")

        # 增量判断
        if os.path.exists(dest_html) and os.path.exists(dest_json):
            if get_mtime(info["src"]) <= max(get_mtime(dest_html), get_mtime(dest_json)):
                print(f"    跳过: {file_id}（未变更）")
                continue

        # 读取 Markdown → 转换为 HTML 片段
        with open(info["src"], "r", encoding="utf-8") as f:
            md_text = f.read()
        html_content = md_to_html_fragment(md_text)

        # 写入 HTML
        with open(dest_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 写入 JSON 元数据
        # reportDate 格式：2026年03月31日（有前导零）
        report_date = info["date"].strftime("%Y年%m月%d日")
        write_json(dest_json, {
            "supplierName": info["supplier"],
            "product": info["product"],
            "reportDate": report_date,
            "file": f"reports/{file_id}.html",
        })

        processed += 1
        print(f"    处理: {file_id} ({report_date})")

    print(f"    采购报告: 扫描 {len(source_files)} 个源文件，"
          f"保留 {len(latest)} 个最新报告，新增/更新 {processed} 个")


# ── 第二步：构建索引 ──────────────────────────────────────
def build_index():
    """扫描 dist/ 下的 JSON 元数据，生成汇总索引"""
    print("  [3/4] 构建索引...")

    alerts = []
    if os.path.isdir(ALERTS_DIR):
        for fname in sorted(os.listdir(ALERTS_DIR)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(ALERTS_DIR, fname), "r", encoding="utf-8") as f:
                alerts.append(json.load(f))

    reports = []
    if os.path.isdir(REPORTS_DIR):
        for fname in sorted(os.listdir(REPORTS_DIR)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(REPORTS_DIR, fname), "r", encoding="utf-8") as f:
                reports.append(json.load(f))

    # 获取当前时间
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    index_data = {
        "alerts": alerts,
        "reports": reports,
        "updatedAt": now,
    }

    index_path = os.path.join(DIST_DIR, "index.json")
    write_json(index_path, index_data)

    # 复制 index.html 模板到 dist
    shutil.copy2(TEMPLATE_PATH, os.path.join(DIST_DIR, "index.html"))

    print(f"    索引: {len(alerts)} 份快报 + {len(reports)} 份报告")
    print(f"    更新时间: {now}")


# ── 主入口 ────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("采购风险看板 - 构建")
    print("=" * 50)

    collect_alerts()
    collect_reports()
    build_index()

    print("=" * 50)
    print("构建完成")


if __name__ == "__main__":
    main()
