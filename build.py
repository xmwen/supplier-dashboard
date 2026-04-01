"""
采购风险看板 - 构建脚本（增量索引版）
- 扫描 dist/alerts/ 和 dist/reports/ 目录，收集所有 .json 元数据文件
- 生成 dist/index.json 汇总索引
- 将 index.html 模板复制到 dist/index.html（前端通过 fetch 加载数据）

增量策略：
- AI 在数据采集阶段已将每份快报/报告拆为独立的 .html + .json
- 本脚本只需汇总索引，不重新渲染任何内容
"""

import json
import os
import shutil

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "index.html")
DIST_DIR = os.path.join(SCRIPT_DIR, "dist")
DIST_INDEX_HTML = os.path.join(DIST_DIR, "index.html")
DIST_INDEX_JSON = os.path.join(DIST_DIR, "index.json")
ALERTS_DIR = os.path.join(DIST_DIR, "alerts")
REPORTS_DIR = os.path.join(DIST_DIR, "reports")


def load_json_files(directory):
    """扫描目录下所有 .json 文件，返回列表"""
    results = []
    if not os.path.isdir(directory):
        return results
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".json"):
            fpath = os.path.join(directory, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append(data)
                print(f"    [OK] {fname}")
            except (json.JSONDecodeError, OSError) as e:
                print(f"    [ERR] {fname}: {e}")
    return results


def build():
    # 确保输出目录存在
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(ALERTS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # 收集预警快报元数据
    print("  扫描预警快报...")
    alerts = load_json_files(ALERTS_DIR)

    # 收集采购报告元数据
    print("  扫描采购报告...")
    reports = load_json_files(REPORTS_DIR)

    # 生成索引文件
    index_data = {
        "alerts": alerts,
        "reports": reports,
        "updatedAt": os.popen("powershell -Command Get-Date -Format 'yyyy-MM-dd HH:mm'").read().strip()
    }

    with open(DIST_INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    # 复制 index.html 模板到 dist
    shutil.copy2(TEMPLATE_PATH, DIST_INDEX_HTML)

    print(f"\n  构建完成!")
    print(f"    预警快报: {len(alerts)} 份")
    print(f"    采购报告: {len(reports)} 份")
    print(f"    索引文件: {DIST_INDEX_JSON}")
    print(f"    看板页面: {DIST_INDEX_HTML}")
    return DIST_INDEX_HTML


if __name__ == "__main__":
    build()
