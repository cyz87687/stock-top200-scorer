#!/usr/bin/env python3
"""
生成A股成交额TOP200评分HTML报告 - 增强版
功能特性：
- 支持TOP200个股数据
- 响应式布局与移动端适配
- 实时排序筛选交互
- 关键指标可视化图表
- 优化的页面性能
"""

import json
import sys
from datetime import datetime

# 输入输出配置
inp = sys.argv[1] if len(sys.argv) > 1 else f"top200_scored_{datetime.now().strftime('%Y-%m-%d')}.json"
out = sys.argv[2] if len(sys.argv) > 2 else f"top200_report_{datetime.now().strftime('%Y-%m-%d')}.html"

# 加载数据
with open(inp, "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]
stats = data.get("stats", {})
date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
total_stocks = len(results)

# 颜色配置
RATING_COLORS = {"S": "#22c55e", "A": "#3b82f6", "B": "#f59e0b", "C": "#f97316", "D": "#ef4444"}
RATING_BG = {"S": "#dcfce7", "A": "#dbeafe", "B": "#fef3c7", "C": "#ffedd5", "D": "#fee2e2"}
RATING_FULL = {"S": "强烈推荐 · 可重仓", "A": "重点关注 · 逢低加仓", "B": "波段操作 · 轻仓参与", "C": "观望为主 · 不新开仓", "D": "坚决回避 · 立即卖出"}

top20 = [r for r in results if r["total"] >= 14]

def build_portfolio(results, n=5):
    candidates = []
    for r in results:
        if r["rating"] not in ("S", "A"):
            continue
        fwd_pe = r.get("fwd_pe")
        if not fwd_pe or fwd_pe <= 0 or fwd_pe > 60:
            continue
        growth = r.get("growth")
        if not growth or growth < 15:
            continue
        tech = r.get("tech", {})
        position = tech.get("position", 50)
        if position > 95:
            continue
        score_diversity = 0
        dims = [r["score_news"], r["score_tech"], r["score_fund"], r.get("score_theme", 0)]
        if min(dims) >= 3:
            score_diversity = 1
        if min(dims) >= 4:
            score_diversity = 2
        composite = r["total"] + score_diversity * 0.5
        if 40 <= position <= 80:
            composite += 0.5
        candidates.append((composite, r))

    candidates.sort(key=lambda x: -x[0])
    picks = []
    used_sectors = set()
    for _, r in candidates:
        sec = r.get("sector", "")
        if sec in used_sectors:
            continue
        picks.append(r)
        used_sectors.add(sec)
        if len(picks) >= n:
            break

    if len(picks) < n:
        for r in results:
            if r in picks:
                continue
            if r["rating"] not in ("S", "A"):
                continue
            fwd_pe = r.get("fwd_pe")
            if not fwd_pe or fwd_pe <= 0 or fwd_pe > 80:
                continue
            sec = r.get("sector", "")
            if sec in used_sectors:
                continue
            picks.append(r)
            used_sectors.add(sec)
            if len(picks) >= n:
                break
    return picks

portfolio_picks = build_portfolio(results)

# 板块均分TOP5
sec_avg = stats.get("sector_avg", {})
sorted_secs = sorted(sec_avg.items(), key=lambda x: -x[1].get("avg", 0))[:5]

# 开始生成HTML
html_parts = []

html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>📊 A股成交额TOP''' + str(total_stocks) + ''' 极简公司评分 | ''' + date_str + '''</title>
<style>
/* 基础样式 */
* {margin:0;padding:0;box-sizing:border-box;}
body {
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
    background:#0f172a;color:#e2e8f0;padding:16px;line-height:1.5;
}
.container {max-width:1400px;margin:0 auto;}

/* 头部 */
.header {text-align:center;padding:24px 0;border-bottom:1px solid #334155;margin-bottom:24px;}
.header h1 {font-size:24px;color:#f8fafc;margin-bottom:8px;}
.header .sub {color:#94a3b8;font-size:13px;margin-bottom:4px;}
.header .meta {color:#64748b;font-size:11px;}

/* 筛选控制 */
.controls {
    display:flex;gap:12px;margin:16px 0;flex-wrap:wrap;
    background:#1e293b;padding:16px;border-radius:12px;border:1px solid #334155;
}
.controls label {font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;}
.controls select, .controls input {
    background:#0f172a;border:1px solid #334155;color:#e2e8f0;
    padding:8px 12px;border-radius:6px;font-size:13px;min-width:140px;
}
.controls select:focus, .controls input:focus {outline:none;border-color:#3b82f6;}
.controls .control-group {flex:1;min-width:160px;}

/* 统计卡片 */
.summary {display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:20px 0;}
.card {
    background:#1e293b;border-radius:12px;padding:16px;text-align:center;
    border:1px solid #334155;transition:transform 0.2s;
}
.card:hover {transform:translateY(-2px);border-color:#475569;}
.card .count {font-size:28px;font-weight:800;margin:4px 0;}
.card .label {font-size:11px;color:#94a3b8;}

/* 图表区域 */
.charts {display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:20px 0;}
.chart-card {
    background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155;
}
.chart-card h3 {font-size:14px;color:#f8fafc;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.chart-container {height:200px;position:relative;}
.bar-chart {display:flex;align-items:flex-end;gap:8px;height:160px;padding:10px 0;}
.bar-item {flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;}
.bar {width:100%;background:linear-gradient(180deg,#3b82f6,#22c55e);border-radius:4px 4px 0 0;transition:height 0.3s;}
.bar-label {font-size:10px;color:#94a3b8;text-align:center;max-width:60px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.bar-value {font-size:11px;color:#e2e8f0;font-weight:700;}

/* 详情卡片 */
.section-title {
    font-size:16px;font-weight:700;color:#f8fafc;
    margin:28px 0 16px;padding-bottom:10px;border-bottom:2px solid #334155;
    display:flex;align-items:center;gap:8px;
}
.top-list {margin-bottom:30px;}
.stock-detail {
    background:#1e293b;border-radius:12px;padding:16px;margin-bottom:12px;
    border-left:4px solid #334155;border:1px solid #334155;transition:all 0.2s;
}
.stock-detail:hover {border-color:#475569;transform:translateX(4px);}
.stock-detail .header-row {
    display:flex;align-items:center;gap:12px;margin-bottom:10px;flex-wrap:wrap;
}
.stock-detail .rank {
    width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-size:14px;font-weight:800;color:#fff;flex-shrink:0;
}
.stock-detail .name {font-size:16px;font-weight:700;color:#f8fafc;}
.stock-detail .code {font-size:11px;color:#94a3b8;}
.stock-detail .total {font-size:28px;font-weight:800;margin-left:auto;}
.stock-detail .rating {
    font-size:12px;font-weight:700;padding:4px 12px;border-radius:8px;text-align:center;
}
.stock-detail .meta-row {
    display:flex;gap:12px;font-size:11px;color:#94a3b8;margin-bottom:10px;flex-wrap:wrap;
}
.stock-detail .dim-row {display:grid;grid-template-columns:repeat(4,1fr);gap:12px;font-size:12px;}
.stock-detail .dim-card {
    background:#0f172a;border-radius:8px;padding:12px;border:1px solid #334155;
}
.stock-detail .dim-card .dim-title {font-size:10px;color:#94a3b8;margin-bottom:6px;}
.stock-detail .dim-card .dim-score {font-size:18px;font-weight:700;margin-right:8px;}
.stock-detail .dim-card .dim-detail {font-size:10px;color:#94a3b8;line-height:1.6;margin-top:6px;}

/* 完整表格 */
.table-container {overflow-x:auto;background:#1e293b;border-radius:12px;border:1px solid #334155;}
.stock-table {width:100%;border-collapse:collapse;min-width:800px;}
.stock-table th {
    background:#0f172a;color:#94a3b8;padding:12px 10px;text-align:left;
    font-weight:600;font-size:11px;position:sticky;top:0;z-index:10;
    border-bottom:1px solid #334155;cursor:pointer;user-select:none;transition:background 0.2s;
}
.stock-table th:hover {background:#1e293b;}
.stock-table td {padding:10px;border-bottom:1px solid #334155;font-size:12px;}
.stock-table tr:hover td {background:#273449;}

/* 表格内元素 */
.s-rank {color:#64748b;font-weight:700;width:40px;}
.s-name {font-weight:700;color:#f8fafc;}
.s-code {color:#94a3b8;font-size:11px;}
.s-pct {font-weight:700;text-align:right;min-width:60px;}
.s-pct.up {color:#ef4444;}
.s-pct.down {color:#22c55e;}
.s-scores {display:flex;gap:4px;justify-content:center;}
.s-score {
    width:24px;height:24px;border-radius:4px;display:flex;align-items:center;justify-content:center;
    font-size:11px;font-weight:700;color:#fff;
}
.s-total {font-size:14px;font-weight:800;text-align:center;min-width:50px;}
.s-rating {
    font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;text-align:center;display:inline-block;
}
.s-pe {color:#94a3b8;font-size:11px;min-width:80px;}
.s-turnover {color:#94a3b8;font-size:11px;text-align:right;}
.s-sector {color:#94a3b8;font-size:11px;}

.hidden-row {display:none !important;}

/* 底部 */
.footer {
    text-align:center;color:#475569;font-size:11px;margin-top:40px;
    padding:24px 0;border-top:1px solid #334155;
}
.footer p {margin:6px 0;}

/* 响应式布局 */
@media (max-width:1200px) {
    .charts {grid-template-columns:1fr;}
    .stock-detail .dim-row {grid-template-columns:repeat(2,1fr);}
}
@media (max-width:768px) {
    .summary {grid-template-columns:repeat(2,1fr);}
    .controls {flex-direction:column;}
    .controls .control-group {width:100%;}
    .controls select, .controls input {width:100%;}
    .stock-detail .rank {width:32px;height:32px;font-size:12px;}
    .stock-detail .name {font-size:14px;}
    .stock-detail .total {font-size:20px;}
    .stock-detail .dim-row {grid-template-columns:1fr;}
    .header h1 {font-size:18px;}
}
@media (max-width:480px) {
    .summary {grid-template-columns:1fr;}
    body {padding:10px;}
}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 A股成交额TOP''' + str(total_stocks) + ''' 极简公司评分</h1>
        <div class="sub">Stock-Scorer v4.1 | 题材热度30% · 基本面30%(含行业前景) · 消息面20% · 技术面20%</div>
        <div class="meta">''' + date_str + ''' | 数据源：东方财富 + 腾讯K线 + iFinD</div>
    </div>

    <!-- 统计卡片 -->
    <div class="summary">''')

# 添加统计卡片
for r in ["S", "A", "B", "C", "D"]:
    count = stats.get("rating_dist", {}).get(r, 0)
    html_parts.append(f'''
        <div class="card">
            <div class="count" style="color:{RATING_COLORS[r]}">{count}</div>
            <div class="label">{r}级 · {RATING_FULL[r]}</div>
        </div>''')

html_parts.append('''
    </div>

    <!-- 今日数据总结 + 组合推荐 -->
    <div class="charts">
        <!-- 今日数据总结 -->
        <div class="chart-card" style="padding:16px;">
            <h3 style="font-size:13px;margin-bottom:10px;">📋 今日数据总结</h3>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px;">
                <div style="background:#0f172a;border-radius:6px;padding:8px;text-align:center;">
                    <div style="font-size:10px;color:#94a3b8;">覆盖个股</div>
                    <div style="font-size:18px;font-weight:800;color:#f8fafc;">''' + str(total_stocks) + '''只</div>
                </div>
                <div style="background:#0f172a;border-radius:6px;padding:8px;text-align:center;">
                    <div style="font-size:10px;color:#94a3b8;">S+A级占比</div>
                    <div style="font-size:18px;font-weight:800;color:#22c55e;">''' + f"{(stats.get('rating_dist',{}).get('S',0)+stats.get('rating_dist',{}).get('A',0))/max(total_stocks,1)*100:.0f}" + '''%</div>
                </div>
                <div style="background:#0f172a;border-radius:6px;padding:8px;text-align:center;">
                    <div style="font-size:10px;color:#94a3b8;">主线板块</div>
                    <div style="font-size:18px;font-weight:800;color:#3b82f6;">''' + str(len([s for s,v in sec_avg.items() if v.get("count",0)>=5])) + '''个</div>
                </div>
            </div>
            <div style="font-size:11px;color:#94a3b8;margin-bottom:6px;">板块均分TOP5</div>''')

for s, v in sorted_secs:
    cnt = v.get("count", 0)
    avg = v.get("avg", 0)
    bar_w = round(min(avg / 20 * 100, 100), 1)
    html_parts.append(f'''
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="color:#e2e8f0;font-size:11px;min-width:60px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{s}</span>
                    <div style="flex:1;background:#0f172a;border-radius:3px;height:12px;overflow:hidden;">
                        <div style="width:{bar_w}%;height:100%;background:linear-gradient(90deg,#3b82f6,#22c55e);border-radius:3px;"></div>
                    </div>
                    <span style="color:#94a3b8;font-size:10px;min-width:55px;text-align:right;">{avg:.1f} ({cnt}只)</span>
                </div>''')

html_parts.append('''
        </div>

        <!-- 组合推荐 -->
        <div class="chart-card" style="padding:16px;">
            <h3 style="font-size:13px;margin-bottom:10px;">🎯 组合推荐 · 板块分散+估值合理</h3>''')

for i, r in enumerate(portfolio_picks):
    rating = r["rating"]
    total = r["total"]
    fwd = r.get("fwd_pe", "-")
    growth = r.get("growth", "-")
    sub = r.get("sub_theme", r["sector"])
    tech = r.get("tech", {})
    position = tech.get("position", 0)
    dims = [r["score_news"], r["score_tech"], r["score_fund"], r.get("score_theme", 0)]
    min_dim = min(dims)
    growth_str = f"{growth:+.0f}%" if isinstance(growth, (int, float)) else str(growth)
    fwd_str = f"{fwd:.1f}x" if isinstance(fwd, (int, float)) else str(fwd)
    pos_str = f"分位{position:.0f}%" if position else ""
    balance_tag = "均衡" if min_dim >= 3 else ""
    tags = [t for t in [sub, pos_str, balance_tag] if t]

    html_parts.append(f'''
                <div style="background:#0f172a;border-radius:6px;padding:8px 10px;margin-bottom:6px;border-left:3px solid {RATING_COLORS[rating]};">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span style="font-size:13px;font-weight:800;color:#f8fafc;">{i+1}. {r["name"]}</span>
                        <span style="font-size:10px;font-weight:700;padding:1px 6px;border-radius:3px;background:{RATING_BG[rating]};color:{RATING_COLORS[rating]};">{rating}</span>
                        <span style="font-size:14px;font-weight:800;color:{RATING_COLORS[rating]};margin-left:auto;">{total:.1f}</span>
                    </div>
                    <div style="display:flex;gap:8px;font-size:10px;color:#94a3b8;margin-top:3px;flex-wrap:wrap;">
                        <span>FwdPE {fwd_str}</span>
                        <span>增速 {growth_str}</span>
                        <span>{' · '.join(tags)}</span>
                    </div>
                </div>''')

html_parts.append('''
                <div style="font-size:9px;color:#475569;margin-top:6px;padding:6px 8px;background:rgba(249,115,22,0.1);border-radius:4px;">
                    ⚠️ 筛选：S/A级 + FwdPE≤60 + 增速≥15% + 分位≤95% + 板块去重 + 四维均衡加分，仅供研究参考
                </div>
        </div>
    </div>

    <!-- 深度分析 -->
    <div class="top-list">
        <div class="section-title">🏆 评分≥14 综合排名 · 投资建议详情 ({len(top20)}只)</div>''')

# 生成详情卡片
for idx, r in enumerate(top20):
    i = idx + 1
    pct = r.get("pct_chg", 0) or 0
    pct_cls = "up" if pct > 0 else "down" if pct < 0 else ""
    rating = r["rating"]
    total = r["total"]
    rank_color = "#f59e0b" if i == 1 else "#94a3b8" if i == 2 else "#cd853f" if i == 3 else "#64748b"

    pe = r.get("pe", 0)
    fwd = r.get("fwd_pe")
    growth = r.get("growth")
    pe_str = f"PE(TTM) {pe:.0f}x" if pe and pe > 0 else "PE(TTM) N/A"
    fwd_str = f" → Fwd {fwd:.0f}x" if fwd else ""
    g_str = f" 增速 {growth:+.0f}%" if growth else " 增速 N/A"
    peg_val = r.get("pe_ladder")
    peg_str = ""
    if peg_val and isinstance(peg_val, dict):
        yrs = sorted(peg_val.keys())
        peg_str = " 阶梯" + "→".join(f"{peg_val[y]}" for y in yrs)
    sub_theme = r.get("sub_theme", "")
    turnover_yi = (r.get("turnover", 0) or 0) / 100000000

    news_reasons = r.get("news_reasons", [])
    fund_reasons = r.get("fund_reasons", [])
    theme_reasons = r.get("theme_reasons", r.get("flow_reasons", []))
    tech = r.get("tech", {})

    news_html = "<br>".join([n.replace("⚠️", "") for n in news_reasons[:3]]) if news_reasons else "无消息数据"
    risk_parts = [n for n in news_reasons if "⚠" in n]
    risk_html = "<br>".join([n.replace("⚠️", "") for n in risk_parts[:2]]) if risk_parts else ""

    boll_label = tech.get("boll_label", "")
    boll_pos = tech.get("boll_pos")
    boll_info = f"BOLL:{boll_label}({boll_pos:.0f}%)" if boll_label and boll_pos is not None else ""

    justification = []
    if r['score_news'] >= 4: justification.append("消息面强劲")
    elif r['score_news'] <= 1: justification.append("消息面疲弱")
    if r['score_tech'] >= 4: justification.append("技术面看多")
    elif r['score_tech'] <= 1: justification.append("技术面承压")
    if r['score_fund'] >= 4: justification.append("估值吸引力强")
    elif r['score_fund'] <= 1: justification.append("估值偏高")
    if r.get('score_theme', 0) >= 4: justification.append("主线题材热度高")
    elif r.get('score_theme', 0) <= 1: justification.append("题材冷门")
    if not justification: justification = ["各维度均衡"]

    html_parts.append(f'''
        <div class="stock-detail" data-rating="{rating}" data-sector="{r.get('sector','')}" data-code="{r['code']}" data-name="{r['name']}">
            <div class="header-row">
                <div class="rank" style="background:{rank_color}">#{i}</div>
                <div>
                    <div class="name">{r['name']}</div>
                    <div class="code">{r['code']} · {r.get('sector','')}</div>
                </div>
                <span class="s-pct {pct_cls}" style="font-size:13px;font-weight:700;">{pct:+.2f}%</span>
                <div class="total" style="color:{RATING_COLORS[rating]}">{total:.1f}</div>
                <div class="rating" style="background:{RATING_BG[rating]};color:{RATING_COLORS[rating]}">{rating}</div>
            </div>
            <div class="meta-row">
                <span>💰 成交额: {turnover_yi:.0f}亿</span>
                <span>📊 {pe_str}{fwd_str}{g_str}{peg_str}</span>
                <span>🏷️ {r['score_news']}/5消息 · {r['score_tech']}/5技术 · {r['score_fund']}/5基本 · {r.get('score_theme',0)}/5热度</span>
            </div>
            <div class="dim-row">
                <div class="dim-card">
                    <div class="dim-title">📰 消息面 ({r['score_news']}/5)</div>
                    <div class="dim-score">{r['score_news']}</div>
                    <div class="dim-detail">{news_html}</div>
                </div>
                <div class="dim-card">
                    <div class="dim-title">📈 技术面 ({r['score_tech']}/5)</div>
                    <div class="dim-score">{r['score_tech']}</div>
                    <div class="dim-detail">趋势: {tech.get('trend','N/A')} · 分位: {tech.get('position','N/A')}%{f' · {boll_info}' if boll_info else ''} · {tech.get('reason','')}</div>
                </div>
                <div class="dim-card">
                    <div class="dim-title">📊 基本面 ({r['score_fund']}/5)</div>
                    <div class="dim-score">{r['score_fund']}</div>
                    <div class="dim-detail">{', '.join(fund_reasons[:3]) if fund_reasons else '数据不足'}</div>
                </div>
                <div class="dim-card">
                    <div class="dim-title">🔥 题材热度 ({r.get('score_theme',0)}/5){f' · {sub_theme}' if sub_theme else ''}</div>
                    <div class="dim-score">{r.get('score_theme',0)}</div>
                    <div class="dim-detail">{', '.join(theme_reasons[:3]) if theme_reasons else '数据不足'}</div>
                </div>
            </div>''')

    if risk_html:
        html_parts.append(f'''
            <div style="font-size:11px;color:#f97316;margin-top:10px;padding:10px;background:rgba(249,115,22,0.1);border-radius:8px;">⚠️ {risk_html}</div>''')

    html_parts.append(f'''
            <div style="font-size:11px;color:#38bdf8;margin-top:8px;">💡 评级原因: {', '.join(justification[:4])} → {rating}级 · {r.get('advice',RATING_FULL.get(rating,''))}</div>
        </div>''')

html_parts.append('''
    </div>

    <!-- 完整表格 -->
    <div class="section-title">📋 完整排名 (可排序/筛选)</div>
    
    <!-- 筛选控制 -->
    <div class="controls">
        <div class="control-group">
            <label>🔍 搜索股票</label>
            <input type="text" id="searchInput" placeholder="输入名称或代码...">
        </div>
        <div class="control-group">
            <label>📊 排序方式</label>
            <select id="sortSelect">
                <option value="total">综合得分 (默认)</option>
                <option value="turnover">成交额</option>
                <option value="pct_chg">涨跌幅</option>
                <option value="pe">PE估值</option>
                <option value="score_news">消息面</option>
                <option value="score_tech">技术面</option>
                <option value="score_fund">基本面</option>
                <option value="score_theme">题材热度</option>
            </select>
        </div>
        <div class="control-group">
            <label>⭐ 评级筛选</label>
            <select id="ratingFilter">
                <option value="">全部评级</option>
                <option value="S">S 级</option>
                <option value="A">A 级</option>
                <option value="B">B 级</option>
                <option value="C">C 级</option>
                <option value="D">D 级</option>
            </select>
        </div>
        <div class="control-group">
            <label>🏷️ 板块筛选</label>
            <select id="sectorFilter">
                <option value="">全部板块</option>
            </select>
        </div>
        <div class="control-group">
            <label>📈 显示数量</label>
            <select id="displayCount">
                <option value="''' + str(total_stocks) + '''">全部''' + str(total_stocks) + '''只</option>
                <option value="100">TOP100</option>
                <option value="50">TOP50</option>
                <option value="30">TOP30</option>
                <option value="20">TOP20</option>
                <option value="10">TOP10</option>
            </select>
        </div>
    </div>
    
    <div class="table-container">
        <table class="stock-table" id="stockTable">
            <thead>
                <tr>
                    <th class="s-rank" data-sort="rank"># ↕</th>
                    <th class="s-name" data-sort="name">名称 ↕</th>
                    <th class="s-code">代码</th>
                    <th class="s-sector">板块</th>
                    <th class="s-pct" data-sort="pct_chg">涨跌幅 ↕</th>
                    <th class="s-scores">四项评分</th>
                    <th class="s-total" data-sort="total">总分 ↕</th>
                    <th class="s-rating">评级</th>
                    <th class="s-pe">PE(TTM)/Fwd/阶梯</th>
                    <th class="s-sector">细分题材</th>
                    <th class="s-turnover" data-sort="turnover">成交额 ↕</th>
                </tr>
            </thead>
            <tbody id="tableBody">''')

# 生成表格行
for idx, r in enumerate(results):
    i = idx + 1
    pct = r.get("pct_chg", 0) or 0
    pct_cls = "up" if pct > 0 else "down" if pct < 0 else ""
    rating = r["rating"]
    fwd = f"{r['fwd_pe']:.0f}x" if r.get("fwd_pe") else "-"
    growth = f"{r['growth']:+.0f}%" if r.get("growth") else "-"
    ladder_val = r.get("pe_ladder")
    if ladder_val and isinstance(ladder_val, dict):
        yrs = sorted(ladder_val.keys())
        ladder_t = "→".join(f"{ladder_val[y]}" for y in yrs)
    else:
        ladder_t = "-"
    pe = f"{r['pe']:.0f}" if r.get("pe") and r["pe"] > 0 else "-"
    sub_theme_t = r.get("sub_theme", "-")
    turnover_yi = (r.get("turnover", 0) or 0) / 100000000

    scores = [r["score_news"], r["score_tech"], r["score_fund"], r.get("score_theme", r.get("score_flow", 0))]
    score_colors = ["#ef4444", "#f97316", "#f59e0b", "#3b82f6", "#22c55e"]
    scores_html = "".join([f'<div class="s-score" style="background:{score_colors[min(int(v),4)]}">{v}</div>' for v in scores])

    html_parts.append(f'''
                <tr data-rating="{rating}" data-sector="{r.get('sector','')}" data-code="{r['code']}" data-name="{r['name']}" data-original-rank="{i}">
                    <td class="s-rank" data-value="{i}">{i}</td>
                    <td class="s-name" data-value="{r['name']}">{r['name']}</td>
                    <td class="s-code" data-value="{r['code']}">{r['code']}</td>
                    <td class="s-sector" data-value="{r.get('sector','')}">{r.get('sector','')}</td>
                    <td class="s-pct {pct_cls}" data-value="{pct}">{pct:+.2f}%</td>
                    <td class="s-scores">{scores_html}</td>
                    <td class="s-total" data-value="{r['total']}" style="color:{RATING_COLORS[rating]}">{r['total']:.1f}</td>
                    <td class="s-rating" style="background:{RATING_BG[rating]};color:{RATING_COLORS[rating]}" data-value="{rating}">{rating}</td>
                    <td class="s-pe" data-value="{r.get('pe',0)}">{pe}/{fwd} {ladder_t} {growth}</td>
                    <td class="s-sector">{sub_theme_t if sub_theme_t else '-'}</td>
                    <td class="s-turnover" data-value="{r.get('turnover',0)}">{turnover_yi:.0f}亿</td>
                </tr>''')

html_parts.append('''
            </tbody>
        </table>
    </div>

    <div class="footer">
        <p>⚠️ 免责声明: 本报告由AI基于stock-scorer极简评分模型自动生成,仅供参考,不构成投资建议。投资有风险,入市需谨慎。</p>
        <p>评分模型: 题材热度30% + 基本面30%(含行业前景) + 消息面20% + 技术面20%</p>
        <p>Generated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
    </div>
</div>

<script>
// 数据存储
const sectors = new Set();

document.addEventListener('DOMContentLoaded', function() {
    initFilters();
    initSorting();
    collectSectors();
    applyFilters();
});

function collectSectors() {
    const rows = document.querySelectorAll('#stockTable tbody tr');
    rows.forEach(row => {
        if (row.dataset.sector) sectors.add(row.dataset.sector);
    });
    
    const sectorFilter = document.getElementById('sectorFilter');
    Array.from(sectors).sort().forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        sectorFilter.appendChild(opt);
    });
}

// 筛选相关
function initFilters() {
    document.getElementById('searchInput').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('sortSelect').addEventListener('change', applyFilters);
    document.getElementById('ratingFilter').addEventListener('change', applyFilters);
    document.getElementById('sectorFilter').addEventListener('change', applyFilters);
    document.getElementById('displayCount').addEventListener('change', applyFilters);
}

// 排序相关
let currentSort = {field: 'total', desc: true};
function initSorting() {
    document.querySelectorAll('#stockTable th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (currentSort.field === field) {
                currentSort.desc = !currentSort.desc;
            } else {
                currentSort.field = field;
                currentSort.desc = true;
            }
            applyFilters();
        });
    });
}

// 主筛选函数
function applyFilters() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const rating = document.getElementById('ratingFilter').value;
    const sector = document.getElementById('sectorFilter').value;
    const sortField = document.getElementById('sortSelect').value || currentSort.field;
    const displayCount = parseInt(document.getElementById('displayCount').value);
    
    if (sortField !== currentSort.field) {
        currentSort.field = sortField;
        currentSort.desc = true;
    }
    
    const tbody = document.getElementById('tableBody');
    let rows = Array.from(tbody.querySelectorAll('tr'));
    
    let visibleCount = 0;
    rows.forEach(row => {
        let show = true;
        if (search && !row.dataset.name.toLowerCase().includes(search) && !row.dataset.code.toLowerCase().includes(search)) {
            show = false;
        }
        if (rating && row.dataset.rating !== rating) {
            show = false;
        }
        if (sector && row.dataset.sector !== sector) {
            show = false;
        }
        
        if (show) {
            row.classList.remove('hidden-row');
            visibleCount++;
        } else {
            row.classList.add('hidden-row');
        }
    });
    
    rows.sort((a, b) => {
        let aVal, bVal;
        switch(currentSort.field) {
            case 'rank':
                aVal = parseInt(a.dataset.originalRank);
                bVal = parseInt(b.dataset.originalRank);
                break;
            case 'name':
                aVal = a.dataset.name;
                bVal = b.dataset.name;
                return currentSort.desc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
            case 'pct_chg':
                aVal = parseFloat(a.querySelector('.s-pct').dataset.value);
                bVal = parseFloat(b.querySelector('.s-pct').dataset.value);
                break;
            case 'total':
                aVal = parseFloat(a.querySelector('.s-total').dataset.value);
                bVal = parseFloat(b.querySelector('.s-total').dataset.value);
                break;
            case 'turnover':
                aVal = parseFloat(a.querySelector('.s-turnover').dataset.value);
                bVal = parseFloat(b.querySelector('.s-turnover').dataset.value);
                break;
            case 'pe':
                aVal = parseFloat(a.querySelector('.s-pe').dataset.value);
                bVal = parseFloat(b.querySelector('.s-pe').dataset.value);
                break;
            default:
                aVal = parseInt(a.dataset.originalRank);
                bVal = parseInt(b.dataset.originalRank);
        }
        return currentSort.desc ? (bVal - aVal) : (aVal - bVal);
    });
    
    rows.forEach(row => tbody.appendChild(row));
    
    let count = 0;
    rows.forEach(row => {
        if (!row.classList.contains('hidden-row')) {
            if (count < displayCount) {
                row.classList.remove('hidden-row');
                const rankCell = row.querySelector('.s-rank');
                rankCell.textContent = count + 1;
                count++;
            } else {
                row.classList.add('hidden-row');
            }
        }
    });
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}
</script>
</body>
</html>''')

# 合并并保存
html = "\n".join(html_parts)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

# 输出统计
print(f"✅ HTML报告已生成: {out}")
print(f"📊 包含 {total_stocks} 只个股")

sd = stats.get("rating_dist", {})
print(f"⭐ 评级分布: S:{sd.get('S',0)} A:{sd.get('A',0)} B:{sd.get('B',0)} C:{sd.get('C',0)} D:{sd.get('D',0)}")

fwd_ok = sum(1 for r in results if r.get("fwd_pe"))
growth_ok = sum(1 for r in results if r.get("growth"))
print(f"📋 数据完整度: Fwd PE:{fwd_ok}/{total_stocks} Growth:{growth_ok}/{total_stocks}")











