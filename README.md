# 采购发现团 - 快报看板

供应商采购风险预警快报的在线看板，通过 GitHub Pages 部署，支持手机访问。

## 项目结构

```
supplier_dashboard/
├── index.html      # 看板模板（含占位符 __REPORTS_DATA__）
├── build.py        # 构建脚本（读取 supplier_discover/output/ 生成 HTML）
├── dist/           # 构建产物（GitHub Pages 发布此目录）
│   └── index.html
└── .gitignore
```

## 工作流程

1. 采购发现团每天 8:00 执行，生成快报到 `supplier_discover/output/`
2. 运行 `python build.py` 将快报注入模板，生成 `dist/index.html`
3. 推送到 GitHub，GitHub Pages 自动更新
4. 手机访问 `https://xmwen.github.io/supplier-dashboard/` 查看快报

## 手动构建

```bash
cd D:\workbuddy\supplier_dashboard
python build.py
```
