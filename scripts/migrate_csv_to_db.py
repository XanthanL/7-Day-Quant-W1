import os
import sys
import pandas as pd
import re
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import DBManager from the new database module
from src.data.database import DBManager
# Import MarketDataProvider from the existing data provider module
from src.data.provider import MarketDataProvider

def migrate_csv_to_db(market_data_dir: str = 'market_data'):
    """
    Reads all CSV files from a specified directory and migrates them
    into the SQLite database using DBManager.

    :param market_data_dir: The directory where CSV stock data files are stored.
    """
    db_manager = DBManager()
    db_manager.init_db() # Ensure tables are created

    data_provider = MarketDataProvider(data_dir=market_data_dir)

    print(f"Starting CSV migration from '{market_data_dir}' to database '{db_manager.engine.url.database}'...")
    
    migrated_count = 0
    for filename in os.listdir(market_data_dir):
        if filename.endswith('.csv'):
            # Extract ticker symbol from filename (e.g., '600519.csv' -> '600519')
            ticker = os.path.splitext(filename)[0]
            
            print(f"Processing {filename} (Ticker: {ticker})...")
            
            # Load data using the existing MarketDataProvider (which reads CSV)
            df = data_provider.load_data(ticker)
            
            if df is not None and not df.empty:
                # Save data to the database using DBManager
                # Ensure the DataFrame has the expected columns for StockDaily model
                # The MarketDataProvider.load_data already returns df with Date as index, and OHLCV columns.
                db_manager.save_daily_data(df, ticker)
                migrated_count += 1
            else:
                print(f"Warning: Could not load data or data is empty for {filename}. Skipping.")
    
    print(f"\nMigration complete. Migrated data for {migrated_count} tickers.")

if __name__ == '__main__':
    # You can specify your market_data directory here, if it's not 'market_data'
    migrate_csv_to_db(market_data_dir='market_data')
