import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from src.data.provider import MarketDataProvider

def run_dual_ma_strategy(df, ticker_symbol):
    """
    对给定的股票数据运行向量化的移动平均线交叉交易策略。
    
    参数:
    df (pd.DataFrame): 包含股票数据的 DataFrame。
    ticker_symbol (str): 股票代码。
    """
    print(f"--- 启动向量化策略 (股票代码: {ticker_symbol}) ---")

    if df is None or df.empty:
        print(f"错误: 传入的 DataFrame 为空，策略无法继续。")
        return

    # 3. 计算 20 日和 60 日简单移动平均线 (SMA)
    print("\n计算移动平均线 (SMA_20, SMA_60)...")
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_60'] = df['Close'].rolling(window=60).mean()
    print("移动平均线计算完成。")

    # 4. 生成交易信号 (Signal)
    # 当短期均线 (SMA_20) 上穿长期均线 (SMA_60) 时，产生买入信号 (1)
    # 否则为卖出/观望信号 (0)
    print("正在生成交易信号 (Signal)...")
    df['Signal'] = np.where(df['SMA_20'] > df['SMA_60'], 1, 0)
    
    # 将移动平均线计算和位移产生的 NaN 值填充为 0
    df['Signal'].fillna(0, inplace=True)
    print("交易信号生成完成。")

    # 5. 计算持仓 (Position)
    # 关键点: 持仓是基于“前一天”的信号。
    # 我们假设今天的移动平均线交叉信号决定明天的操作。
    # 因此今天的 Signal 决定明天的 Position。
    # 这通过将 Signal 位移 (shift) 1 天实现。
    # 这样，Position 的值就是前一天的 Signal。
    print("正在计算持仓...")
    df['Position'] = df['Signal'].shift(1)
    
    # 将位移产生的 NaN 填充为 0 (表示初始无持仓)
    df['Position'].fillna(0, inplace=True)
    print("持仓计算完成。")

    # 6. 删除所有计算中产生的 NaN 值，确保后续分析数据的完整性
    # (SMA 计算和位移会产生 NaN)
    df.dropna(inplace=True)

    # 7. 打印 DataFrame 的最后 5 行，包括新列以供预览
    print(f"\n--- {ticker_symbol} 策略结果预览 (最后 5 行) ---")
    print(df[['Close', 'SMA_20', 'SMA_60', 'Signal', 'Position']].tail())
    
    # 打印 Signal 和 Position 的前 10 行，更清晰地展示位移效果
    print(f"\n--- {ticker_symbol} Signal 和 Position 初始预览 (前 10 行) ---")
    print(df[['Close', 'SMA_20', 'SMA_60', 'Signal', 'Position']].head(10))

    # 8. 计算每日收益和累计收益
    print("\n--- 正在计算每日收益和累计收益 ---")
    df['Daily_Return'] = df['Close'].pct_change()
    
    # 策略每日收益: Position * Daily_Return (Position 为 1 表示做多，0 表示空仓)
    df['Strategy_Daily_Return'] = df['Position'] * df['Daily_Return']
    
    # 计算累计收益
    # 策略收益
    df['Cumulative_Strategy_Return'] = (1 + df['Strategy_Daily_Return']).cumprod()
    # 买入并持有基准收益
    df['Cumulative_Buy_Hold_Return'] = (1 + df['Daily_Return']).cumprod()
    
    # 将累计收益的第一个 NaN 值填充为 1 作为起始点
    df['Cumulative_Strategy_Return'].fillna(1, inplace=True)
    df['Cumulative_Buy_Hold_Return'].fillna(1, inplace=True)
    
    print("每日收益和累计收益计算完成。")

    # 9. 绘图功能
    print("\n--- 正在生成 K 线图和策略信号图 ---")
    # 为了图表清晰，截取最近 N 个交易日的数据
    plot_df = df.tail(200).copy() # 使用 .copy() 避免 SettingWithCopyWarning

    # 准备 addplot 参数，将 SMA_20 和 SMA_60 作为覆盖层绘制在主图上
    apds = [
        mpf.make_addplot(plot_df['SMA_20'], color='blue', panel=0, width=0.7, type='line', secondary_y=False, label='SMA 20'),
        mpf.make_addplot(plot_df['SMA_60'], color='red', panel=0, width=0.7, type='line', secondary_y=False, label='SMA 60'),
    ]

    # 添加买入/卖出信号
    # 创建 'Buy' 和 'Sell' 信号 Series，与 plot_df 对齐
    buy_signals_plot = pd.Series(np.nan, index=plot_df.index)
    sell_signals_plot = pd.Series(np.nan, index=plot_df.index)

    # 找到买入信号日期: Signal 从 0 变为 1
    buy_dates = plot_df[(plot_df['Signal'] == 1) & (plot_df['Signal'].shift(1) == 0)].index
    # 找到卖出信号日期: Signal 从 1 变为 0
    sell_dates = plot_df[(plot_df['Signal'] == 0) & (plot_df['Signal'].shift(1) == 1)].index
    
    # 在相应的日期上设置收盘价
    buy_signals_plot.loc[buy_dates] = plot_df.loc[buy_dates, 'Close']
    sell_signals_plot.loc[sell_dates] = plot_df.loc[sell_dates, 'Close']

    if not buy_signals_plot.dropna().empty:
        apds.append(
            mpf.make_addplot(
                buy_signals_plot,
                type='scatter',
                marker='^',
                markersize=100,
                color='green',
                panel=0,
                label='Buy Signal'
            )
        )
    if not sell_signals_plot.dropna().empty:
        apds.append(
            mpf.make_addplot(
                sell_signals_plot,
                type='scatter',
                marker='v',
                markersize=100,
                color='red',
                panel=0,
                label='Sell Signal'
            )
        )

    # 将累计收益图添加到新面板
    apds.append(
        mpf.make_addplot(plot_df['Cumulative_Strategy_Return'], color='purple', panel=2, width=1.0, type='line', secondary_y=False, label='Strategy Return'),
    )
    apds.append(
        mpf.make_addplot(plot_df['Cumulative_Buy_Hold_Return'], color='orange', panel=2, width=1.0, type='line', secondary_y=False, label='Buy & Hold Return'),
    )

    # 绘制 K 线图
    fig, axlist = mpf.plot(plot_df, 
                         type='candle', 
                         style='yahoo', 
                         volume=True, 
                         addplot=apds, 
                         title=f"{ticker_symbol} (Kweichow Moutai) MA Crossover Strategy ({len(plot_df)} Days)", 
                         ylabel='Stock Price', 
                         ylabel_lower='Volume',
                         figscale=1.5, 
                         returnfig=True,
                         panel_ratios=(3, 1, 1), # 调整面板比例以适应新面板
                        )
    
    # 为主面板和收益新面板添加图例
    if axlist is not None:
        axlist[0].legend(loc='upper left') # 主图图例
        
        if len(axlist) > 2 and axlist[2] is not None:
            handles, labels = axlist[2].get_legend_handles_labels()
            if handles and labels:
                axlist[2].legend(handles, labels, loc='upper left')
            axlist[2].set_ylabel('Cumulative Return')

    plt.show() # 显示图表
    print("\n--- K 线图和策略信号图生成完成 ---")


if __name__ == '__main__':
    # 作为一个模块独立运行时，可以指定一个默认的 ticker
    ticker = '600519'
    provider = MarketDataProvider(data_dir='./market_data')
    stock_data = provider.load_data(ticker)
    
    if stock_data is not None:
        run_dual_ma_strategy(stock_data.copy(), ticker) # 传递 DataFrame 的副本以避免修改原始数据
    else:
        print(f"无法加载 {ticker} 的数据。")
