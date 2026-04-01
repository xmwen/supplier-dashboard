"""Generate alerts_summary.json and reports_data.json from source markdown files."""
import json, glob, os, re
from datetime import datetime, timedelta

# === 预警快报 ===
alert_files = sorted(glob.glob(r'D:\workbuddy\supplier_discover\output\采购风险预警快报_*.md'))
week_ago = datetime.now() - timedelta(days=7)
alerts = []
for f in alert_files:
    basename = os.path.basename(f)
    m = re.search(r'(\d{8})', basename)
    if not m:
        continue
    date_str = m.group(1)
    dt = datetime.strptime(date_str, '%Y%m%d')
    if dt < week_ago:
        continue
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    high = len(re.findall(r'风险等级[：:]\s*高', content))
    mid = len(re.findall(r'风险等级[：:]\s*中', content))
    low = len(re.findall(r'风险等级[：:]\s*低', content))
    none = len(re.findall(r'风险等级[：:]\s*无异常', content))
    date_label = f'{dt.year}年{dt.month}月{dt.day}日'
    alerts.append({
        'date': dt.strftime('%Y-%m-%d'),
        'dateLabel': date_label,
        'fileContent': content,
        'summary': {'high': high, 'mid': mid, 'low': low, 'none': none}
    })

with open(r'D:\workbuddy\supplier_dashboard\output\alerts_summary.json', 'w', encoding='utf-8') as f:
    json.dump(alerts, f, ensure_ascii=False, indent=2)
print(f'alerts: {len(alerts)} files')

# === 采购报告 ===
report_files = sorted(glob.glob(r'D:\workbuddy\supplier_analysis\output\*采购风险分析报告*.md'))
latest = {}
for f in report_files:
    basename = os.path.basename(f)
    m = re.match(r'(.+?)_', basename)
    if m:
        supplier = m.group(1)
        latest[supplier] = f

reports = []
for supplier, f in latest.items():
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()
    m = re.search(r'报告日期[：:]\s*(.+)', content)
    report_date = m.group(1).strip() if m else ''
    m2 = re.search(r'风险等级[：:]\s*(.+)', content)
    risk_raw = m2.group(1).strip() if m2 else 'none'
    risk_map = {'高': 'high', '中': 'mid', '低': 'low'}
    overall_risk = 'none'
    for k, v in risk_map.items():
        if k in risk_raw:
            overall_risk = v
            break
    m3 = re.search(r'总体评估[：:]\s*(.+?)(?:\n|$)', content)
    summary = m3.group(1).strip() if m3 else ''
    m4 = re.match(r'.+?_(.+?)_采购风险分析报告', os.path.basename(f))
    product = m4.group(1) if m4 else ''
    reports.append({
        'supplierName': supplier,
        'product': product,
        'reportDate': report_date,
        'overallRisk': overall_risk,
        'summary': summary,
        'fileContent': content
    })

with open(r'D:\workbuddy\supplier_dashboard\output\reports_data.json', 'w', encoding='utf-8') as f:
    json.dump(reports, f, ensure_ascii=False, indent=2)
print(f'reports: {len(reports)} files')
print('JSON generation done')
