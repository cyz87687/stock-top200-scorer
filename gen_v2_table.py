#!/usr/bin/env python3
"""
生成A股TOP200 v2 紧凑表格报告
修复内容：
1. 目标价使用 boll_upper（修复7%fallback bug）
2. 空间%列使用正确CSS类（space-hi/md/lo/vl）
3. 排序DOM重排集成在JS模板中
"""

import json, sys, os, re, glob
from datetime import datetime

# ============================================================
# Config
# ============================================================
WORKDIR = os.path.dirname(os.path.abspath(__file__))

# Input: scored JSON
JSON_GLOB = os.path.join(WORKDIR, "top200_scored_*.json")
json_files = sorted(glob.glob(JSON_GLOB), reverse=True)
if not json_files:
    print("ERROR: no scored JSON found")
    sys.exit(1)
JSON_FILE = json_files[0]

# Extract date from filename
date_match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(JSON_FILE))
date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

# Output HTML
OUT_FILE = os.path.join(WORKDIR, f"top200_report_{date_str}_v2.html")

# Template files (extracted from existing v2 HTML)
HEAD_TPL = os.path.join(WORKDIR, "_template_head.html")
FOOT_TPL = os.path.join(WORKDIR, "_template_foot.html")

# ============================================================
# Load data
# ============================================================
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]

# ============================================================
# Computed fields
# ============================================================

def get_target_price(r):
    """使用 boll_upper 作为目标价，fallback: price * 1.10"""
    price = r["price"]
    tech = r.get("tech", {}) or {}
    bu = tech.get("boll_upper")
    if bu is not None and bu > 0:
        return round(bu, 2)
    return round(price * 1.10, 2)

def get_space_pct(r, target):
    """空间幅度百分比"""
    return round((target - r["price"]) / r["price"] * 100, 1)

def get_space_class(space_pct):
    """空间% CSS类"""
    if space_pct >= 20:
        return "space-hi"
    elif space_pct >= 10:
        return "space-md"
    elif space_pct >= 5:
        return "space-lo"
    return "space-vl"

def get_plratio(r):
    """盈亏比 = (基本面+消息+题材质量) / 技术风险，经增速调整"""
    fund = r["score_fund"]
    news = r["score_news"]
    techs = r["score_tech"]
    theme = r["score_theme"]
    growth = r.get("growth", 0) or 0
    fwd_pe = r.get("fwd_pe", 0) or 0

    # 基本面质量分
    quality = (fund + news + theme) / 3.0

    # 增速修正因子
    growth_factor = 1.0 + min(max(growth, 0), 300) / 200.0

    # 技术风险修正
    tech_risk = max(techs, 1.0) / 3.0

    # 估值修正
    pe_factor = 1.0
    if fwd_pe > 0 and fwd_pe < 15:
        pe_factor = 1.3  # 低估值溢价
    elif fwd_pe > 60:
        pe_factor = 0.7  # 高估值折价

    ratio = quality * growth_factor * pe_factor / tech_risk * 1.2
    return round(ratio, 2)

def get_plratio_class(pl):
    """盈亏比CSS类"""
    if pl >= 7:
        return "pl-2"
    elif pl >= 4:
        return "pl-1"
    return "pl-0"

def get_winrate(r):
    """胜率 = 基于技术面强弱 + 基本面质量"""
    tech = r.get("tech", {}) or {}
    position = tech.get("position", 50) or 50
    score_tech = r["score_tech"]
    score_fund = r["score_fund"]
    score_news = r["score_news"]
    score_theme = r["score_theme"]

    # 技术面贡献
    if score_tech >= 4:
        tech_bonus = 15
    elif score_tech >= 3:
        tech_bonus = 5
    else:
        tech_bonus = -5

    # 基本面贡献
    fund_bonus = int((score_fund + score_news + score_theme) * 2)

    # 位置修正
    if position < 30:
        pos_bonus = 10  # 低位胜率高
    elif position < 60:
        pos_bonus = 0
    elif position < 85:
        pos_bonus = -5
    else:
        pos_bonus = -10

    wr = 40 + tech_bonus + fund_bonus + pos_bonus
    return max(10, min(90, wr))

