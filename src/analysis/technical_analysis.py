import pandas as pd
import numpy as np
import mplfinance as mpf # 导入 mplfinance

from src.data.provider import MarketDataProvider

def run_technical_analysis(df, ticker_symbol):

    """

    对给定的股票数据进行技术分析并绘图。

    

    参数:

    df (pd.DataFrame): 包含股票数据的 DataFrame。

    ticker_symbol (str): 股票代码。

    """

    print(f"--- 开始对 {ticker_symbol} 进行技术分析 ---")



    if df is None or df.empty:

        print(f"错误: 传入的 DataFrame 为空，分析无法进行。")

        return



    # 3. 计算移动平均线 (SMA)

    print("\n计算移动平均线...")

    df['SMA_20'] = df['Close'].rolling(window=20).mean()

    df['SMA_60'] = df['Close'].rolling(window=60).mean()

    print("移动平均线计算完成。")



    # 4. 计算收益率

    print("\n计算对数收益率...")

    # 对数收益率：ln(Pt / Pt-1)

    df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))

    print("对数收益率计算完成。")



    # 5. 计算滚动波动率 (Volatility)

    print("\n计算滚动波动率...")

    # 滚动波动率：对数收益率的滚动标准差

    df['Volatility_20'] = df['Log_Ret'].rolling(window=20).std()

    print("滚动波动率计算完成。")



    # 删除所有计算中产生的 NaN 值，确保后续分析数据的完整性

    df.dropna(inplace=True)



    # 6. 打印包含新增列的 DataFrame 尾部5行

    print(f"\n--- {ticker_symbol} 分析结果预览 (尾部5行) ---")

    print(df.tail())



    # 7. 绘图功能

    print("\n--- 正在生成 K 线图 ---")

    # 截取最近 200 个交易日的数据，用于图表清晰

    plot_df = df.tail(200).copy() # 使用 .copy() 避免 SettingWithCopyWarning



    # 准备 addplot 参数，将 SMA_20 和 SMA_60 作为覆盖层绘制在主图上

    apds = [

        mpf.make_addplot(plot_df['SMA_20'], color='blue', panel=0, width=0.7, type='line', secondary_y=False, label='SMA 20'),

        mpf.make_addplot(plot_df['SMA_60'], color='red', panel=0, width=0.7, type='line', secondary_y=False, label='SMA 60'),

    ]



    # 绘制 K 线图

    fig, axlist = mpf.plot(plot_df, 

                         type='candle', 

                         style='yahoo', 

                         volume=True, 

                         addplot=apds, 

                         title=f"{ticker_symbol} Candlestick Chart ({len(plot_df)} Days)", 

                         ylabel='Stock Price', 

                         ylabel_lower='Volume',

                         figscale=1.5, 

                         returnfig=True

                        )

    

    # 尝试在主图上添加图例

    if axlist is not None and len(axlist) > 0 and axlist[0] is not None:

        axlist[0].legend(loc='upper left')



    mpf.show() # 显示图表

    print("\n--- K 线图生成完成 ---")





if __name__ == '__main__':

    # 作为一个模块独立运行时，可以指定一个默认的 ticker

    # 首先加载数据，然后调用分析函数

    ticker = '600519'

    provider = MarketDataProvider(data_dir='./market_data')

    stock_data = provider.load_data(ticker)

    

    if stock_data is not None:

        run_technical_analysis(stock_data.copy(), ticker) # 传递 DataFrame 的副本以避免修改原始数据

    else:

        print(f"无法加载 {ticker} 的数据。")
