# 采购看板每日推送 - 标准工作流程

> 本文档是自动化任务的标准执行手册。每次执行时 AI 严格按此流程操作，避免遗漏和重复工作。

## 环境准备

执行前先确认以下路径可用：

| 用途 | 路径 |
|------|------|
| 工作目录 | `/home/hughxmwen/workspace/dashboard` |
| 预警快报源 | `/home/hughxmwen/workspace/supplier_discover/output/采购风险预警快报_*.md` |
| 采购报告源 | `/home/hughxmwen/workspace/supplier_analysis/output/*采购风险分析报告*.md` |
| 构建输出 | `/home/hughxmwen/workspace/dashboard/dist/` |
| Git | `git`（已在 PATH） |
| SSH | `/usr/bin/ssh` |
| Python | `python3` |

## 工作流程（增量模式）

### 第一步 + 第二步：运行 build.py

`build.py` 已集成完整流程，一条命令完成数据采集 + 索引构建：

```bash
cd /home/hughxmwen/workspace/dashboard
PYTHONIOENCODING=utf-8 python3 build.py
```

build.py 的职责：
- **数据采集**：扫描源目录的 Markdown 文件，增量对比，将新增/变更的文件转为 HTML + JSON 元数据
  - 预警快报：`/home/hughxmwen/workspace/supplier_discover/output/采购风险预警快报_*.md` → `dist/alerts/YYYY-MM-DD.html` + `.json`
  - 采购报告：`/home/hughxmwen/workspace/supplier_analysis/output/*采购风险分析报告*.md` → `dist/reports/供应商名-产品名.html` + `.json`
  - 增量策略：对比源文件与目标文件的修改时间，未变更的跳过
  - 报告按供应商-产品分组，每组只保留最新日期的一份
- **构建索引**：扫描 `dist/alerts/` 和 `dist/reports/` 下所有 `.json`，生成汇总索引 `dist/index.json`
- **复制模板**：将 `index.html` 模板复制到 `dist/index.html`

> **核心原则：不做内容解析/摘要，直接将原始 Markdown 转 HTML 片段。**

### 第三步：Git 推送

```bash
cd /home/hughxmwen/workspace/dashboard
git add -A
if git diff --cached --quiet; then
    # nothing to commit, skip push
    echo "No changes to commit"
else
    git commit -m "auto: daily dashboard update $(date +%Y-%m-%d)"
    git push origin main
fi
```

## 注意事项

1. **编码问题**：Python 必须设置 `PYTHONIOENCODING=utf-8` 环境变量
2. **增量策略**：build.py 内部已实现，对比源文件与目标文件修改时间，未变更的跳过
3. **Git 跳过**：如果没有文件变更（`git diff --cached --quiet` 返回 0），不执行 commit 和 push
4. **文件名规范**（build.py 内部已固化）：
   - 快报 HTML：`dist/alerts/YYYY-MM-DD.html`
   - 快报 JSON：`dist/alerts/YYYY-MM-DD.json`
   - 报告 HTML：`dist/reports/供应商名-产品名.html`（如 `村田-MLCC.html`）
   - 报告 JSON：`dist/reports/供应商名-产品名.json`