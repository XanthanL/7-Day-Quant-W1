import pandas as pd
import numpy as np # 导入 numpy，尽管当前 RSI 计算中未使用，但为将来扩展考虑

def calculate_rsi(df, period=14):
    """
    计算相对强弱指数 (RSI)。
    通常 RSI 使用 Wilder's smoothing (一种指数加权移动平均)。
    
    参数:
    df (pd.DataFrame): 包含 'Close' 列的 DataFrame。
    period (int): RSI 计算周期。
    
    返回:
    pd.Series: 包含 RSI 值的 Series。
    """
    if 'Close' not in df.columns:
        return None

    close_prices = df['Close']
    delta = close_prices.diff()

    # 分离上涨和下跌
    up = delta.copy()
    down = delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    down = abs(down)

    # 使用 pandas.ewm (指数加权移动平均) 来模拟 Wilder's smoothing
    # com 参数对应于 backtrader 中的 period-1
    avg_gain = up.ewm(com=period - 1, adjust=False, min_periods=period).mean()
    avg_loss = down.ewm(com=period - 1, adjust=False, min_periods=period).mean()

    # 计算相对强度 (RS)
    rs = avg_gain / avg_loss
    
    # 计算 RSI
    rsi = 100 - (100 / (1 + rs))
    return rsi
