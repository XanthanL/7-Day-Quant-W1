# 导入所需库
import akshare as ak
import pandas as pd
import os
from pathlib import Path

class MarketDataProvider:
    """
    一个用于下载、存储和加载中国A股市场数据的提供者类。
    数据源已从 yfinance 更换为 akshare。
    """

    def __init__(self, data_dir: str = './data'):
        """
        初始化 MarketDataProvider。

        :param data_dir: 用于存储/读取 CSV 文件的目录路径。
                         默认为 './data'。如果目录不存在，将自动创建。
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            os.makedirs(self.data_dir)
            print(f"已创建数据目录: {self.data_dir.resolve()}")

    def download_data(self, ticker: str, start_date: str, end_date: str):
        """
        从 akshare 下载指定A股的后复权日线数据并将其保存为 CSV 文件。

        :param ticker: 股票代码 (例如, '600519').
        :param start_date: 数据下载的开始日期 (格式: 'YYYY-MM-DD').
        :param end_date: 数据下载的结束日期 (格式: 'YYYY-MM-DD').
        """
        print(f"开始使用 akshare 下载 {ticker} 从 {start_date} 到 {end_date} 的数据...")

        try:
            # akshare 的日期格式为 'YYYYMMDD'，需要转换
            start_date_ak = start_date.replace('-', '')
            end_date_ak = end_date.replace('-', '')

            # 使用 akshare 下载后复权 ('hfq') 的日线数据
            data = ak.stock_zh_a_hist(symbol=ticker, 
                                      period="daily", 
                                      start_date=start_date_ak, 
                                      end_date=end_date_ak, 
                                      adjust="hfq")

            if data.empty:
                print(f"警告: 未能下载 {ticker} 的数据。请检查代码或日期范围。")
                return

            # --- 数据清洗和列名统一 ---
            # 将 akshare 的中文列名映射为我们项目使用的英文列名
            rename_map = {
                '日期': 'Date',
                '开盘': 'Open',
                '最高': 'High',
                '最低': 'Low',
                '收盘': 'Close',
                '成交量': 'Volume'
                # '成交额', '振幅', '涨跌幅', '涨跌额', '换手率' 等列我们暂时不用
            }
            data.rename(columns=rename_map, inplace=True)

            # 将 'Date' 列转换为 datetime 对象并设为索引
            data['Date'] = pd.to_datetime(data['Date'])
            data.set_index('Date', inplace=True)
            
            # 为了兼容性，我们可以创建一个 'Adj Close' 列，这里直接使用复权后的 'Close'
            data['Adj Close'] = data['Close']
            
            # 筛选我们需要的列
            required_columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            data = data[required_columns]

            # 定义要保存的文件路径
            file_path = self.data_dir / f"{ticker}.csv"

            # 将 DataFrame 保存为 CSV 文件
            data.to_csv(file_path)

            print(f"成功: {ticker} 的数据已保存至 {file_path.resolve()}")

        except Exception as e:
            print(f"错误: 下载或保存 {ticker} 数据时发生错误: {e}")

    def load_data(self, ticker: str) -> pd.DataFrame or None:
        """
        从本地 CSV 文件加载指定股票的数据。(此方法无需更改)

        :param ticker: 要加载的股票代码。
        :return: 一个包含股票数据的 pandas DataFrame，其中 'Date' 列是索引。
                 如果文件不存在，则返回 None。
        """
        file_path = self.data_dir / f"{ticker}.csv"

        if not file_path.exists():
            print(f"错误: 找不到 {ticker} 的数据文件 at {file_path.resolve()}。请先调用 download_data()。")
            return None

        try:
            data = pd.read_csv(file_path, index_col='Date', parse_dates=True)
            print(f"成功: 已从 {file_path.resolve()} 加载 {ticker} 的数据。")
            return data
        
        except Exception as e:
            print(f"错误: 加载 {ticker} 数据时发生错误: {e}")
            return None

# --- 脚本执行入口 ---
if __name__ == '__main__':
    # 创建 MarketDataProvider 实例
    provider = MarketDataProvider(data_dir='./market_data')

    # 定义要下载的A股股票和时间范围
    ticker_symbol = '600519'  # 贵州茅台
    start_dt = '2020-01-01'
    end_dt = '2023-12-31'

    # 下载数据
    provider.download_data(ticker=ticker_symbol, start_date=start_dt, end_date=end_dt)

    # 加载数据并验证
    print("\n--- 加载数据 ---")
    stock_data = provider.load_data(ticker=ticker_symbol)

    if stock_data is not None:
        print(f"\n{ticker_symbol} 数据预览:")
        print(stock_data.head())
        print("\n数据信息:")
        stock_data.info()

