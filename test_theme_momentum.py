#!/usr/bin/env python3
"""验证题材热度 v2.7 数据驱动动量算法。不涉及网络。"""
import importlib.util, os, sys

# 动态导入 step2_stockscorer_v2 模块
spec = importlib.util.spec_from_file_location(
    "step2", os.path.join(os.path.dirname(__file__), "step2_stockscorer_v2.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def make_kl(trend_pct, n=60):
    """构造一条单调递减/递增的日K线：从100跌/涨到 100*(1+trend/100)"""
    closes = []
    end = 100.0 * (1 + trend_pct / 100.0)
    for i in range(n):
        c = 100.0 + (end - 100.0) * (i / (n - 1))
        closes.append({"date": f"2026-07-{i%28+1:02d}", "close": round(c, 2)})
    return closes

# 1) 个股动量计算
kl_down = make_kl(-15)     # 近20日约 -15%
kl_up = make_kl(+15)       # 近20日约 +15%
kl_flat = make_kl(-1)
print("个股20日动量 跌-15%:", m._stock_momentum(kl_down)[20])
print("个股20日动量 涨+15%:", m._stock_momentum(kl_up)[20])

# 2) 聚合：构造一个"近期大部分下跌"的题材(光模块)样本
mom_down = [m._stock_momentum(make_kl(-12)) for _ in range(5)]
mom_up = [m._stock_momentum(make_kl(+12)) for _ in range(5)]
mom_mix = [m._stock_momentum(make_kl(-8)), m._stock_momentum(make_kl(-6)),
           m._stock_momentum(make_kl(+2)), m._stock_momentum(make_kl(-10))]
mom_storage = [m._stock_momentum(make_kl(-10)) for _ in range(4)]
agg_down = m._agg_momentum(mom_down)
agg_up = m._agg_momentum(mom_up)
agg_mix = m._agg_momentum(mom_mix)
agg_storage = m._agg_momentum(mom_storage)
print("\n光模块(全跌) 20日中位:", round(agg_down[20]['median'],1), "上涨占比:", agg_down[20]['up_ratio'])
print("光模块(全涨) 20日中位:", round(agg_up[20]['median'],1), "上涨占比:", agg_up[20]['up_ratio'])
print("光模块(混合偏跌) 20日中位:", round(agg_mix[20]['median'],1), "上涨占比:", agg_mix[20]['up_ratio'])

# 3) score_theme 场景验证
sub_mom = {"光模块": agg_down, "AI芯片/CPU": agg_up, "存储芯片": agg_storage}
theme_mom = {"AI/半导体": agg_mix}
mom_map = {  # code -> 个股动量
    "sh600001": m._stock_momentum(make_kl(-14)),
    "sh600002": m._stock_momentum(make_kl(+14)),
}
print("\n=== score_theme 场景 ===")
# 场景A: 光模块个股(中际旭创), 内禀5, 题材全跌 -> 不应满分
sA = m.score_theme("中际旭创", "AI/半导体", -3.0, 1e9, ["AI/半导体"]*10,
                   mom_map=mom_map, theme_mom=theme_mom, sub_mom=sub_mom, code="sh600001")
print(f"光模块-近期下跌 内禀5 -> 评分={sA[0]} 生命周期={sA[3]}")
print("   理由:", sA[1][:4])
# 场景B: AI芯片个股(海光信息), 内禀5, 题材全涨 -> 满分(合理)
sB = m.score_theme("海光信息", "AI/半导体", 4.0, 1e9, ["AI/半导体"]*10,
                   mom_map=mom_map, theme_mom=theme_mom, sub_mom=sub_mom, code="sh600002")
print(f"AI芯片-近期上涨 内禀5 -> 评分={sB[0]} 生命周期={sB[3]}")
# 场景C: 存储芯片(兆易创新), 内禀5, 题材混合偏跌 -> 不应满分
sC = m.score_theme("兆易创新", "AI/半导体", -2.0, 1e9, ["AI/半导体"]*10,
                   mom_map=mom_map, theme_mom=theme_mom, sub_mom=sub_mom, code="sh600001")
print(f"存储芯片-混合偏跌 内禀5 -> 评分={sC[0]} 生命周期={sC[3]}")

assert sA[0] < 5, "❌ 下跌题材不应满分!"
assert sC[0] < 5, "❌ 偏跌题材不应满分!"
assert sB[0] == 5, "❌ 上涨题材应得满分(合理)!"
print("\n✅ 核心断言通过: 下跌/偏跌题材 < 5 分, 上涨题材 = 5 分")
