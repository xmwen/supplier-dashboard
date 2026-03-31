"""
采购发现团 - 快报看板构建脚本
读取 output/ 目录下的快报 md 文件，解析并生成 index.html
"""

import re
import json
import glob
import os
from datetime import datetime

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "index.html")
DIST_PATH = os.path.join(SCRIPT_DIR, "dist", "index.html")


def parse_date_from_filename(filename):
    """从文件名中提取日期：采购风险预警快报_20260330.md → 2026-03-30"""
    match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def parse_risk_level(text):
    """从标题行提取风险等级"""
    if "高风险" in text or "🔴" in text:
        return "high"
    elif "中风险" in text or "🟡" in text:
        return "mid"
    elif "低风险" in text or "🟢" in text:
        return "low"
    elif "无异常" in text or "🚫" in text:
        return "none"
    return "none"


def parse_supplier_name_and_product(heading):
    """解析供应商标题行，提取名称和产品"""
    # 格式: ## [供应商名称]（产品：产品名）- [🔴 高风险]
    # 或:   ## [供应商名称] - [🚫 无异常]
    heading = heading.strip()

    # 提取产品（可选）
    product = None
    product_match = re.search(r"（产品：(.+?)）", heading)
    if product_match:
        product = product_match.group(1)

    # 提取名称
    name_match = re.search(r"\[([^\]]+)\]", heading)
    if name_match:
        name = name_match.group(1)
    else:
        name = "未知供应商"

    risk = parse_risk_level(heading)

    return name, product, risk


def parse_report(filepath):
    """解析单个快报 md 文件"""
    filename = os.path.basename(filepath)
    date = parse_date_from_filename(filename)
    if not date:
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    suppliers = []
    signals = []
    current_name = None
    current_product = None
    current_risk = None
    footer = ""

    lines = content.split("\n")
    in_footer = False

    for line in lines:
        # 检测供应商标题行
        if line.startswith("## ["):
            # 保存上一个供应商
            if current_name:
                suppliers.append({
                    "name": current_name,
                    "product": current_product,
                    "risk": current_risk,
                    "signals": signals.copy()
                })
                signals = []

            current_name, current_product, current_risk = parse_supplier_name_and_product(line)

        # 检测风险信号（以 - 开头的列表项）
        elif line.strip().startswith("- ") and current_name and not in_footer:
            # 跳过"该供应商今日未发现"这种
            if "未发现" not in line and "无异常" not in line:
                signal_text = line.strip()[2:]  # 去掉 "- "
                # 转义 HTML 特殊字符
                signal_text = signal_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                signals.append(signal_text)

        # 检测页脚
        elif line.startswith("报告生成时间："):
            in_footer = True
            footer = line.strip()
        elif in_footer and line.strip():
            footer += " | " + line.strip()

    # 保存最后一个供应商
    if current_name:
        suppliers.append({
            "name": current_name,
            "product": current_product,
            "risk": current_risk,
            "signals": signals.copy()
        })

    return {
        "date": date,
        "suppliers": suppliers,
        "footer": footer
    }


def build():
    """构建看板 HTML"""
    # 读取模板
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # 扫描 output 目录
    md_files = sorted(
        glob.glob(os.path.join(OUTPUT_DIR, "采购风险预警快报_*.md")),
        reverse=True  # 最新的在前
    )

    if not md_files:
        print("⚠️ 未找到快报文件，生成空看板")

    reports = []
    for filepath in md_files:
        report = parse_report(filepath)
        if report:
            reports.append(report)
            print(f"  ✅ 解析: {os.path.basename(filepath)} → {report['date']}, {len(report['suppliers'])}个供应商")

    # 注入数据到模板
    reports_json = json.dumps(reports, ensure_ascii=False, indent=2)
    html = template.replace("__REPORTS_DATA__", reports_json)

    # 写入 dist
    os.makedirs(os.path.dirname(DIST_PATH), exist_ok=True)
    with open(DIST_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n🎉 构建完成: {DIST_PATH}")
    print(f"   共 {len(reports)} 份快报")

    return DIST_PATH


if __name__ == "__main__":
    build()
