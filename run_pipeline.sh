#!/bin/bash
# A股TOP200 v2报告生成流水线
# 用法: ./run_pipeline.sh [--skip-fetch]

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR" || exit 1

echo "=== A股TOP200 v2报告流水线 ==="
echo "日期: $(date '+%Y-%m-%d %H:%M:%S')"
echo "工作目录: $WORKDIR"
echo ""

# Step 1: 获取TOP200原始数据
if [ "$1" != "--skip-fetch" ]; then
    echo ">>> Step 1: 获取TOP200行情数据"
    python3 fetch_top200_sina.py || { echo "❌ 获取数据失败"; exit 1; }
    echo "✅ 数据获取完成"
else
    echo ">>> Step 1: 跳过数据获取"
fi

# Step 2: 评分计算（含并发加速）
echo ""
echo ">>> Step 2: 评分计算"
python3 run_step2_fast.py || { echo "❌ 评分计算失败"; exit 1; }
echo "✅ 评分计算完成"

# Step 3: 生成v2 HTML报告
echo ""
echo ">>> Step 3: 生成v2紧凑表格报告"
python3 gen_v2_table.py || { echo "❌ 报告生成失败"; exit 1; }
echo "✅ 报告生成完成"

# 显示最新报告
LATEST_JSON=$(ls -t top200_scored_*.json 2>/dev/null | head -1)
LATEST_HTML=$(ls -t top200_report_*_v2.html 2>/dev/null | head -1)
echo ""
echo "=== 完成 ==="
echo "📊 数据: $LATEST_JSON"
echo "📄 报告: $LATEST_HTML"
