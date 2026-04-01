"""
一次性迁移脚本：将旧的 alerts_summary.json / reports_data.json 拆分为单独文件
运行一次后即可删除
"""

import json
import os
import markdown

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
ALERTS_DIR = os.path.join(DIST_DIR, "alerts")
REPORTS_DIR = os.path.join(DIST_DIR, "reports")

MD = markdown.Markdown(extensions=["tables", "fenced_code", "toc"])


def migrate_alerts():
    fpath = os.path.join(OUTPUT_DIR, "alerts_summary.json")
    if not os.path.exists(fpath):
        print("  alerts_summary.json not found, skip")
        return

    with open(fpath, "r", encoding="utf-8") as f:
        items = json.load(f)

    os.makedirs(ALERTS_DIR, exist_ok=True)
    for item in items:
        date = item.get("date", "unknown")
        # 写 JSON 元数据（不含 fileContent）
        meta = {
            "date": item.get("date", ""),
            "dateLabel": item.get("dateLabel", ""),
            "summary": item.get("summary", {"high": 0, "mid": 0, "low": 0, "none": 0}),
            "file": f"alerts/{date}.html"
        }
        with open(os.path.join(ALERTS_DIR, f"{date}.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 渲染 Markdown -> HTML
        MD.reset()
        html_body = MD.convert(item.get("fileContent", ""))
        with open(os.path.join(ALERTS_DIR, f"{date}.html"), "w", encoding="utf-8") as f:
            f.write(html_body)

        print(f"  [OK] alert {date}")


def migrate_reports():
    fpath = os.path.join(OUTPUT_DIR, "reports_data.json")
    if not os.path.exists(fpath):
        print("  reports_data.json not found, skip")
        return

    with open(fpath, "r", encoding="utf-8") as f:
        items = json.load(f)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    for item in items:
        name = item.get("supplierName", "unknown")
        product = item.get("product", "")
        slug = f"{name}-{product}" if product else name

        # 写 JSON 元数据（不含 fileContent）
        meta = {
            "supplierName": item.get("supplierName", ""),
            "product": item.get("product", ""),
            "reportDate": item.get("reportDate", ""),
            "overallRisk": item.get("overallRisk", "none"),
            "summary": item.get("summary", ""),
            "file": f"reports/{slug}.html"
        }
        with open(os.path.join(REPORTS_DIR, f"{slug}.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 渲染 Markdown -> HTML
        MD.reset()
        html_body = MD.convert(item.get("fileContent", ""))
        with open(os.path.join(REPORTS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(html_body)

        print(f"  [OK] report {slug}")


if __name__ == "__main__":
    print("Migrating alerts...")
    migrate_alerts()
    print("Migrating reports...")
    migrate_reports()
    print("Done!")
