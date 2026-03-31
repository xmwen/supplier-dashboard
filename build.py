"""
采购风险看板 - 构建脚本
读取 supplier_discover/output/ 下的预警快报 + supplier_analysis/output/ 下的采购报告
解析并生成 index.html
"""

import re
import json
import glob
import os
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
    product_match = re.search(r"（产品：(.+?)）", heading)
    if product_match:
        product = product_match.group(1)
    name_match = re.search(r"\[([^\]]+)\]", heading)
    name = name_match.group(1) if name_match else "未知供应商"
    risk = parse_alert_risk(heading)
    return name, product, risk


def parse_alert_file(filepath):
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
        if line.startswith("## ["):
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


# ==================== 采购报告解析 ====================

def parse_report_risk(text):
    if "🔴" in text or "高风险" in text or "高" == text.strip():
        return "high"
    elif "🟡" in text or "中风险" in text or "中" == text.strip():
        return "mid"
    elif "🟢" in text or "低风险" in text or "低" == text.strip():
        return "low"
    return "none"


def parse_report_date_from_filename(filename):
    match = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if match:
        return f"{match.group(1)}年{match.group(2)}月{match.group(3)}日"
    return ""


def parse_analysis_report(filepath):
    """解析供应商采购风险分析报告"""
    filename = os.path.basename(filepath)
    report_date = parse_report_date_from_filename(filename)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    result = {
        "supplierName": "",
        "product": None,
        "reportDate": report_date,
        "overallRisk": "none",
        "summary": "",
        "dimensions": [],
        "keyRisks": [],
        "sections": [],
        "recommendations": [],
        "sources": "",
        "genTime": "",
    }

    # 提取供应商名称（从第一行标题）
    first_line = lines[0].strip().lstrip("#").strip() if lines else ""
    name_match = re.search(r"^(.+?)（(.+?)）采购风险分析报告", first_line)
    if name_match:
        result["supplierName"] = name_match.group(1).strip()
        result["product"] = name_match.group(2).strip()
    else:
        name_match = re.search(r"^(.+?)采购风险分析报告", first_line)
        if name_match:
            result["supplierName"] = name_match.group(1).strip()

    # 如果文件名中也有供应商名，作为 fallback
    if not result["supplierName"]:
        fname_match = re.match(r"(.+?)_", filename)
        if fname_match:
            result["supplierName"] = fname_match.group(1)

    # 从文件名提取产品（如果有下划线分隔）
    if not result["product"]:
        parts = filename.replace("采购风险分析报告", "").replace(".md", "").split("_")
        if len(parts) >= 2:
            result["product"] = parts[1]

    # 解析报告日期（从内容中）
    for line in lines:
        dm = re.search(r"报告日期：(\d{4})年(\d{2})月(\d{2})日", line)
        if dm:
            result["reportDate"] = f"{dm.group(1)}年{dm.group(2)}月{dm.group(3)}日"
            break

    # 提取生成时间
    for line in lines:
        gm = re.search(r"报告生成时间：(.+)", line)
        if gm:
            result["genTime"] = gm.group(1).strip()
            break

    # 提取综合风险等级
    for line in lines:
        if "综合风险等级" in line or "风险等级" in line:
            if "高" in line and "中" not in line and "低" not in line:
                result["overallRisk"] = "high"
            elif "中" in line:
                result["overallRisk"] = "mid"
            elif "低" in line:
                result["overallRisk"] = "low"
            break

    # 提取总体评估（总体评估：... 段落）
    for i, line in enumerate(lines):
        if line.strip().startswith("总体评估："):
            summary = line.strip().replace("总体评估：", "")
            # 继续读后续行直到遇到空行或分隔线
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip() == "" or lines[j].strip().startswith("━━") or lines[j].strip().startswith("---"):
                    break
                summary += " " + lines[j].strip()
            result["summary"] = summary.replace("<", "&lt;").replace(">", "&gt;")
            break

    # 解析维度表格
    in_dim_table = False
    dim_cols = False
    for i, line in enumerate(lines):
        if "| 维度优先级 | 具体维度 | 风险等级 | 说明 |" in line or "| 维度 | 风险等级 | 说明 |" in line:
            in_dim_table = True
            dim_cols = "| 维度 |" in line  # 三列格式
            continue
        if in_dim_table:
            if line.strip().startswith("|") and "---" in line:
                continue
            if line.strip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 4 and not dim_cols:
                    name = cells[1]
                    risk_str = cells[2]
                    desc = cells[3] if len(cells) > 3 else ""
                elif len(cells) >= 3 and dim_cols:
                    name = cells[0]
                    risk_str = cells[1]
                    desc = cells[2] if len(cells) > 2 else ""
                else:
                    continue
                # 清理优先级星号
                name = re.sub(r'^\s*⭐+\s*', '', name)
                # 提取风险等级
                risk = parse_report_risk(risk_str)
                if risk != "none" or "❓" not in risk_str:
                    result["dimensions"].append({
                        "name": name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                        "risk": risk,
                        "desc": desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    })
            else:
                in_dim_table = False

    # 解析关键风险点
    in_key_risks = False
    current_risk_title = ""
    current_risk_detail = ""
    for line in lines:
        if line.strip().startswith("🔍 关键风险点") or line.strip() == "## 🔍 关键风险点":
            in_key_risks = True
            continue
        if in_key_risks:
            # 遇到建议措施章节，停止解析关键风险点
            if "💡 建议措施" in line or line.strip().startswith("## 💡 建议措施") or line.strip().startswith("## ✅ 建议措施"):
                if current_risk_title:
                    result["keyRisks"].append({
                        "title": current_risk_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                        "detail": current_risk_detail.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    })
                in_key_risks = False
                continue
            if line.strip().startswith("---") or line.strip().startswith("━━"):
                if current_risk_title:
                    result["keyRisks"].append({
                        "title": current_risk_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                        "detail": current_risk_detail.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    })
                    current_risk_title = ""
                    current_risk_detail = ""
                continue
            if line.strip().startswith("## ") and "关键风险点" not in line:
                if current_risk_title:
                    result["keyRisks"].append({
                        "title": current_risk_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                        "detail": current_risk_detail.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    })
                    current_risk_title = ""
                    current_risk_detail = ""
                in_key_risks = False
                continue
            # 匹配 "1、**标题**" 格式
            title_match = re.match(r'^\d+[、\.]\s*\*\*(.+?)\*\*', line.strip())
            if title_match:
                if current_risk_title:
                    result["keyRisks"].append({
                        "title": current_risk_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                        "detail": current_risk_detail.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    })
                current_risk_title = title_match.group(1)
                # 标题后面的正文也在同一行
                after = line.strip()[line.strip().index("**", line.strip().index("**") + 2) + 2:].strip()
                current_risk_detail = after
            elif current_risk_title:
                current_risk_detail += " " + line.strip()
    if current_risk_title:
        result["keyRisks"].append({
            "title": current_risk_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
            "detail": current_risk_detail.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        })

    # ── 将原始 markdown 文本转为基本 HTML ──
    def _esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    def _md_to_html(text):
        """将 markdown 文本转为 HTML，保留 <svg> 等原始标签"""
        if not text:
            return ""
        if "<svg" in text:
            return text  # SVG 已是 HTML，直接保留
        import re as _re
        result_lines = []
        in_ul = False
        for line in text.split("\n"):
            s = line.strip()
            # 跳过纯分隔线
            if _re.match(r"^[\u2501━┅─━─\u2500-]{3,}$", s) or s.startswith("━━"):
                if in_ul:
                    result_lines.append("</ul>")
                    in_ul = False
                continue
            # 引用块
            if s.startswith(">"):
                c = s.lstrip(">").strip()
                result_lines.append(f'<blockquote>{_esc(c)}</blockquote>')
                continue
            # 无序列表项
            lm = _re.match(r"^[-•*]\s+(.+)", s)
            if lm:
                if not in_ul:
                    result_lines.append("<ul>")
                    in_ul = True
                content = _process_inline(_esc(lm.group(1)))
                result_lines.append(f"  <li>{content}</li>")
                continue
            if in_ul:
                result_lines.append("</ul>")
                in_ul = False
            # 普通段落
            if s:
                result_lines.append(f"<p>{_process_inline(_esc(s))}</p>")
        if in_ul:
            result_lines.append("</ul>")
        return "\n".join(result_lines)

    def _process_inline(text):
        import re as _re
        text = _re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        return text

    # 解析详细分析章节（不含建议措施）
    in_section = False
    current_section_title = ""
    current_section_lines = []
    rec_keywords = ("短期", "中期", "长期")
    for i, line in enumerate(lines):
        ls = line.strip().rstrip("\r")
        m = re.match(r"^####\s+(.+)", ls)
        if m:
            header = m.group(1).strip()
            # 遇到建议措施的周期标题时停止 sections 解析
            if header.startswith(rec_keywords):
                if current_section_title:
                    raw = "\n".join(current_section_lines)
                    if raw.strip():
                        result["sections"].append({
                            "title": _esc(current_section_title),
                            "content": "",
                            "html": _md_to_html(raw)
                        })
                break
            # 如果当前已有 section 且遇到新标题，先保存旧的再开始新的
            # "图" 开头的标题（如 "图1：近3年营收"）视为独立图表 section
            # 其他子标题（如 "①公司财务状况"）也各自创建独立 section
            if current_section_title:
                raw = "\n".join(current_section_lines)
                if raw.strip():
                    result["sections"].append({
                        "title": _esc(current_section_title),
                        "content": "",
                        "html": _md_to_html(raw)
                    })
            current_section_title = header
            current_section_lines = []
            in_section = True
        elif in_section:
            if re.match(r"^[\u2501━┅─━─\u2500-]{3,}$", ls) or ls.startswith("━━") or ls.startswith("━━━"):
                # 保存当前 section
                if current_section_title:
                    raw = "\n".join(current_section_lines)
                    if raw.strip():
                        result["sections"].append({
                            "title": _esc(current_section_title),
                            "content": "",
                            "html": _md_to_html(raw)
                        })
                # 只有遇到明确的章节结束标记才退出：separator 后紧跟建议措施章节
                # 向前看一行判断是否是章节结束
                next_idx = i + 1
                next_line = lines[next_idx].strip().rstrip("\r") if next_idx < len(lines) else ""
                if next_line.startswith(rec_keywords) or "💡 建议措施" in next_line:
                    break
                # 否则继续（这可能是章节内的分隔线），清空并保持 in_section
                current_section_title = ""
                current_section_lines = []
                in_section = False
            else:
                current_section_lines.append(line)

    # 解析建议措施
    in_recs = False
    rec_period = ""   # 当前周期标题
    pending_recs = []  # 当前周期内累积的建议项
    for line in lines:
        ls = line.strip().rstrip("\r")
        if "💡 建议措施" in ls:
            in_recs = True
            continue
        if in_recs:
            if ls.startswith("---") or ls.startswith("━━"):
                # 分隔线：先将 pending 合并到结果（因为后面会换 period）
                if pending_recs:
                    result["recommendations"].extend(pending_recs)
                    pending_recs = []
                rec_period = ""
                continue
            if ls.startswith("## ") and "建议" not in ls:
                # 建议措施章节结束：保存 pending
                if pending_recs:
                    result["recommendations"].extend(pending_recs)
                    pending_recs = []
                in_recs = False
                continue
            # 匹配建议周期标题（### 或 #### 格式）
            pm = re.match(r"^#{3,4}\s+(.+)", ls)
            if pm:
                # 换新周期前，保存旧周期内的建议
                if pending_recs:
                    result["recommendations"].extend(pending_recs)
                    pending_recs = []
                rec_period = _esc(pm.group(1).strip())
                continue
            # 匹配建议内容
            rm = re.match(r"^\d+[、\.]\s*\*\*(.+?)\*\*[：:：]?\s*(.*)", ls)
            if rm and rec_period:
                title = rm.group(1)
                detail = rm.group(2).strip() if rm.group(2) else ""
                pending_recs.append({
                    "period": rec_period,
                    "content": _esc(title + ("：" + detail if detail else ""))
                })
                continue
            # 续行：累加到当前建议的 content（如来源注释）
            if rec_period and pending_recs and ls:
                last = pending_recs[-1]
                last["content"] += " " + _esc(ls)
    # 循环结束后保存最后的 pending
    if pending_recs:
        result["recommendations"].extend(pending_recs)

    # 提取信息来源统计
    for line in lines:
        if "信息来源统计" in line or "本次信息来源统计" in line:
            src_parts = []
            for j in range(lines.index(line) + 1, min(lines.index(line) + 10, len(lines))):
                if lines[j].strip().startswith("•") or lines[j].strip().startswith("-"):
                    src_parts.append(lines[j].strip())
                elif lines[j].strip() == "":
                    break
            result["sources"] = " ".join(src_parts).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            break

    return result


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
        # 检查日期是否在一周内
        try:
            report_dt = datetime.strptime(report["date"], "%Y-%m-%d")
            if report_dt < one_week_ago:
                print(f"  ⏭️ 跳过过期快报: {os.path.basename(fp)} ({report['date']})")
                continue
        except ValueError:
            pass
        alerts.append(report)
        print(f"  ✅ 预警快报: {os.path.basename(fp)} → {report['date']}, {len(report['suppliers'])}个供应商")

    # 2. 解析采购报告（每类别只保留最新一个）
    report_files = sorted(
        glob.glob(os.path.join(REPORTS_SOURCE_DIR, "*采购风险分析报告*.md")),
        reverse=True
    )
    reports = []
    seen_categories = set()
    for fp in report_files:
        # 提取类别：文件名中 "_采购风险分析报告" 前的文字
        basename = os.path.basename(fp)
        cat_match = re.match(r"(.+?)_采购风险分析报告", basename)
        category = cat_match.group(1) if cat_match else os.path.splitext(basename)[0]
        if category in seen_categories:
            print(f"  ⏭️ 跳过旧报告（类别已有更新）: {os.path.basename(fp)} [{category}]")
            continue
        report = parse_analysis_report(fp)
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