def get_winrate_class(wr):
    """胜率CSS类"""
    if wr >= 70:
        return "wr-hi"
    elif wr >= 50:
        return "wr-md"
    return "wr-lt"

def get_deviation(r):
    """偏离度 = (position - 50) * 0.28（近似）"""
    tech = r.get("tech", {}) or {}
    position = tech.get("position", 50) or 50
    return round((position - 50) * 0.28, 1)

def get_trend_label(r):
    """趋势标签"""
    tech = r.get("tech", {}) or {}
    trend = tech.get("trend", "")
    if "双线多头" in trend or ("周线多头" in trend and "日线多头" in trend):
        return "双周期多头", '<span class="tag-safe">双多</span>'
    elif "周线多头" in trend:
        return "周线多头", '<span class="tag-warn">周多</span>'
    elif "日线多头" in trend:
        return "日线多头", '<span class="tag-warn">日多</span>'
    else:
        return "双周期偏空", '<span class="tag-danger">偏空</span>'

def get_macd_status(r):
    """MACD状态"""
    tech = r.get("tech", {}) or {}
    # 简化：trend包含信号
    trend = tech.get("trend", "")
    if "金叉" in trend:
        return "金叉", "macd-gold"
    if "死叉" in trend:
        return "死叉", "macd-dead"
    return "-", "macd-none"

def get_resonance(r):
    """共振状态"""
    score_theme = r["score_theme"]
    score_tech = r["score_tech"]
    score_fund = r["score_fund"]
    tech = r.get("tech", {}) or {}
    trend = tech.get("trend", "")

    # 题材+趋势共振
    if score_theme >= 4 and ("多头" in trend):
        return "趋势确认", '<span class="tag-safe">共振</span>'
    elif score_fund >= 4 and score_theme >= 4:
        return "基本面共振", '<span class="tag-safe">共振</span>'
    elif score_tech >= 4 and score_theme >= 3:
        return "技术共振", '<span class="tag-warn">偏强</span>'
    elif score_theme <= 2 and ("空头" in trend or "偏空" in trend):
        return "弱势", '<span class="tag-danger">弱势</span>'
    return "中性", '<span class="tag-neutral">-</span>'

def get_strategy(r):
    """操作策略"""
    rating = r.get("rating", "B")
    advice = r.get("advice", "")
    total = r["total"]

    if rating == "S":
        return "重仓配置"
    elif rating == "A" and total >= 15:
        return "逢低加仓"
    elif rating == "A":
        return "持仓持有"
    elif rating == "B":
        return "轻仓博弈"
    return "观望"

# ============================================================
# Build CSS overrides for space classes
# ============================================================
SPACE_CLASS_CSS = """
.space-hi{color:#ef4444;font-weight:700;}
.space-md{color:#3b82f6;font-weight:700;}
.space-lo{color:#f59e0b;font-weight:700;}
.space-vl{color:#22c55e;font-weight:700;}
"""

# ============================================================
# Load templates
# ============================================================
if os.path.exists(HEAD_TPL) and os.path.exists(FOOT_TPL):
    with open(HEAD_TPL, "r", encoding="utf-8") as f:
        head = f.read()
    with open(FOOT_TPL, "r", encoding="utf-8") as f:
        foot = f.read()
else:
    # Extract from existing v2 HTML as fallback
    EXISTING_HTML = os.path.join(WORKDIR, "top200_report_2026-07-02_v2.html")
    if os.path.exists(EXISTING_HTML):
        with open(EXISTING_HTML, "r", encoding="utf-8") as f:
            html = f.read()
        tb_start = html.find('<tbody id="tbody">')
        tb_end = html.find('</tbody>', tb_start)
        head = html[:tb_start + len('<tbody id="tbody">\n')]
        foot = html[tb_end:]
    else:
        print("ERROR: No template found")
        sys.exit(1)

    # Save templates for next time
    with open(HEAD_TPL, "w", encoding="utf-8") as f:
        f.write(head)
    with open(FOOT_TPL, "w", encoding="utf-8") as f:
        f.write(foot)

# Inject space class CSS before </style>
style_end = head.rfind('</style>')
if style_end > 0:
    head = head[:style_end] + SPACE_CLASS_CSS + head[style_end:]

# Update date
head = head.replace('2026-07-02', date_str)

