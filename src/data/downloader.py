import akshare as ak
import pandas as pd
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import time
import random
from typing import Optional

from src.data.database import DBManager

class StockDownloader:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        # Initialize DBManager to ensure tables exist
        self.db_manager.init_db()
        print("StockDownloader initialized.")

    def get_all_a_stock_symbols(self, limit: Optional[int] = None) -> list[str]:
        """
        使用 akshare 获取当前 A 股所有股票代码。
        :param limit: 如果设置，只返回前 limit 只股票代码，用于调试。
        :return: 股票代码列表。
        """
        print("Fetching all A-share stock symbols from Akshare...")
        try:
            stock_list_df = ak.stock_zh_a_spot_em()
            symbols = stock_list_df['代码'].tolist()
            if limit:
                symbols = symbols[:limit]
            print(f"Found {len(symbols)} A-share stock symbols.")
            return symbols
        except Exception as e:
            print(f"Error fetching stock symbols: {e}")
            return []

    def update_single_stock(self, symbol: str) -> dict:
        """
        更新单个股票的历史日线数据。
        增量更新逻辑：从数据库中该股票的最新日期+1天开始下载。
        如果数据库中无数据，则从 '20200101' 开始下载。
        
        :param symbol: 股票代码。
        :return: 包含更新结果的字典。
        """
        try:
            latest_date_in_db = self.db_manager.get_latest_date(symbol)
            
            start_date_download: date
            if latest_date_in_db:
                # Start from the day after the latest date in DB
                start_date_download = latest_date_in_db + timedelta(days=1)
            else:
                # No data in DB, start from a historical base date
                start_date_download = date(2020, 1, 1) # Default start date if no data

            end_date_download = datetime.now().date() # Current date
            
            # If start_date_download is in the future, or today, no need to download
            if start_date_download > end_date_download:
                return {'symbol': symbol, 'status': 'SKIPPED', 'message': 'Already up to date or future date.'}

            # Convert dates to 'YYYYMMDD' string format for akshare
            start_date_str = start_date_download.strftime('%Y%m%d')
            end_date_str = end_date_download.strftime('%Y%m%d')

            # Add rate limiting to prevent IP ban
            time.sleep(random.uniform(0.1, 0.5))

            # Download data using akshare
            data = ak.stock_zh_a_hist(symbol=symbol, 
                                      period="daily", 
                                      start_date=start_date_str, 
                                      end_date=end_date_str, 
                                      adjust="hfq") # 后复权

            if data.empty:
                return {'symbol': symbol, 'status': 'NO_NEW_DATA', 'message': f'No new data from {start_date_str} to {end_date_str}.'}

            # Data cleaning and column renaming to match StockDaily model
            data.rename(columns={
                'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume',
                '日期': 'Date', '开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'
            }, inplace=True)
            
            # Filter out any data points already in the database
            # This is a double check, as start_date_download should already handle it.
            # But in case Akshare returns redundant data, this ensures proper upsert behavior.
            if latest_date_in_db:
                 data = data[data.index.date > latest_date_in_db]

            if data.empty:
                 return {'symbol': symbol, 'status': 'ALREADY_EXIST', 'message': 'Data already exists in DB.'}

            self.db_manager.save_daily_data(data, symbol)
            return {'symbol': symbol, 'status': 'SUCCESS', 'records_saved': len(data)}

        except Exception as e:
            return {'symbol': symbol, 'status': 'FAILED', 'error': str(e)}

    def download_index_data(self, symbol: str = 'sh000300') -> dict:
        """
        下载指定指数的历史日线数据。
        
        :param symbol: 指数代码 (例如: 'sh000300' 代表沪深300)。
        :return: 包含下载结果的字典。
        """
        print(f"Downloading index data for {symbol}...")
        try:
            latest_date_in_db = self.db_manager.get_latest_date(symbol)
            
            start_date_download: date
            if latest_date_in_db:
                start_date_download = latest_date_in_db + timedelta(days=1)
            else:
                start_date_download = date(2005, 1, 1) # Indices usually have longer history

            end_date_download = datetime.now().date()
            
            if start_date_download > end_date_download:
                return {'symbol': symbol, 'status': 'SKIPPED', 'message': 'Index data already up to date.'}

            start_date_str = start_date_download.strftime('%Y%m%d')
            end_date_str = end_date_download.strftime('%Y%m%d')

            data = ak.stock_zh_index_daily(symbol=symbol)

            if data.empty:
                return {'symbol': symbol, 'status': 'NO_NEW_DATA', 'message': 'No data found for index.'}

            # Data cleaning and column renaming to match StockDaily model
            data.rename(columns={
                'date': 'Date', 'open': 'Open',
                'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
            }, inplace=True)
            data['Date'] = pd.to_datetime(data['Date'])
            data.set_index('Date', inplace=True)
            
            # Filter data to save only new records
            if latest_date_in_db:
                 data = data[data.index.date > latest_date_in_db]

            if data.empty:
                 return {'symbol': symbol, 'status': 'ALREADY_EXIST', 'message': 'Index data already exists in DB.'}

            self.db_manager.save_daily_data(data, symbol)
            return {'symbol': symbol, 'status': 'SUCCESS', 'records_saved': len(data)}

        except Exception as e:
            return {'symbol': symbol, 'status': 'FAILED', 'error': str(e)}

    def download_all_stocks(self, max_workers: int = 5, limit: Optional[int] = None):
        """
        并发下载所有 A 股股票的历史日线数据。
        
        :param max_workers: 并发工作线程数。
        :param limit: 如果设置，只下载前 limit 只股票，用于调试。
        """
        symbols = self.get_all_a_stock_symbols(limit=limit)
        if not symbols:
            print("No symbols to download.")
            return

        print(f"Starting concurrent download for {len(symbols)} stocks with {max_workers} workers...")
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map update_single_stock to all symbols and display progress with tqdm
            futures = [executor.submit(self.update_single_stock, symbol) for symbol in symbols]
            for future in tqdm(futures, total=len(symbols), desc="Downloading stock data"):
                results.append(future.result())

        print("\n--- Download Summary ---")
        success_count = 0
        skipped_count = 0
        no_new_data_count = 0
        failed_count = 0

        for res in results:
            if res['status'] == 'SUCCESS':
                success_count += 1
                # print(f"  {res['symbol']}: SUCCESS, saved {res['records_saved']} records.")
            elif res['status'] == 'SKIPPED':
                skipped_count += 1
                # print(f"  {res['symbol']}: SKIPPED, {res['message']}")
            elif res['status'] == 'NO_NEW_DATA':
                no_new_data_count += 1
                # print(f"  {res['symbol']}: NO_NEW_DATA, {res['message']}")
            elif res['status'] == 'ALREADY_EXIST':
                no_new_data_count += 1 # Treat as no new data for summary
                # print(f"  {res['symbol']}: ALREADY_EXIST, {res['message']}")
            elif res['status'] == 'FAILED':
                failed_count += 1
                print(f"  {res['symbol']}: FAILED, Error: {res['error']}")
        
        print(f"Total processed: {len(symbols)}")
        print(f"Successful updates: {success_count}")
        print(f"Skipped (up to date): {skipped_count}")
        print(f"No new data: {no_new_data_count}")
        print(f"Failed updates: {failed_count}")

# For independent testing
if __name__ == '__main__':
    db_manager = DBManager()
    downloader = StockDownloader(db_manager)

    # Example: Download data for a limited number of stocks for testing
    downloader.download_all_stocks(max_workers=3, limit=10) # Test with 10 stocks, 3 workers
    
    # After download, check database status
    print("\nChecking database status after download:")
    status = db_manager.get_status()
    if 'error' not in status:
        print(f"Total records: {status['total_records']}")
        print(f"Distinct symbols: {status['distinct_symbols_count']}")
        for symbol, latest_date in status['latest_trade_dates_per_symbol'].items():
            print(f"  {symbol}: {latest_date}")
    else:
        print(f"Error getting status: {status['error']}")
