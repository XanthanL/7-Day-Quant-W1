import pandas as pd
from datetime import date, datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Float, Date, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Define the path for the SQLite database
# The database file will be created in the project root by default
DB_PATH = 'quant.db'

# Base class for declarative models
Base = declarative_base()

class StockDaily(Base):
    """
    SQLAlchemy model for daily stock data.
    """
    __tablename__ = 'stock_daily'

    symbol = Column(String, primary_key=True, index=True)
    trade_date = Column(Date, primary_key=True, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    def __repr__(self):
        return (f"<StockDaily(symbol='{self.symbol}', trade_date='{self.trade_date}', "
                f"close={self.close})")

class DBManager:
    """
    Manages database connections and operations for stock daily data.
    """
    def __init__(self, db_path: str = DB_PATH):
        """
        Initializes the database engine and session factory.

        :param db_path: Path to the SQLite database file.
        """
        # SQLAlchemy 2.0 style engine creation
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,  # Set to True for verbose SQLAlchemy logging
            connect_args={"check_same_thread": False} # Required for SQLite with multiple threads (e.g., if using FastAPI/Flask)
        )
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        print(f"Database manager initialized for {db_path}")

    def init_db(self):
        """
        Creates all defined tables in the database.
        """
        Base.metadata.create_all(self.engine)
        print("Database tables initialized.")

    def save_daily_data(self, df: pd.DataFrame, symbol: str):
        """
        Saves daily stock data from a DataFrame into the database.
        Handles primary key conflicts by updating existing records (upsert).

        :param df: DataFrame containing stock data with 'Date' as index and 'Open', 'High', 'Low', 'Close', 'Volume' columns.
        :param symbol: The stock symbol (e.g., '600519').
        """
        if df.empty:
            print(f"Warning: DataFrame for {symbol} is empty, no data to save.")
            return

        session = self.Session()
        try:
            for index, row in df.iterrows():
                stock_daily_data = StockDaily(
                    symbol=symbol,
                    trade_date=index.date(),  # Convert pandas timestamp to date object
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row['Volume']
                )
                session.merge(stock_daily_data) # Use merge for upsert functionality
            session.commit()
            print(f"Successfully saved/updated {len(df)} records for {symbol}.")
        except Exception as e:
            session.rollback()
            print(f"Error saving data for {symbol}: {e}")
        finally:
            session.close()

    def get_daily_data(self, symbol: str, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """
        Retrieves daily stock data for a given symbol from the database.

        :param symbol: The stock symbol.
        :param start_date: Optional start date for data retrieval (inclusive).
        :param end_date: Optional end date for data retrieval (inclusive).
        :return: A pandas DataFrame with 'trade_date' as index, or an empty DataFrame if no data found.
        """
        session = self.Session()
        try:
            query = session.query(StockDaily).filter(StockDaily.symbol == symbol)

            if start_date:
                query = query.filter(StockDaily.trade_date >= start_date)
            if end_date:
                query = query.filter(StockDaily.trade_date <= end_date)

            records = query.order_by(StockDaily.trade_date).all()
            
            if not records:
                print(f"No data found for {symbol} with the given criteria.")
                return pd.DataFrame()

            # Convert records to a list of dictionaries
            data = [
                {
                    'Date': r.trade_date,
                    'Open': r.open,
                    'High': r.high,
                    'Low': r.low,
                    'Close': r.close,
                    'Volume': r.volume
                }
                for r in records
            ]
            
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date']) # Ensure 'Date' is datetime
            df.set_index('Date', inplace=True)
            return df
        except Exception as e:
            print(f"Error retrieving data for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            session.close()

    def get_latest_date(self, symbol: str) -> Optional[date]:
        """
        Retrieves the latest trade date for a given stock symbol from the database.

        :param symbol: The stock symbol.
        :return: The latest trade date (datetime.date) or None if no data found.
        """
        session = self.Session()
        try:
            # Query the latest trade_date for the given symbol
            latest_record = session.query(StockDaily.trade_date).filter(StockDaily.symbol == symbol).order_by(StockDaily.trade_date.desc()).first()
            if latest_record:
                return latest_record[0] # first() returns a tuple, get the first element
            return None
        except Exception as e:
            print(f"Error getting latest date for {symbol}: {e}")
            return None
        finally:
            session.close()

    def get_status(self) -> dict:
        """
        Returns a dictionary with database status information:
        - Total number of records.
        - Number of distinct stock symbols.
        - Latest trade date for each symbol.
        """
        session = self.Session()
        status = {}
        try:
            # 1. Total number of records
            total_records = session.query(StockDaily).count()
            status['total_records'] = total_records

            # 2. Number of distinct stock symbols
            distinct_symbols = session.query(StockDaily.symbol).distinct().count()
            status['distinct_symbols_count'] = distinct_symbols

            # 3. Latest trade date for each symbol
            latest_dates_query = session.query(
                StockDaily.symbol,
                func.max(StockDaily.trade_date).label('latest_date')
            ).group_by(StockDaily.symbol).all()

            latest_dates = {row.symbol: row.latest_date for row in latest_dates_query}
            status['latest_trade_dates_per_symbol'] = latest_dates

        except Exception as e:
            print(f"Error getting database status: {e}")
            status['error'] = str(e)
        finally:
            session.close()
        return status

    def load_panel_data(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Loads daily stock data for all symbols within a specified date range,
        returning a pandas DataFrame with MultiIndex (trade_date, symbol).

        :param start_date: The start date for data retrieval (inclusive).
        :param end_date: The end date for data retrieval (inclusive).
        :return: A pandas DataFrame with MultiIndex (trade_date, symbol),
                 or an empty DataFrame if no data found.
        """
        session = self.Session()
        try:
            query = session.query(StockDaily).filter(
                StockDaily.trade_date >= start_date,
                StockDaily.trade_date <= end_date
            ).order_by(StockDaily.trade_date, StockDaily.symbol).all()

            if not query:
                print(f"No panel data found between {start_date} and {end_date}.")
                return pd.DataFrame()

            data = [
                {
                    'trade_date': r.trade_date,
                    'symbol': r.symbol,
                    'open': r.open,
                    'high': r.high,
                    'low': r.low,
                    'close': r.close,
                    'volume': r.volume
                }
                for r in query
            ]

            df = pd.DataFrame(data)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index(['trade_date', 'symbol'], inplace=True)
            return df

        except Exception as e:
            print(f"Error loading panel data: {e}")
            return pd.DataFrame()
        finally:
            session.close()


# Example usage (for testing this module independently)
if __name__ == '__main__':
    db_manager = DBManager()
    db_manager.init_db()

    # --- Test save_daily_data ---
    print("\n--- Testing save_daily_data ---")
    # Create some dummy data
    dummy_data_1 = pd.DataFrame({
        'Open': [100.0, 101.0, 102.0],
        'High': [102.0, 103.0, 104.0],
        'Low': [99.0, 100.0, 101.0],
        'Close': [101.0, 102.0, 103.0],
        'Volume': [1000.0, 1100.0, 1200.0]
    }, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
    db_manager.save_daily_data(dummy_data_1, 'TEST01')

    dummy_data_2 = pd.DataFrame({
        'Open': [200.0, 201.0, 202.0],
        'High': [202.0, 203.0, 204.0],
        'Low': [199.0, 200.0, 201.0],
        'Close': [201.0, 202.0, 203.0],
        'Volume': [2000.0, 2100.0, 2200.0]
    }, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
    db_manager.save_daily_data(dummy_data_2, 'TEST02')

    # Test upsert: update an existing record for TEST01
    dummy_data_update = pd.DataFrame({
        'Open': [100.5],
        'High': [102.5],
        'Low': [99.5],
        'Close': [101.5],
        'Volume': [1050.0]
    }, index=pd.to_datetime(['2023-01-01']))
    db_manager.save_daily_data(dummy_data_update, 'TEST01')

    # --- Test get_daily_data ---
    print("\n--- Testing get_daily_data ---")
    retrieved_df_1 = db_manager.get_daily_data('TEST01')
    print("\nRetrieved data for TEST01 (all):")
    print(retrieved_df_1)

    retrieved_df_2 = db_manager.get_daily_data('TEST02', start_date=date(2023, 1, 2))
    print("\nRetrieved data for TEST02 (from 2023-01-02):")
    print(retrieved_df_2)

    retrieved_df_none = db_manager.get_daily_data('NONEXISTENT')
    print("\nRetrieved data for NONEXISTENT:")
    print(retrieved_df_none)

    # --- Test get_status ---
    print("\n--- Testing get_status ---")
    status_info = db_manager.get_status()
    print("\nDatabase Status:")
    for key, value in status_info.items():
        if key == 'latest_trade_dates_per_symbol':
            print(f"  Latest trade dates per symbol:")
            for symbol, dt in value.items():
                print(f"    {symbol}: {dt}")
        else:
            print(f"  {key.replace('_', ' ').capitalize()}: {value}")

    # Clean up the test database file
    # os.remove(DB_PATH) # Uncomment to remove the test db after execution
