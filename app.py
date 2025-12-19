import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

from src.data.database import DBManager
from src.strategies.alpha_model import AlphaModel
from src.backtesting.portfolio_backtest import PortfolioBacktester

st.set_page_config(layout="wide", page_title="量化交易仪表盘 (Quant Dashboard)")

st.title("量化交易策略仪表盘 (Quant Trading Strategy Dashboard)")

# --- Cached Data Loading ---

@st.cache_resource
def get_db_manager():
    """
    Caches the DBManager to avoid reconnecting to the database on every script rerun.
    """
    print("Initializing DBManager...")
    db_manager = DBManager()
    return db_manager

# --- Helper Functions ---
def calculate_max_drawdown(portfolio_history: pd.DataFrame) -> float:
    """
    Calculates the maximum drawdown from the portfolio history.
    """
    if 'TotalValue' not in portfolio_history.columns or portfolio_history.empty:
        return 0.0
    
    # Calculate the running maximum
    running_max = portfolio_history['TotalValue'].cummax()
    # Calculate the drawdown
    drawdown = (portfolio_history['TotalValue'] - running_max) / running_max
    # Get the maximum drawdown
    max_drawdown = drawdown.min()
    return max_drawdown

# --- Main App ---

db_manager = get_db_manager()

tab1, tab2 = st.tabs(["选股扫描 (Alpha Scanner)", "策略回测 (Backtest)"])

# --- Tab 1: Alpha Scanner ---
with tab1:
    st.header("多因子选股扫描器 (Multi-factor Alpha Scanner)")

    col1, col2 = st.columns([1, 4])
    with col1:
        target_date = st.date_input("请选择扫描日期 (Select Date)", value=date.today() - timedelta(days=1))
        top_k_scanner = st.slider("选择Top K股票数量 (Select Top K)", 1, 20, 5)

    if st.button("开始扫描市场 (Scan Market)"):
        with st.spinner("正在运行Alpha模型... (Running Alpha Model...)"):
            alpha_model = AlphaModel(db_manager)
            top_stocks_df = alpha_model.get_top_stocks(top_k=top_k_scanner, target_date=target_date)

            if not top_stocks_df.empty:
                st.subheader(f"Top {top_k_scanner} Stocks for {target_date}")
                st.dataframe(top_stocks_df, use_container_width=True)
            else:
                st.warning("在指定日期未找到足够数据进行选股。(No data found to select stocks for the given date.)")

# --- Tab 2: Backtest ---
with tab2:
    st.header("投资组合回测 (Portfolio Backtest)")

    with st.sidebar:
        st.header("回测参数 (Backtest Parameters)")
        start_date = st.date_input("回测开始日期 (Start Date)", value=date(2023, 1, 1))
        end_date = st.date_input("回测结束日期 (End Date)", value=date.today())
        
        top_k_backtest = st.slider("每次选股的Top K数量 (Top K per Rebalance)", 1, 20, 5)
        rebalance_freq = st.number_input("调仓频率 (交易日天数) (Rebalance Freq in days)", min_value=1, value=20)
        
        st.subheader("风险控制 (Risk Control)")
        index_symbol = st.text_input("大盘指数代码 (Market Index Symbol)", value='sh000300')
        stop_loss_pct = st.slider("个股止损百分比 (Stop Loss %)", 0.0, 0.2, 0.1, 0.01)

    if st.button("运行回测 (Run Backtest)"):
        if start_date >= end_date:
            st.error("错误：开始日期必须在结束日期之前。(Error: Start date must be before end date.)")
        else:
            with st.spinner("正在运行投资组合回测... (Running portfolio backtest...)"):
                # Instantiate models
                alpha_model_backtest = AlphaModel(db_manager)
                backtester = PortfolioBacktester(
                    db_manager=db_manager,
                    alpha_model=alpha_model_backtest,
                    index_symbol=index_symbol,
                    stop_loss_pct=stop_loss_pct
                )

                # Run backtest
                backtester.run_backtest(
                    start_date=start_date,
                    end_date=end_date,
                    rebalance_freq=int(rebalance_freq),
                    top_k=top_k_backtest
                )
                
                # Get history
                history_df = backtester.portfolio_history.copy()

                if not history_df.empty:
                    st.subheader("回测结果 (Backtest Results)")

                    # --- Performance Metrics ---
                    total_return_pct = (history_df['TotalValue'].iloc[-1] / history_df['TotalValue'].iloc[0] - 1) * 100
                    max_drawdown_pct = calculate_max_drawdown(history_df) * 100
                    
                    col_metric1, col_metric2 = st.columns(2)
                    col_metric1.metric("总回报率 (Total Return)", f"{total_return_pct:.2f}%")
                    col_metric2.metric("最大回撤 (Max Drawdown)", f"{max_drawdown_pct:.2f}%")

                    # --- Performance Chart ---
                    history_df['Date'] = pd.to_datetime(history_df['Date'])
                    fig = px.line(history_df, x='Date', y='TotalValue', title='投资组合净值曲线 (Portfolio Value Over Time)')
                    fig.update_layout(xaxis_title='日期 (Date)', yaxis_title='投资组合净值 (Portfolio Value)')
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning("回测未生成任何历史数据。(Backtest did not produce any history.)")
