"""
采购风险看板 - 构建脚本（整篇渲染版）
- 预警快报和采购报告均整篇 Markdown → HTML 渲染，零解析
- 读取 output/alerts_summary.json 和 output/reports_data.json（由 AI 整理）
- 用 markdown 库将 fileContent 渲染成 htmlBody，注入模板
"""

import json
import os
import markdown

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "index.html")
DIST_PATH = os.path.join(SCRIPT_DIR, "dist", "index.html")
ALERTS_JSON = os.path.join(SCRIPT_DIR, "output", "alerts_summary.json")
REPORTS_JSON = os.path.join(SCRIPT_DIR, "output", "reports_data.json")

MD = markdown.Markdown(extensions=["tables", "fenced_code", "toc"])


def build():
    # 读取模板
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # 读取预警快报 JSON
    alerts_raw = []
    if os.path.exists(ALERTS_JSON):
        with open(ALERTS_JSON, "r", encoding="utf-8") as f:
            alerts_raw = json.load(f)
        print(f"  ✅ 预警快报 JSON: {ALERTS_JSON} ({len(alerts_raw)} 份)")
    else:
        print(f"  ⚠️ 预警快报 JSON 不存在: {ALERTS_JSON}")

    # 读取采购报告 JSON
    reports_raw = []
    if os.path.exists(REPORTS_JSON):
        with open(REPORTS_JSON, "r", encoding="utf-8") as f:
            reports_raw = json.load(f)
        print(f"  ✅ 采购报告 JSON: {REPORTS_JSON} ({len(reports_raw)} 份)")
    else:
        print(f"  ⚠️ 采购报告 JSON 不存在: {REPORTS_JSON}")

    # 整篇渲染预警快报
    alerts = []
    for item in alerts_raw:
        MD.reset()
        html_body = MD.convert(item.get("fileContent", ""))
        alerts.append({
            "date": item.get("date", ""),
            "dateLabel": item.get("dateLabel", ""),
            "htmlBody": html_body,
            "summary": item.get("summary", {"high": 0, "mid": 0, "low": 0, "none": 0}),
        })
        print(f"    📄 渲染快报: {item.get('date', '?')}")

    # 整篇渲染采购报告
    reports = []
    for item in reports_raw:
        MD.reset()
        html_body = MD.convert(item.get("fileContent", ""))
        reports.append({
            "supplierName": item.get("supplierName", ""),
            "product": item.get("product", ""),
            "reportDate": item.get("reportDate", ""),
            "overallRisk": item.get("overallRisk", "none"),
            "summary": item.get("summary", ""),
            "htmlBody": html_body,
        })
        print(f"    📄 渲染报告: {item.get('supplierName', '?')}")

    # 注入数据
    alerts_json = json.dumps(alerts, ensure_ascii=False, indent=2)
    reports_json = json.dumps(reports, ensure_ascii=False, indent=2)
    html = template.replace("__ALERTS_DATA__", alerts_json)
    html = html.replace("__REPORTS_DATA__", reports_json)

    # 写入 dist
    os.makedirs(os.path.dirname(DIST_PATH), exist_ok=True)
    with open(DIST_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n🎉 构建完成: {DIST_PATH}")
    print(f"   预警快报: {len(alerts)} 份")
    print(f"   采购报告: {len(reports)} 份")
    return DIST_PATH


if __name__ == "__main__":
    build()
