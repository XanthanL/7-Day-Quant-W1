from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import os.path
import sys

import backtrader as bt
import pandas as pd

# 导入 DualMAStrategy
from src.strategies.backtrader_ma import DualMAStrategy 

def run_optimization(df, initial_cash=100000.0, commission=0.0005, maxcpus=1):
    """
    运行 DualMAStrategy 参数优化的通用函数。
    
    参数:
    df (pd.DataFrame): 包含股票数据的 DataFrame。
    initial_cash (float): 初始资金。
    commission (float): 交易佣金。
    maxcpus (int): 优化运行时使用的 CPU 核心数。
    """
    # 创建 Cerebro 实体
    cerebro = bt.Cerebro()

    # 创建数据 Feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,  # 使用索引作为日期时间
        open='Open',
        high='High',
        low='Low',
        close='Close',
        volume='Volume',
        openinterest=-1
    )

    # 将数据 Feed 添加到 Cerebro
    cerebro.adddata(data)

    # 设置初始资金
    cerebro.broker.setcash(initial_cash)

    # 设置佣金
    cerebro.broker.setcommission(commission=0.0005)

    # 添加策略进行优化
    # p_short 从 5 到 20 (步长 5): 即 5, 10, 15, 20
    # p_long 从 30 到 60 (步长 10): 即 30, 40, 50, 60
    cerebro.optstrategy(
        DualMAStrategy,
        p_short=range(5, 21, 5),  # 21 是为了包含 20
        p_long=range(30, 61, 10)   # 61 是为了包含 60
    )

    # 添加分析器 (这些分析器将应用于每个优化的策略实例)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade')

    # 运行所有回测
    print("开始运行参数优化...")
    optimized_runs = cerebro.run(maxcpus=maxcpus) # 使用传入的 maxcpus 参数
    print("参数优化完成。")

    # 提取并打印结果
    best_params = {}
    best_value = 0.0

    print("\n--- 优化结果 ---")
    for run in optimized_runs:
        for strategy_instance in run:
            p_short = strategy_instance.p.p_short
            p_long = strategy_instance.p.p_long
            
            trade_analysis = strategy_instance.analyzers.trade.get_analysis()
            
            initial_cash_for_run = cerebro.broker.startingcash # 获取初始资金 (每次运行是独立的)
            total_pnl = trade_analysis.pnl.net.total if trade_analysis.pnl.net.total is not None else 0.0

            current_value = initial_cash_for_run + total_pnl
            
            print(f"参数: p_short={p_short}, p_long={p_long}, 最终资金: {current_value:.2f}")

            if current_value > best_value:
                best_value = current_value
                best_params = {'p_short': p_short, 'p_long': p_long}
    
    print("\n--- 最佳优化结果 ---")
    print(f"最佳参数: {best_params}")
    print(f"最高最终资金: {best_value:.2f}")

    return best_params, best_value

if __name__ == '__main__':
    # 示例运行优化
    from src.data.provider import MarketDataProvider
    
    ticker = '600519'
    provider = MarketDataProvider(data_dir='market_data')
    stock_data = provider.load_data(ticker)

    if stock_data is not None:
        print(f"--- 运行 DualMAStrategy 参数优化 (股票代码: {ticker}) ---")
        best_params, best_value = run_optimization(df=stock_data.copy(), maxcpus=1)
        print(f"\n主程序中获取的最佳参数: {best_params}")
        print(f"主程序中获取的最高最终资金: {best_value:.2f}")
    else:
        print(f"无法加载 {ticker} 的数据。")