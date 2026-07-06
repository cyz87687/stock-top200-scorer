#!/usr/bin/env python3
"""
获取沪深A股成交额TOP200 - 新浪财经行情中心
"""
import json, sys, os, time
import urllib.request
import ssl
from datetime import datetime

ssl._create_default_https_context = ssl._create_unverified_context

print(f"📊 获取A股全市场行情 (新浪财经) | {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def fetch_sina_page(page):
    url = (
        f"https://vip.stock.finance.sina.com.cn/quotes_service/api/"
        f"json_v2.php/Market_Center.getHQNodeData?page={page}&num=80&"
        f"sort=amount&asc=0&node=hs_a"
    )
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://vip.stock.finance.sina.com.cn/'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('gbk', errors='ignore'))

def fetch_all_stocks():
    all_data = []
    for page in range(1, 4):
        try:
            items = fetch_sina_page(page)
            if not items:
                break
            for item in items:
                code = item.get('code', '')
                name = item.get('name', '')
                price = item.get('trade', '0')
                pct = item.get('changepercent', '0')
                turnover = item.get('amount', '0')
                symbol = item.get('symbol', '')
                if not code or not name:
                    continue
                if any(x in name for x in ['ST', '退', '*ST']):
                    continue
                if code[0] not in '0368':
                    continue
                all_data.append({
                    'code': code, 'name': name,
                    'price': float(price) if price else 0.0,
                    'pct_chg': float(pct) if pct else 0.0,
                    'turnover': float(turnover) if turnover else 0.0,
                    'symbol': symbol,
                })
            print(f"   第{page}页: {len(items)}条")
            if len(items) < 80:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"   第{page}页失败: {e}")
            break
    return all_data

try:
    stocks = fetch_all_stocks()
    print(f"   总计获取: {len(stocks)}只")
    if len(stocks) < 200:
        print("❌ 获取数量不足200只")
        sys.exit(1)

    # 新浪已按成交额排序，直接取前200
    top200 = stocks[:200]

    result = {"top50": []}
    for s in top200:
        prefix = "sh" if s['code'].startswith('6') else "sz"
        result["top50"].append({
            "name": s['name'], "code": f"{prefix}{s['code']}",
            "price": s['price'], "pct_chg": s['pct_chg'],
            "turnover": s['turnover'], "amount": s['turnover']
        })

    tmp = "top200_all_a.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    if os.path.exists("top200_all_a.json"):
        os.remove("top200_all_a.json")
    os.rename(tmp, "top200_all_a.json")

    print(f"✅ 已保存 top200_all_a.json | TOP200只")
    print(f"   第1: {top200[0]['name']} ({top200[0]['code']}) 成交{top200[0]['turnover']/1e8:.1f}亿")
    print(f"   第200: {top200[199]['name']} ({top200[199]['code']}) 成交{top200[199]['turnover']/1e8:.1f}亿")

except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
