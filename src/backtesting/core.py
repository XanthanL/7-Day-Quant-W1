from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # 导入日期时间模块
import os.path  # 导入路径管理模块
import sys  # 导入系统模块

# 导入 backtrader 平台
import backtrader as bt
import pandas as pd

# 从新的包路径导入策略
from src.strategies.backtrader_ma import DualMAStrategy # 从 src.strategies.backtrader_ma 导入 DualMAStrategy

def run_backtest(strategy_class, df, initial_cash=100000.0, commission=0.0005, plot=True):
    """
    运行 backtrader 回测的通用函数。
    
    参数:
    strategy_class: 要回测的策略类。
    df (pd.DataFrame): 包含股票数据的 DataFrame。
    initial_cash (float): 初始资金。
    commission (float): 交易佣金。
    plot (bool): 是否绘制结果图。
    """
    # 创建 Cerebro 实体
    cerebro = bt.Cerebro()

    # 添加策略
    cerebro.addstrategy(strategy_class)

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
    cerebro.broker.setcommission(commission=commission)

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    # 打印初始资金状况
    print('初始投资组合价值: %.2f' % cerebro.broker.getvalue())

    # 运行所有回测
    results = cerebro.run()
    strat = results[0] # 获取策略结果

    # 打印最终结果
    print('最终投资组合价值: %.2f' % cerebro.broker.getvalue())

    # 打印分析器结果
    print('\n分析器结果:')
    print('夏普比率:', strat.analyzers.sharpe.get_analysis()['sharperatio'])
    print('最大回撤:', strat.analyzers.drawdown.get_analysis()['max']['drawdown'])
    print('最大回撤百分比: %.2f%% ' % (strat.analyzers.drawdown.get_analysis().max.drawdown))

    # 绘制结果
    if plot:
        cerebro.plot()

# Removed if __name__ == '__main__': block as it relied on MarketDataProvider
