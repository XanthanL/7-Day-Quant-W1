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
                 initial_capital: float = 1_000_000, commission: float = 0.001,
                 index_symbol: str = 'sh000300', stop_loss_pct: float = 0.10):
        """
        Initializes the PortfolioBacktester.

        :param db_manager: An instance of DBManager for data access.
        :param alpha_model: An instance of AlphaModel for stock selection.
        :param initial_capital: Starting capital for the backtest.
        :param commission: Transaction commission rate (e.g., 0.001 for 0.1%).
        :param index_symbol: Symbol of the market index for risk control (e.g., 'sh000300').
        :param stop_loss_pct: Percentage for individual stock stop-loss (e.g., 0.10 for 10%).
        """
        self.db_manager = db_manager
        self.alpha_model = alpha_model
        self.initial_capital = initial_capital
        self.commission = commission
        self.cash = initial_capital
        self.current_positions: Dict[str, int] = {} # {symbol: shares}
        self.positions_cost_price: Dict[str, float] = {} # {symbol: cost_price_per_share}
        self.portfolio_history = pd.DataFrame(columns=['Date', 'TotalValue', 'Cash'])
        self.close_prices_df: pd.DataFrame = pd.DataFrame()
        self.trading_days: pd.DatetimeIndex = pd.DatetimeIndex([])

        self.index_symbol = index_symbol
        self.stop_loss_pct = stop_loss_pct
        self.index_close_df: pd.DataFrame = pd.DataFrame() # To store index close prices
        self.index_sma_df: pd.DataFrame = pd.DataFrame()   # To store index SMA
        self.market_downtrend_active: bool = False         # Flag for market filter state

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

    def _calculate_sma(self, series: pd.Series, window: int) -> pd.Series:
        """Helper to calculate Simple Moving Average."""
        return series.rolling(window=window).mean()

    def _liquidate_all_positions(self, current_day_prices: pd.Series):
        """Liquidates all current stock positions."""
        liquidated_stocks = []
        for symbol, shares in list(self.current_positions.items()):
            if symbol in current_day_prices.index:
                sell_price = current_day_prices[symbol]
                self.cash += shares * sell_price * (1 - self.commission)
                liquidated_stocks.append(f"{symbol} ({shares} shares @ {sell_price:.2f})")
                del self.current_positions[symbol]
                if symbol in self.positions_cost_price:
                    del self.positions_cost_price[symbol]
            else:
                # This should ideally not happen if data is well managed
                print(f"    Warning: Could not liquidate {symbol} as no current price available for {current_day_prices.name}.")
        if liquidated_stocks:
            print(f"    Liquidated: {', '.join(liquidated_stocks)}. Cash after liquidation: {self.cash:.2f}")

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
        print(f"Market Index for Risk Control: {self.index_symbol}, Stop Loss Percentage: {self.stop_loss_pct * 100:.2f}%")

        # Step 1: Data Pre-fetching
        print("Loading panel data...")
        # Load slightly more data than needed for start_date to cover initial factor calculation
        # AlphaModel's get_top_stocks handles its own internal date range for factor calculation
        # This ensures we have enough history for the first selection
        data_prefetch_start_date = start_date - timedelta(days=120) # ~4 months prior for initial factors and index SMA
        raw_panel_data = self.db_manager.load_panel_data(data_prefetch_start_date, end_date)

        if raw_panel_data.empty:
            print("Error: No stock data loaded for the specified date range. Backtest aborted.")
            return

        # Convert to Wide Format for close prices
        self.close_prices_df = raw_panel_data['close'].unstack(level='symbol')
        
        # Load Index Data and calculate SMA_20
        index_raw_data = self.db_manager.load_panel_data(data_prefetch_start_date, end_date)
        if index_raw_data.empty or self.index_symbol not in index_raw_data.index.get_level_values('symbol').unique():
            print(f"Warning: No index data loaded for {self.index_symbol} or index symbol not found. Market filter will be disabled.")
            self.index_close_df = pd.DataFrame(index=self.close_prices_df.index)
            self.index_sma_df = pd.DataFrame(index=self.close_prices_df.index)
        else:
            # Filter for the index symbol and then unstack
            index_df_filtered = index_raw_data.loc[(slice(None), self.index_symbol), 'close']
            if not index_df_filtered.empty:
                index_df_filtered = index_df_filtered.droplevel('symbol').to_frame(name='close')
                self.index_close_df = index_df_filtered # This is now just the close prices for the index
                self.index_sma_df = self._calculate_sma(self.index_close_df['close'], 20).to_frame(name='SMA_20')
            else:
                print(f"Warning: Index data for {self.index_symbol} is empty after filtering. Market filter will be disabled.")
                # 初始化带有 'close' 列的空 DataFrame，填满 NaN
                self.index_close_df = pd.DataFrame(index=self.close_prices_df.index, columns=['close'])
                # 初始化带有 'SMA_20' 列的空 DataFrame
                self.index_sma_df = pd.DataFrame(index=self.close_prices_df.index, columns=['SMA_20'])
        
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
            
            # --- Daily Net Asset Value Update (beginning of day) ---
            # This is done here to capture value before any trading on current day
            current_day_prices_for_value_calc = self.close_prices_df.loc[current_day].dropna()
            # Handle cases where current_day_prices might be empty for value calc
            if current_day_prices_for_value_calc.empty and i > 0:
                # If no prices for today, use previous day's value
                last_total_value = self.portfolio_history['TotalValue'].iloc[-1]
                last_cash = self.portfolio_history['Cash'].iloc[-1]
                self.portfolio_history = self.portfolio_history._append(
                    {'Date': current_day_date, 'TotalValue': last_total_value, 'Cash': last_cash},
                    ignore_index=True
                )
                continue # Skip to next day if no current prices
            elif current_day_prices_for_value_calc.empty and i == 0:
                 print(f"  Warning: No price data for {current_day_date}, first day. Skipping day.")
                 continue # Cannot proceed if first day has no prices

            # Get prices for today (used for all trading decisions and value updates)
            current_day_prices = self.close_prices_df.loc[current_day].dropna()
            
            # --- Step A: Market Filter (大盘风控) ---
            yesterday = current_day - pd.Timedelta(days=1)
            yesterday_index_close = None
            yesterday_index_sma_20 = None

            if yesterday in self.index_close_df.index:
                yesterday_index_close = self.index_close_df.loc[yesterday, 'close']
            if yesterday in self.index_sma_df.index:
                yesterday_index_sma_20 = self.index_sma_df.loc[yesterday, 'SMA_20']
            
            market_filter_triggered = False
            if yesterday_index_close is not None and yesterday_index_sma_20 is not None:
                if yesterday_index_close < yesterday_index_sma_20:
                    if not self.market_downtrend_active:
                        print(f"\n--- {current_day_date}: 市场下行趋势 (指数收盘价 < SMA_20) 检测到。---")
                        print("  触发熔断机制：清仓所有持仓。")
                        self._liquidate_all_positions(current_day_prices)
                        self.market_downtrend_active = True
                    market_filter_triggered = True # Always triggered if market is below SMA
                else:
                    self.market_downtrend_active = False # Market recovers or is above SMA

            if market_filter_triggered:
                # After market filter, update portfolio value and continue to next day
                current_total_value = self._get_portfolio_value(current_day_prices)
                self.portfolio_history = self.portfolio_history._append(
                    {'Date': current_day_date, 'TotalValue': current_total_value, 'Cash': self.cash},
                    ignore_index=True
                )
                print(f"  {current_day_date}: 熔断后当前总资产 = {current_total_value:.2f}, 现金 = {self.cash:.2f}")
                continue # Skip all other trading logic for this day


            # --- Step B: Individual Stop Loss (个股止损) ---
            stocks_stopped_loss = []
            positions_to_check = list(self.current_positions.items()) # Iterate on a copy of items
            for symbol, shares in positions_to_check:
                if symbol in current_day_prices.index:
                    current_price = current_day_prices[symbol]
                    cost_price = self.positions_cost_price.get(symbol)
                    
                    if cost_price and current_price < cost_price * (1 - self.stop_loss_pct):
                        sell_price = current_price
                        self.cash += shares * sell_price * (1 - self.commission)
                        stocks_stopped_loss.append(f"{symbol} ({shares} shares @ {sell_price:.2f}, 成本: {cost_price:.2f})")
                        del self.current_positions[symbol]
                        del self.positions_cost_price[symbol]
            
            if stocks_stopped_loss:
                print(f"\n--- {current_day_date}: 个股止损触发 ---")
                print(f"  止损卖出: {', '.join(stocks_stopped_loss)}")
                current_total_value_after_stop_loss = self._get_portfolio_value(current_day_prices)
                # Update this day's history with the new value after stop loss
                self.portfolio_history.loc[self.portfolio_history['Date'] == current_day_date, 'TotalValue'] = current_total_value_after_stop_loss
                self.portfolio_history.loc[self.portfolio_history['Date'] == current_day_date, 'Cash'] = self.cash


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
                            if symbol in self.positions_cost_price:
                                del self.positions_cost_price[symbol]
                            
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
                        if buy_candidates:
                            cash_per_stock = self.cash / len(buy_candidates)

                            for symbol in buy_candidates:
                                buy_price = current_day_prices[symbol]
                                # Number of shares to buy, ensuring we don't go negative on cash
                                shares_to_buy = int((cash_per_stock / buy_price) * (1 - self.commission)) # Account for commission implicitly
                                
                                if shares_to_buy > 0 and (shares_to_buy * buy_price * (1 + self.commission)) <= self.cash:
                                    self.cash -= shares_to_buy * buy_price * (1 + self.commission)
                                    self.current_positions[symbol] = self.current_positions.get(symbol, 0) + shares_to_buy
                                    self.positions_cost_price[symbol] = buy_price # Store cost price
                                    stocks_bought.append(f"{symbol} ({shares_to_buy} shares @ {buy_price:.2f})")

                if stocks_bought:
                    print(f"  Bought: {', '.join(stocks_bought)}")
                else:
                    print("  No stocks bought.")

                current_total_value_after_rebalance = self._get_portfolio_value(current_day_prices)
                print(f"  After rebalance: 总资产 = {current_total_value_after_rebalance:.2f}, 现金 = {self.cash:.2f}")
            
            # --- Daily Net Asset Value Update (end of day) ---
            # This is now handled before market filter and after stop-loss/rebalance
            # Ensure the last entry in portfolio_history is always up-to-date for current day.
            # If no trades on this day, update with just the value change due to price fluctuation.
            # Otherwise, it's already updated by market filter or stop-loss.
            if not market_filter_triggered and not stocks_stopped_loss: # If no trading activity to update value
                 current_total_value = self._get_portfolio_value(current_day_prices)
                 self.portfolio_history.loc[self.portfolio_history['Date'] == current_day_date, 'TotalValue'] = current_total_value
                 self.portfolio_history.loc[self.portfolio_history['Date'] == current_day_date, 'Cash'] = self.cash # Cash usually unchanged without trade



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
