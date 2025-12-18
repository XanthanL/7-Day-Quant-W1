import pandas as pd
from datetime import date, timedelta
from src.data.database import DBManager # Assuming DBManager is needed for data access

class AlphaModel:
    """
    Implements a multi-factor stock selection model based on Momentum and Volatility.
    """

    def __init__(self, db_manager: DBManager):
        """
        Initializes the AlphaModel with a DBManager instance for data access.

        :param db_manager: An instance of DBManager.
        """
        self.db_manager = db_manager

    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Momentum_20 and Volatility_20 factors.

        :param df: A pandas DataFrame with MultiIndex (trade_date, symbol) and a 'close' column.
        :return: DataFrame with 'Momentum_20' and 'Volatility_20' factor columns.
        """
        if df.empty:
            return pd.DataFrame()

        # Ensure index is sorted for rolling calculations
        df = df.sort_index()

        # Calculate Momentum_20
        # For each symbol, calculate (current close / close 20 days ago) - 1
        # Use `groupby(level='symbol')` to apply calculations within each stock group
        df['Momentum_20'] = df.groupby(level='symbol')['close'].transform(
            lambda x: x.div(x.shift(20)) - 1
        )

        # Calculate Volatility_20
        # For each symbol, calculate 20-day rolling standard deviation of daily returns
        df['Volatility_20'] = df.groupby(level='symbol')['close'].transform(
            lambda x: x.pct_change().rolling(20).std()
        )

        return df

    def get_top_stocks(self, top_k: int = 5, target_date: date = None) -> pd.DataFrame:
        """
        Identifies the top_k stocks based on a combined Momentum and Volatility score.
        Allows specifying a target_date for historical backtesting.

        :param top_k: The number of top stocks to return.
        :param target_date: The date for which to calculate factors and select stocks.
                            If None, defaults to today's date.
        :return: A DataFrame of top_k stock symbols with their final scores, sorted.
        """
        if target_date is None:
            target_date_for_selection = date.today()
        else:
            target_date_for_selection = target_date

        # Determine the date range for data loading
        # Need at least 20 trading days for factor calculation.
        # Load data for the last 90 calendar days to ensure enough data
        # even with holidays/weekends for rolling(20) calculations.
        end_date_for_load = target_date_for_selection
        start_date_for_load = target_date_for_selection - timedelta(days=90)

        print(f"Loading panel data from {start_date_for_load} to {end_date_for_load} for factor calculation (as of {target_date_for_selection})...")
        panel_data = self.db_manager.load_panel_data(start_date_for_load, end_date_for_load)

        if panel_data.empty:
            print("No panel data loaded for factor calculation.")
            return pd.DataFrame()
        
        # Ensure we only use data up to the target_date_for_selection
        panel_data = panel_data.loc[panel_data.index.get_level_values('trade_date') <= pd.Timestamp(target_date_for_selection)]


        # Calculate factors
        print("Calculating factors...")
        factors_df = self.calculate_factors(panel_data.copy()) # Use a copy to avoid SettingWithCopyWarning

        # Drop rows with NaN in factors (due to rolling/shifting)
        factors_df.dropna(subset=['Momentum_20', 'Volatility_20'], inplace=True)

        if factors_df.empty:
            print("No data remaining after factor calculation and dropping NaNs.")
            return pd.DataFrame()

        # Get data for the specific target_date or the most recent available trading day on or before target_date
        # The index is (trade_date, symbol).
        available_dates = factors_df.index.get_level_values('trade_date').unique()
        
        # Find the latest trade_date on or before target_date_for_selection
        valid_trade_dates = available_dates[available_dates <= pd.Timestamp(target_date_for_selection)]
        
        if valid_trade_dates.empty:
            print(f"No valid trade date found on or before {target_date_for_selection} for factor analysis.")
            return pd.DataFrame()
            
        analysis_date = valid_trade_dates.max() # This is the actual date for which we have factors
        print(f"Analyzing data for factors as of: {analysis_date}")
        
        target_day_factors = factors_df.loc[analysis_date]
        
        if target_day_factors.empty:
            print(f"No factor data for the analysis date {analysis_date}.")
            return pd.DataFrame()

        # Scoring Logic
        print("Ranking stocks and calculating final scores...")
        # Rank Momentum (descending, higher momentum is better)
        target_day_factors['Rank_Momentum'] = target_day_factors['Momentum_20'].rank(ascending=False, method='average')

        # Rank Volatility (ascending, lower volatility is better)
        target_day_factors['Rank_Volatility'] = target_day_factors['Volatility_20'].rank(ascending=True, method='average')

        # Final Score: Equal weighting of ranks
        target_day_factors['Final_Score'] = (
            0.5 * target_day_factors['Rank_Momentum'] +
            0.5 * target_day_factors['Rank_Volatility']
        )

        # Sort by Final_Score and get top_k
        top_stocks = target_day_factors.sort_values(by='Final_Score', ascending=True).head(top_k)
        
        # Reset index to make 'symbol' a column and select relevant info
        top_stocks_result = top_stocks.reset_index()[['symbol', 'Momentum_20', 'Volatility_20', 'Final_Score']]
        top_stocks_result['analysis_date'] = analysis_date # Add analysis date to the result
        
        print(f"Top {top_k} stocks identified as of {analysis_date}:")
        print(top_stocks_result)

        return top_stocks_result
