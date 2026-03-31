"""
采购风险看板 - 构建脚本
- 预警快报：轻量解析提取结构化数据（日期、供应商、风险、信号）
- 采购报告：整篇 Markdown 用 markdown 库渲染成 HTML，前端直接 innerHTML 显示
"""

import re
import json
import glob
import os
import markdown
from datetime import datetime, timedelta

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKBuddy_DIR = os.path.dirname(SCRIPT_DIR)
ALERTS_SOURCE_DIR = os.path.join(WORKBuddy_DIR, "supplier_discover", "output")
REPORTS_SOURCE_DIR = os.path.join(WORKBuddy_DIR, "supplier_analysis", "output")
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "index.html")
DIST_PATH = os.path.join(SCRIPT_DIR, "dist", "index.html")


# ==================== 预警快报解析 ====================

def parse_alert_date(filename):
    match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def parse_alert_risk(text):
    if "高风险" in text or "🔴" in text:
        return "high"
    elif "中风险" in text or "🟡" in text:
        return "mid"
    elif "低风险" in text or "🟢" in text:
        return "low"
    elif "无异常" in text or "🚫" in text:
        return "none"
    return "none"


def parse_alert_supplier(heading):
    heading = heading.strip()
    product = None
    product_match = re.search(r"（(.+?)）", heading)
    if product_match:
        product = product_match.group(1)
    name_match = re.search(r"\[([^\]]+)\]", heading)
    if name_match:
        name = name_match.group(1)
    else:
        num_match = re.match(r"\d+[.、)\s]\s*(.+)", heading)
        name = num_match.group(1).strip() if num_match else "未知供应商"
        name = re.sub(r"（.+?）$", "", name).strip()
    risk = parse_alert_risk(heading)
    return name, product, risk


def parse_alert_file(filepath):
    """解析预警快报，提取结构化数据"""
    filename = os.path.basename(filepath)
    date = parse_alert_date(filename)
    if not date:
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    suppliers = []
    signals = []
    current_name = current_product = current_risk = None
    footer = ""
    in_footer = False

    for line in content.split("\n"):
        if line.startswith("## ") and (line.startswith("## [") or re.match(r"^## \d+[.、)\s]", line)):
            if current_name:
                suppliers.append({"name": current_name, "product": current_product, "risk": current_risk, "signals": signals.copy()})
                signals = []
            current_name, current_product, current_risk = parse_alert_supplier(line)
        elif line.strip().startswith("- ") and current_name and not in_footer:
            if "未发现" not in line and "无异常" not in line:
                sig = line.strip()[2:].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                signals.append(sig)
        elif line.startswith("报告生成时间："):
            in_footer = True
            footer = line.strip()
        elif in_footer and line.strip():
            footer += " | " + line.strip()

    if current_name:
        suppliers.append({"name": current_name, "product": current_product, "risk": current_risk, "signals": signals.copy()})

    return {"date": date, "suppliers": suppliers, "footer": footer}


# ==================== 采购报告解析（整篇渲染） ====================

def parse_report_metadata(filepath):
    """从采购报告中只提取元数据（用于列表展示），正文整篇渲染"""
    filename = os.path.basename(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 日期
    date_match = re.search(r"(\d{4})年(\d{2})月(\d{2})日", content[:200])
    report_date = f"{date_match.group(1)}年{date_match.group(2)}月{date_match.group(3)}日" if date_match else ""

    # 供应商名（从文件名）
    cat_match = re.match(r"(.+?)_采购风险分析报告", filename)
    supplier_name = cat_match.group(1) if cat_match else os.path.splitext(filename)[0]

    # 产品
    parts = filename.replace("采购风险分析报告", "").replace(".md", "").split("_")
    product = parts[1] if len(parts) >= 2 else None

    # 风险等级
    overall_risk = "none"
    for line in content.split("\n")[:50]:
        if "风险等级" in line:
            if "🔴" in line or "高" in line and "中" not in line and "低" not in line:
                overall_risk = "high"
            elif "🟡" in line or ("中" in line and "高" not in line):
                overall_risk = "mid"
            elif "🟢" in line or "低" in line:
                overall_risk = "low"
            break

    # 摘要（总体评估那行，取前200字）
    summary = ""
    for line in content.split("\n")[:20]:
        if "总体评估" in line:
            summary = line.replace("总体评估：", "").strip()[:200]
            break

    # 整篇渲染为 HTML
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"])
    html_body = md.convert(content)

    return {
        "supplierName": supplier_name,
        "product": product,
        "reportDate": report_date,
        "overallRisk": overall_risk,
        "summary": summary.replace("<", "&lt;").replace(">", "&gt;"),
        "htmlBody": html_body,
    }


# ==================== 构建 ====================

def build():
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # 1. 解析预警快报（只保留最近一周）
    one_week_ago = datetime.now() - timedelta(days=7)
    alert_files = sorted(
        glob.glob(os.path.join(ALERTS_SOURCE_DIR, "采购风险预警快报_*.md")),
        reverse=True
    )
    alerts = []
    for fp in alert_files:
        report = parse_alert_file(fp)
        if not report:
            continue
        try:
            report_dt = datetime.strptime(report["date"], "%Y-%m-%d")
            if report_dt < one_week_ago:
                print(f"  ⏭️ 跳过过期快报: {os.path.basename(fp)} ({report['date']})")
                continue
        except ValueError:
            pass
        alerts.append(report)
        print(f"  ✅ 预警快报: {os.path.basename(fp)} → {report['date']}, {len(report['suppliers'])}个供应商")

    # 2. 解析采购报告（每类别只保留最新一个，整篇渲染）
    report_files = sorted(
        glob.glob(os.path.join(REPORTS_SOURCE_DIR, "*采购风险分析报告*.md")),
        reverse=True
    )
    reports = []
    seen_categories = set()
    for fp in report_files:
        basename = os.path.basename(fp)
        cat_match = re.match(r"(.+?)_采购风险分析报告", basename)
        category = cat_match.group(1) if cat_match else os.path.splitext(basename)[0]
        if category in seen_categories:
            print(f"  ⏭️ 跳过旧报告: {os.path.basename(fp)} [{category}]")
            continue
        report = parse_report_metadata(fp)
        if report and report["supplierName"]:
            reports.append(report)
            seen_categories.add(category)
            print(f"  ✅ 采购报告: {os.path.basename(fp)} → {report['supplierName']} [{category}]")

    # 3. 注入数据
    alerts_json = json.dumps(alerts, ensure_ascii=False, indent=2)
    reports_json = json.dumps(reports, ensure_ascii=False, indent=2)
    html = template.replace("__ALERTS_DATA__", alerts_json)
    html = html.replace("__REPORTS_DATA__", reports_json)

    # 4. 写入 dist
    os.makedirs(os.path.dirname(DIST_PATH), exist_ok=True)
    with open(DIST_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n🎉 构建完成: {DIST_PATH}")
    print(f"   预警快报: {len(alerts)} 份")
    print(f"   采购报告: {len(reports)} 份")
    return DIST_PATH


if __name__ == "__main__":
    build()
