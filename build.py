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
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # /home/hughxmwen/workspace

# 源目录（预警快报和采购报告）
ALERTS_DIR = os.path.join(PROJECT_DIR, "supplier_discover", "output")
REPORTS_DIR = os.path.join(PROJECT_DIR, "supplier_analysis", "output")

# 输出目录
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
    """解析供应商标题行，提取名称和产品
    
    两种格式：
    1. 新格式（alert-spec）: ### 供应商名（产品：产品名） — 🟡中风险
    2. 旧格式: ## [供应商名称]（产品：产品名）- [🔴 高风险]
    """
    heading = heading.strip()
    
    # 新格式：### 供应商名（产品：产品名） — 🟡中风险
    # 提取产品（可选）
    product = None
    product_match = re.search(r"（产品：(.+?)）", heading)
    if product_match:
        product = product_match.group(1)

    # 提取名称
    name_match = re.search(r"^###\s+([^（\s]+)", heading)
    if not name_match:
        # 尝试旧格式
        name_match = re.search(r"\[([^\]]+)\]", heading)
    
    if name_match:
        name = name_match.group(1)
    else:
        name = "未知供应商"

    risk = parse_risk_level(heading)

    return name, product, risk


def parse_report(filepath):
    """解析单个快报 md 文件
    
    支持两种格式：
    1. 新格式（alert-spec）: 统计表格 + 重要动态/风险预警章节
    2. 旧格式: 直接每个供应商一个章节
    """
    filename = os.path.basename(filepath)
    date = parse_date_from_filename(filename)
    if not date:
        # 尝试从内容中提取日期
        match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", filepath)
        if match:
            date = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        else:
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
    
    # 新格式：先从统计表格提取供应商
    for line in lines:
        # 匹配统计表格中的供应商: 
        # | 🟡 中风险 | 2家（村田、台积电）|
        # | 无异常 | 1家（村田） |
        # | 🚫 无异常 | 1家 |
        
        # 先尝试 emoji + 文字
        risk_match = re.search(r"([🟡🟢🔴🚫])\s*([中高低无异常]+)", line)
        if risk_match:
            risk_emoji = risk_match.group(1)
            risk_text = risk_match.group(2)
            risk = parse_risk_level(risk_emoji + risk_text)
        else:
            # 尝试纯文字（无emoji）
            risk_match = re.search(r"([^|]+)\|\s*(\d+)家", line)
            if risk_match:
                risk_text = risk_match.group(1).strip()
                risk = parse_risk_level(risk_text)
                risk_emoji = None
            else:
                continue
        
        # 提取括号内的供应商列表
        suppliers_in_parens = re.search(r"（([^）]+)）", line)
        if suppliers_in_parens:
            supplier_list = suppliers_in_parens.group(1).split("、")
            for supplier_name in supplier_list:
                suppliers.append({
                    "name": supplier_name.strip(),
                    "product": None,
                    "risk": risk,
                    "signals": []
                })
    
    # 然后从章节内容提取动态和风险信号
    in_section = None  # "重要动态" or "风险预警"
    
    for line in lines:
        # 检测章节开始
        if line.startswith("## 重要动态"):
            in_section = "重要动态"
            continue
        elif line.startswith("## 风险预警"):
            in_section = "风险预警"
            continue
        elif line.startswith("# ") or line.startswith("## 统计"):
            in_section = None
            continue
        
        # 检测供应商标题行
        if line.startswith("### "):
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
            in_section = None  # 标题行不算在章节里

        # 检测风险信号（以 - 开头的列表项）
        elif line.strip().startswith("- ") and current_name:
            # 跳过"该供应商今日未发现"这种
            if "未发现" not in line and "无异常" not in line:
                signal_text = line.strip()[2:]  # 去掉 "- "
                # 转义 HTML 特殊字符
                signal_text = signal_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                signals.append(signal_text)

        # 检测页脚
        elif line.startswith("报告生成时间："):
            footer = line.strip()
        elif line.startswith("生成时间："):
            footer = line.strip()

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

    # 扫描预警快报目录
    alert_files = sorted(
        glob.glob(os.path.join(ALERTS_DIR, "采购风险预警快报_*.md")),
        reverse=True  # 最新的在前
    )

    # 扫描采购报告目录
    report_files = sorted(
        glob.glob(os.path.join(REPORTS_DIR, "*采购风险分析报告*.md")),
        reverse=True
    )

    if not alert_files and not report_files:
        print("⚠️ 未找到任何文件，生成空看板")

    reports = []

    # 解析预警快报
    for filepath in alert_files:
        report = parse_report(filepath)
        if report:
            reports.append(report)
            print(f"  ✅ 解析预警: {os.path.basename(filepath)} → {report['date']}, {len(report['suppliers'])}个供应商")

    # 解析采购报告（暂用相同解析逻辑，后续可根据需要扩展）
    for filepath in report_files:
        report = parse_report(filepath)
        if report:
            reports.append(report)
            print(f"  ✅ 解析报告: {os.path.basename(filepath)} → {report['date']}, {len(report['suppliers'])}个供应商")

    # 注入数据到模板
    reports_json = json.dumps(reports, ensure_ascii=False, indent=2)
    html = template.replace("__REPORTS_DATA__", reports_json)

    # 写入 dist
    os.makedirs(os.path.dirname(DIST_PATH), exist_ok=True)
    with open(DIST_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n🎉 构建完成: {DIST_PATH}")
    print(f"   共 {len(reports)} 份文件（预警快报 + 采购报告）")

    return DIST_PATH


if __name__ == "__main__":
    build()
