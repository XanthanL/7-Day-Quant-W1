import pandas as pd
from datetime import date, timedelta
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns

from src.data.database import DBManager
from src.strategies.alpha_model import AlphaModel

class PortfolioBacktester:
    """
    Implements a multi-stock, periodic rebalancing portfolio backtesting engine.
    """

    def __init__(self, db_manager: DBManager, alpha_model: AlphaModel,
                 initial_capital: float = 1_000_000, commission: float = 0.001):
        """
        Initializes the PortfolioBacktester.

        :param db_manager: An instance of DBManager for data access.
        :param alpha_model: An instance of AlphaModel for stock selection.
        :param initial_capital: Starting capital for the backtest.
        :param commission: Transaction commission rate (e.g., 0.001 for 0.1%).
        """
        self.db_manager = db_manager
        self.alpha_model = alpha_model
        self.initial_capital = initial_capital
        self.commission = commission
        self.cash = initial_capital
        self.current_positions: Dict[str, int] = {} # {symbol: shares}
        self.portfolio_history = pd.DataFrame(columns=['Date', 'TotalValue', 'Cash'])
        self.close_prices_df: pd.DataFrame = pd.DataFrame()
        self.trading_days: pd.DatetimeIndex = pd.DatetimeIndex([])

        sns.set_style("whitegrid") # Set seaborn style for plots

    def _get_portfolio_value(self, current_day_prices: pd.Series) -> float:
        """
        Calculates the current total value of the portfolio.
        :param current_day_prices: Series of current day close prices for held stocks.
        :return: Total portfolio value.
        """
        holdings_value = 0.0
        for symbol, shares in self.current_positions.items():
            if symbol in current_day_prices.index:
                holdings_value += shares * current_day_prices[symbol]
        return self.cash + holdings_value

    def run_backtest(self, start_date: date, end_date: date, rebalance_freq: int = 20, top_k: int = 5):
        """
        Runs the backtest simulation.

        :param start_date: Start date for the backtest.
        :param end_date: End date for the backtest.
        :param rebalance_freq: Rebalancing frequency in trading days.
        :param top_k: Number of top stocks to select by the AlphaModel.
        """
        print(f"Starting backtest from {start_date} to {end_date} with rebalance frequency {rebalance_freq} days.")
        print(f"Initial Capital: {self.initial_capital}, Commission: {self.commission * 100:.2f}%")

        # Step 1: Data Pre-fetching
        print("Loading panel data...")
        # Load slightly more data than needed for start_date to cover initial factor calculation
        # AlphaModel's get_top_stocks handles its own internal date range for factor calculation
        # This ensures we have enough history for the first selection
        data_prefetch_start_date = start_date - timedelta(days=90) # ~3 months prior for initial factors
        raw_panel_data = self.db_manager.load_panel_data(data_prefetch_start_date, end_date)

        if raw_panel_data.empty:
            print("Error: No data loaded for the specified date range. Backtest aborted.")
            return

        # Convert to Wide Format for close prices
        self.close_prices_df = raw_panel_data['close'].unstack(level='symbol')
        
        # Filter trading days within the actual backtest range
        self.trading_days = self.close_prices_df.index[
            (self.close_prices_df.index.date >= start_date) & 
            (self.close_prices_df.index.date <= end_date)
        ].drop_duplicates().sort_values()

        if self.trading_days.empty:
            print("Error: No valid trading days within the specified backtest range. Backtest aborted.")
            return

        print(f"Total trading days: {len(self.trading_days)}")
        
        # Ensure initial cash is recorded
        self.portfolio_history = self.portfolio_history._append(
            {'Date': self.trading_days[0].date() - timedelta(days=1), 'TotalValue': self.initial_capital, 'Cash': self.initial_capital},
            ignore_index=True
        )

        # Step 2: Time Loop
        for i, current_day in enumerate(self.trading_days):
            current_day_date = current_day.date()
            # Removed daily print: print(f"\nProcessing Day: {current_day_date} ({i+1}/{len(self.trading_days)})")

            # Get prices for today
            current_day_prices = self.close_prices_df.loc[current_day].dropna()

            if current_day_prices.empty:
                # Removed daily print: print(f"  No price data for {current_day_date}, skipping day.")
                # Record previous day's value if current day has no prices
                last_record = self.portfolio_history.iloc[-1]
                self.portfolio_history = self.portfolio_history._append(
                    {'Date': current_day_date, 'TotalValue': last_record['TotalValue'], 'Cash': last_record['Cash']},
                    ignore_index=True
                )
                continue
            
            # --- Rebalance Logic ---
            if i % rebalance_freq == 0:
                print(f"\n--- Rebalancing on {current_day_date} ---")
                
                # For rebalancing, we use data available *up to the previous trading day*.
                # We pass the day BEFORE the current trading day as target_date to AlphaModel
                # to avoid any look-ahead bias. AlphaModel will then use data up to that day.
                target_date_for_alpha_model = current_day_date - timedelta(days=1)
                
                selected_stocks_df = self.alpha_model.get_top_stocks(top_k=top_k, target_date=target_date_for_alpha_model)
                new_selection = set(selected_stocks_df['symbol'].tolist())
                print(f"  Selected stocks: {list(new_selection)}")

                stocks_sold = []
                # --- Sell old stocks ---
                for symbol, shares in list(self.current_positions.items()): # Iterate on a copy
                    if symbol not in new_selection:
                        if symbol in current_day_prices.index:
                            sell_price = current_day_prices[symbol]
                            self.cash += shares * sell_price * (1 - self.commission)
                            stocks_sold.append(f"{symbol} ({shares} shares @ {sell_price:.2f})")
                            del self.current_positions[symbol]
                        # Removed warning, as it's not a rebalancing action, but a data issue
                        # else:
                        #     print(f"    Warning: Tried to sell {symbol} but no current price available.")
                            
                if stocks_sold:
                    print(f"  Sold: {', '.join(stocks_sold)}")
                else:
                    print("  No stocks sold.")

                stocks_bought = []
                # --- Buy new stocks (equal weight allocation) ---
                if new_selection:
                    # Distribute available cash among new selections
                    if self.cash > 0:
                        buy_candidates = []
                        for symbol in new_selection:
                            if symbol in current_day_prices.index and current_day_prices[symbol] > 0:
                                buy_candidates.append(symbol)
                            # Removed warning
                            # else:
                            #     print(f"    Warning: {symbol} in new selection but no valid current price or price is zero. Skipping purchase.")

                        if buy_candidates:
                            cash_per_stock = self.cash / len(buy_candidates)

                            for symbol in buy_candidates:
                                buy_price = current_day_prices[symbol]
                                # Number of shares to buy, ensuring we don't go negative on cash
                                shares_to_buy = int((cash_per_stock / buy_price) * (1 - self.commission)) # Account for commission implicitly
                                
                                if shares_to_buy > 0 and (shares_to_buy * buy_price * (1 + self.commission)) <= self.cash:
                                    self.cash -= shares_to_buy * buy_price * (1 + self.commission)
                                    self.current_positions[symbol] = self.current_positions.get(symbol, 0) + shares_to_buy
                                    stocks_bought.append(f"{symbol} ({shares_to_buy} shares @ {buy_price:.2f})")
                                # Removed warnings/prints here for brevity, keeping only essential
                                # elif shares_to_buy > 0:
                                #      print(f"    Not enough cash to buy {shares_to_buy} shares of {symbol} with commission. Remaining cash: {self.cash:.2f}")
                                # else:
                                #     print(f"    Cannot buy 0 shares of {symbol} or buy price too high for available cash.")
                        # Removed "No valid buy candidates" print
                        # else:
                        #     print("    No valid buy candidates among new selection with available prices.")
                    # Removed "No cash available" print
                    # else:
                    #     print("    No cash available to make new purchases.")
                # Removed "No stocks selected for purchase" print
                # else:
                #     print("  No stocks selected for purchase during rebalancing.")

                if stocks_bought:
                    print(f"  Bought: {', '.join(stocks_bought)}")
                else:
                    print("  No stocks bought.")

                current_total_value_after_rebalance = self._get_portfolio_value(current_day_prices)
                print(f"  After rebalance: Total Value = {current_total_value_after_rebalance:.2f}, Cash = {self.cash:.2f}")
            
            # --- Daily Net Asset Value Update ---
            current_total_value = self._get_portfolio_value(current_day_prices)
            self.portfolio_history = self.portfolio_history._append(
                {'Date': current_day_date, 'TotalValue': current_total_value, 'Cash': self.cash},
                ignore_index=True
            )
            # Removed daily print: print(f"  End of day {current_day_date}: Total Value = {current_total_value:.2f}, Cash = {self.cash:.2f}")

        print("\nBacktest completed.")
        print(f"Final Portfolio Value: {self.portfolio_history['TotalValue'].iloc[-1]:.2f}")
        print(f"Total Return: {(self.portfolio_history['TotalValue'].iloc[-1] / self.initial_capital - 1) * 100:.2f}%")

    def plot_performance(self):
        """
        Plots the total portfolio value over time and displays total return.
        """
        if self.portfolio_history.empty:
            print("No backtest history to plot. Please run backtest first.")
            return

        self.portfolio_history['Date'] = pd.to_datetime(self.portfolio_history['Date'])
        self.portfolio_history.set_index('Date', inplace=True)

        plt.figure(figsize=(12, 6))
        plt.plot(self.portfolio_history.index, self.portfolio_history['TotalValue'], label='Portfolio Value')
        plt.title('Portfolio Backtest Performance')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        total_return = (self.portfolio_history['TotalValue'].iloc[-1] / self.initial_capital - 1) * 100
        print(f"Total Return: {total_return:.2f}%")
