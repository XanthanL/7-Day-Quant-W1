import backtrader as bt
import pandas as pd

# 移除不再需要的导入
# import datetime  # 导入日期时间模块
# import os.path  # 导入路径管理模块
# import sys  # 导入系统模块

# 从新的包路径导入回测运行函数
from src.backtesting.core import run_backtest

# 创建一个 RSI 策略
class RSIStrategy(bt.Strategy):
    # 策略参数
    params = (
        ('period', 14),  # RSI 周期
        ('low_threshold', 30),  # RSI 低阈值 (超卖)
        ('high_threshold', 70), # RSI 高阈值 (超买)
    )

    def __init__(self):
        # 保存数据源中 'close' 线的引用
        self.dataclose = self.datas[0].close

        # 创建 RSI 指标
        self.rsi = bt.indicators.RSI(self.datas[0].close, period=self.params.period)

        # 跟踪待处理订单
        self.order = None

    def log(self, txt, dt=None):
        ''' 策略的日志函数'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 买入/卖出订单已提交/被券商接受 - 无需操作
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('买入执行, 价格: %.2f, 成本: %.2f, 佣金 %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
            elif order.issell():
                self.log('卖出执行, 价格: %.2f, 成本: %.2f, 佣金 %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('交易利润, 毛利润 %.2f, 净利润 %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # 检查是否有待处理订单... 如果有，则不能发送另一个订单
        if self.order:
            return

        # 如果当前没有持仓
        if not self.position:
            # RSI 小于低阈值 (超卖), 发出买入信号
            if self.rsi[0] < self.params.low_threshold:
                self.log('创建买入订单, %.2f (RSI: %.2f)' % (self.dataclose[0], self.rsi[0]))
                self.order = self.buy()
        # 如果当前有持仓
        else:
            # RSI 大于高阈值 (超买), 发出卖出信号 (清仓)
            if self.rsi[0] > self.params.high_threshold:
                self.log('创建卖出订单, %.2f (RSI: %.2f)' % (self.dataclose[0], self.rsi[0]))
                self.order = self.close()

if __name__ == '__main__':
    # 示例运行 RSIStrategy
    # 确保 'market_data/600519.csv' 存在
    print("--- 运行 RSIStrategy 回测 ---")
    run_backtest(RSIStrategy, datapath='market_data/600519.csv')