# ============================================================
# Generate data rows
# ============================================================
rows = []
for i, r in enumerate(results):
    idx = i + 1
    price = r["price"]
    target = get_target_price(r)
    space = get_space_pct(r, target)
    sp_cls = get_space_class(space)
    pl = get_plratio(r)
    pl_cls = get_plratio_class(pl)
    wr = get_winrate(r)
    wr_cls = get_winrate_class(wr)
    dev = get_deviation(r)
    trend_label, trend_html = get_trend_label(r)
    macd_label, macd_cls = get_macd_status(r)
    res_label, res_html = get_resonance(r)
    strategy = get_strategy(r)

    rating = r.get("rating", "B")
    total = r["total"]
    pct_chg = r.get("pct_chg", 0) or 0

    space_str = f"+{space}%" if space >= 0 else f"{space}%"

    # data-cs-* uses rating for color
    row = (
        f'<tr class="data-row" data-rank="{idx}" data-name="{r["name"]}" data-code="{r["code"]}" '
        f'data-price="{price}" data-target="{target}" data-space="{space}" '
        f'data-plratio="{pl}" data-winrate="{wr}" data-oldtotal="{total}" '
        f'data-trend="{trend_label}" data-macd="{macd_label}" data-resonance="{res_label}" '
        f'data-strategy="{strategy}" data-rating="{rating}" data-pctchg="{pct_chg}" '
        f'data-deviation="{dev}">\n'
        f'<td>{idx}</td>\n'
        f'<td class="s-name" style="cursor:pointer" onclick="showDetail({i})">{r["name"]}</td>\n'
        f'<td class="s-code">{r["code"][2:]}</td>\n'
        f'<td style="font-weight:700;color:#f8fafc;">{price:.2f}</td>\n'
        f'<td style="color:#94a3b8;">{target:.2f}</td>\n'
        f'<td class="{sp_cls}">{space_str}</td>\n'
        f'<td class="{pl_cls}">{pl:.2f}</td>\n'
        f'<td class="{wr_cls}">{wr}%</td>\n'
        f'<td class="cs-{rating}">{total:.1f}</td>\n'
        f'<td>{trend_html}</td>\n'
        f'<td><span class="{macd_cls}">{macd_label}</span></td>\n'
        f'<td>{res_html}</td>\n'
        f'<td class="st-watch">{strategy}</td>\n'
        f'</tr>'
    )
    rows.append(row)

tbody = '\n'.join(rows)

# ============================================================
# Assemble final HTML
# ============================================================
html = head + tbody + '\n' + foot

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

# ============================================================
# Report
# ============================================================
space_vals = [get_space_pct(r, get_target_price(r)) for r in results]
from collections import Counter
cls_cnt = Counter()
for r in results:
    sp = get_space_pct(r, get_target_price(r))
    cls_cnt[get_space_class(sp)] += 1

print(f"✅ v2报告已生成: {OUT_FILE}")
print(f"📊 总标的: {len(results)} | 日期: {date_str}")
print(f"📈 空间范围: {min(space_vals):.1f}% ~ {max(space_vals):.1f}%")
print(f"  正空间: {sum(1 for s in space_vals if s > 0)} | 负空间: {sum(1 for s in space_vals if s < 0)}")
print(f"  space-hi(≥20%): {cls_cnt.get('space-hi', 0)}")
print(f"  space-md(10-20%): {cls_cnt.get('space-md', 0)}")
print(f"  space-lo(5-10%): {cls_cnt.get('space-lo', 0)}")
print(f"  space-vl(<5%): {cls_cnt.get('space-vl', 0)}")

# Check for 7% fallback issue
fallback_count = 0
for r in results:
    target = get_target_price(r)
    expected_7pct = round(r["price"] * 1.07, 2)
    if abs(target - expected_7pct) < 0.02:
        fallback_count += 1
print(f"  ⚠️ 7%fallback标的: {fallback_count} (应尽量少)")

# Top 5 by space
print(f"\n🔝 空间幅度 TOP5:")
for r in sorted(results, key=lambda x: -get_space_pct(x, get_target_price(x)))[:5]:
    sp = get_space_pct(r, get_target_price(r))
    print(f"  {r['name']} ({r['code']}): +{sp}%")
