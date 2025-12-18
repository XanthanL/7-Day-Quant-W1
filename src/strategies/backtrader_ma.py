from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # 导入日期时间模块
import os.path  # 导入路径管理模块
import sys  # 导入系统模块

# 导入 backtrader 平台
import backtrader as bt
import pandas as pd


# 创建一个策略
class DualMAStrategy(bt.Strategy):
    # 策略参数
    params = (('p_short', 20), ('p_long', 60),)

    def __init__(self):
        # 保存数据源中 'close' 线的引用
        self.dataclose = self.datas[0].close

        # 创建 SMA 指标
        self.sma_short = bt.indicators.SimpleMovingAverage(
            self.datas[0].close, period=self.p.p_short
        )
        self.sma_long = bt.indicators.SimpleMovingAverage(
            self.datas[0].close, period=self.p.p_long
        )

        # 跟踪待处理订单和买入价格/佣金
        self.order = None
        self.buyprice = None
        self.buycomm = None

    def log(self, txt, dt=None):
        ''' 策略的日志函数'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 买入/卖出订单已提交/被券商接受 - 无需操作
            return

        # 检查订单是否已完成
        # 注意: 如果资金不足，券商可能会拒绝订单
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    '买入执行, 价格: %.2f, 成本: %.2f, 佣金 %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log('卖出执行, 价格: %.2f, 成本: %.2f, 佣金 %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('交易利润, 毛利润 %.2f, 净利润 %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # 简单记录数据系列的收盘价
        # self.log('收盘价, %.2f' % self.dataclose[0])

        # 检查是否有待处理订单... 如果有，则不能发送另一个订单
        if self.order:
            return

        # 检查是否已在市场中持有头寸
        if not self.position:
            # 尚未在市场中 - 我们可以进场
            # 如果短周期均线向上穿过长周期均线 (金叉)
            if self.sma_short[0] > self.sma_long[0] and self.sma_short[-1] <= self.sma_long[-1]:
                self.log('创建买入订单, %.2f' % self.dataclose[0])
                self.order = self.buy()
        else:
            # 已在市场中持有头寸
            # 如果短周期均线向下穿过长周期均线 (死叉)
            if self.sma_short[0] < self.sma_long[0] and self.sma_short[-1] >= self.sma_long[-1]:
                self.log('创建卖出订单, %.2f' % self.dataclose[0])
                self.order = self.close()
