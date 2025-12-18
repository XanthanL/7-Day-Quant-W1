import akshare as ak
import pandas as pd
import time
from datetime import datetime, timedelta

from src.utils.indicators import calculate_rsi # 从新的路径导入 calculate_rsi

# 定义策略逻辑函数
def check_signal(df, low_threshold=30, high_threshold=70):
    """
    根据 RSI 指标检查交易信号。
    
    参数:
    df (pd.DataFrame): 包含股票数据的 DataFrame。
    low_threshold (int): RSI 超卖阈值。
    high_threshold (int): RSI 超买阈值。
    
    返回:
    str: 'BUY', 'SELL' 或 'HOLD'。
    """
    rsi_values = calculate_rsi(df)
    if rsi_values is None or rsi_values.empty:
        return 'HOLD', None
    
    current_rsi = rsi_values.iloc[-1]

    if current_rsi < low_threshold:
        return 'BUY', current_rsi
    elif current_rsi > high_threshold:
        return 'SELL', current_rsi
    else:
        return 'HOLD', current_rsi

def main(ticker='600519'):
    """
    主监控循环。
    
    参数:
    ticker (str): 要监控的股票代码。
    """
    print(f"--- 启动模拟实盘监控脚本 (股票代码: {ticker}) ---")
    rsi_period = 14
    rsi_low = 30
    rsi_high = 70
    data_lookback_days = 100 # 获取最近 N 天的数据用于计算指标

    while True:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{current_time}] 正在获取 {ticker} 的数据并检查信号...")

        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=data_lookback_days)).strftime('%Y%m%d')

            # 使用 akshare 获取历史数据，并进行后复权 (hfq)
            # ak.stock_zh_a_hist 的 symbol 参数需要 '股票代码'
            df_hist = ak.stock_zh_a_hist(symbol=ticker, 
                                         period="daily", 
                                         start_date=start_date, 
                                         end_date=end_date, 
                                         adjust="hfq")
            
            if df_hist.empty:
                print(f"警告: 未能获取 {ticker} 的数据。跳过本次检查。\n")
                time.sleep(60)
                continue

            # 数据清洗和列名统一
            df_hist.rename(columns={
                '日期': 'Date', '开盘': 'Open', '最高': 'High',
                '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'
            }, inplace=True)
            df_hist['Date'] = pd.to_datetime(df_hist['Date'])
            df_hist.set_index('Date', inplace=True)
            df_hist.sort_index(inplace=True) # 确保按日期排序

            latest_close = df_hist['Close'].iloc[-1]
            # 传递 rsi_period 给 calculate_rsi 函数
            signal, current_rsi = check_signal(df_hist, rsi_low, rsi_high)

            print(f"  最新收盘价: {latest_close:.2f}")
            if current_rsi is not None:
                print(f"  当前 RSI({rsi_period}): {current_rsi:.2f}")
            else:
                print(f"  RSI 无法计算 (数据不足)")

            if signal == 'BUY':
                print("  *** BUY SIGNAL TRIGGERED ***")
            elif signal == 'SELL':
                print("  *** SELL SIGNAL TRIGGERED ***")
            else:
                print("  信号: HOLD")

        except Exception as e:
            print(f"发生错误: {e}")
            print("  请检查网络连接或 akshare 数据源是否可用。\n")
        
        print(f"  下一次检查时间: {(datetime.now() + timedelta(seconds=60)).strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(60) # 每 60 秒检查一次

if __name__ == '__main__':
    # 作为一个模块独立运行时，可以指定一个默认的 ticker
    main(ticker='600519')
