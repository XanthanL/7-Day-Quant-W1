# 导入所需库
from datetime import datetime, date
import sys
import re
import os

# 从新的包路径导入模块
from src.backtesting.core import run_backtest
from src.backtesting.optimizer import run_optimization
from src.backtesting.portfolio_backtest import PortfolioBacktester
from src.strategies.backtrader_ma import DualMAStrategy
from src.strategies.rsi import RSIStrategy
from src.monitoring.live_monitor import main as run_live_monitor
from src.data.database import DBManager
from src.data.downloader import StockDownloader
from src.strategies.alpha_model import AlphaModel


def get_ticker_input():
    """
    提示用户输入股票代码并进行基本验证。
    返回一个有效的股票代码字符串。
    """
    while True:
        ticker = input("请输入6位数的股票代码 (例如: 600519): ").strip()
        if re.match(r'^\d{6}$', ticker): # 验证输入是否为6位数字
            return ticker
        else:
            print("错误: 股票代码必须是6位数字。请重新输入。")

def data_management_menu(db_manager: DBManager):
    """
    数据管理子菜单：全市场数据下载和数据库状态检查。
    """
    downloader = StockDownloader(db_manager) # Initialize here to avoid early Akshare calls

    while True:
        print("\n--- 数据管理 ---")
        print("  1. 全市场股票数据增量下载")
        print("  2. 检查数据库状态")
        print("  0. 返回主菜单")

        choice = input("请输入您的选择 (0-2): ")

        if choice == '1':
            print("\n--- 全市场股票数据增量下载 ---")
            max_workers_input = input("请输入并发下载线程数 (默认 5): ")
            max_workers = int(max_workers_input) if max_workers_input.isdigit() else 5

            limit_input = input("请输入下载股票数量限制 (用于测试, 0 表示全部, 默认 0): ")
            limit = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else None
            
            downloader.download_all_stocks(max_workers=max_workers, limit=limit)
            print("--- 下载完成 ---")

        elif choice == '2':
            print("\n--- 检查数据库状态 ---")
            db_status = db_manager.get_status()
            if 'error' in db_status:
                print(f"无法获取数据库状态: {db_status['error']}")
            else:
                print(f"数据库文件: {db_manager.engine.url.database}")
                print(f"总记录数: {db_status.get('total_records', 0)}")
                print(f"不同股票代码数量: {db_status.get('distinct_symbols_count', 0)}")
                print("各股票最新交易日期:")
                latest_dates = db_status.get('latest_trade_dates_per_symbol', {})
                if latest_dates:
                    sorted_latest_dates = sorted(latest_dates.items())
                    num_symbols = len(sorted_latest_dates)
                    
                    if num_symbols > 10:
                        for symbol, trade_date in sorted_latest_dates[:5]:
                            print(f"  - {symbol}: {trade_date}")
                        print("  ... (省略部分) ...")
                        for symbol, trade_date in sorted_latest_dates[-5:]:
                            print(f"  - {symbol}: {trade_date}")
                    else:
                        for symbol, trade_date in sorted_latest_dates:
                            print(f"  - {symbol}: {trade_date}")
                else:
                    print("  (无数据)")
            print("--- 数据库状态检查完成 ---")
        elif choice == '0':
            break
        else:
            print("无效的选择，请重新输入。")

def single_stock_strategy_menu(db_manager: DBManager):
    """
    单股票策略回测子菜单。
    """
    while True:
        print("\n--- 单股票策略回测 ---")
        print("  1. 运行 DualMAStrategy 回测")
        print("  2. 运行 RSIStrategy 回测")
        print("  3. 运行 DualMAStrategy 参数优化")
        print("  0. 返回主菜单")

        choice = input("请输入您的选择 (0-3): ")

        if choice in ['1', '2', '3']:
            ticker = get_ticker_input()
            stock_data = db_manager.get_daily_data(ticker)

            if stock_data.empty:
                print(f"错误: 数据库中找不到 {ticker} 的数据。请先下载数据。")
                continue
            
            print(f"\n正在为 {ticker} 加载数据库数据...")
            
            if choice == '1':
                print(f"\n--- 运行 DualMAStrategy 回测 (股票代码: {ticker}) ---")
                run_backtest(DualMAStrategy, stock_data.copy(), plot=True)
                print("\n--- DualMAStrategy 回测完成 ---")

            elif choice == '2':
                print(f"\n--- 运行 RSIStrategy 回测 (股票代码: {ticker}) ---")
                run_backtest(RSIStrategy, stock_data.copy(), plot=True)
                print("\n--- RSIStrategy 回测完成 ---")

            elif choice == '3':
                print(f"\n--- 运行 DualMAStrategy 参数优化 (股票代码: {ticker}) ---")
                run_optimization(stock_data.copy(), maxcpus=1)
                print("\n--- 参数优化完成 ---")
        elif choice == '0':
            break
        else:
            print("无效的选择，请重新输入。")

def main():
    """
    项目主入口函数。
    可以用于数据管理，运行策略回测，参数优化，多因子选股或启动实时监控。
    """
    print("--- 量化交易项目主程序 ---")
    db_manager = DBManager()

    while True:
        print("\n请选择要执行的操作:")
        print("  1. 数据管理 (下载/检查数据库)")
        print("  2. 单股票策略回测")
        print("  3. 多因子选股 (Alpha Model)")
        print("  4. 投资组合回测")
        print("  5. 实时监控")
        print("  0. 退出")

        choice = input("请输入您的选择 (0-5): ")

        if choice == '1':
            data_management_menu(db_manager)
        elif choice == '2':
            single_stock_strategy_menu(db_manager)
        elif choice == '3':
            print("\n--- 运行多因子选股模型 (Alpha Model) ---")
            alpha_model = AlphaModel(db_manager)
            
            top_k_input = input(f"请输入要返回的Top N股票数量 (默认 {5}): ")
            top_k = int(top_k_input) if top_k_input.isdigit() and int(top_k_input) > 0 else 5

            top_stocks_df = alpha_model.get_top_stocks(top_k=top_k)
            if not top_stocks_df.empty:
                print("\n成功获取Top股票:")
                print(top_stocks_df)
            else:
                print("\n未能获取Top股票，请检查数据和模型逻辑。")
            print("\n--- 多因子选股模型运行完成 ---")
        elif choice == '4':
            print("\n--- 运行投资组合回测 (Portfolio Backtest) ---")
            alpha_model = AlphaModel(db_manager) # AlphaModel requires DBManager
            portfolio_backtester = PortfolioBacktester(db_manager, alpha_model)

            start_date_str = input("请输入回测开始日期 (YYYY-MM-DD, 例如: 2023-01-01): ")
            end_date_str = input("请输入回测结束日期 (YYYY-MM-DD, 例如: 2023-12-31): ")
            rebalance_freq_str = input("请输入调仓频率 (交易日天数, 默认 20): ")
            top_k_str = input("请输入每次选股的Top K数量 (默认 5): ")

            try:
                start_date_backtest = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date_backtest = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                rebalance_freq = int(rebalance_freq_str) if rebalance_freq_str.isdigit() else 20
                top_k = int(top_k_str) if top_k_str.isdigit() else 5

                portfolio_backtester.run_backtest(start_date_backtest, end_date_backtest, rebalance_freq, top_k)
                portfolio_backtester.plot_performance()

            except ValueError as e:
                print(f"输入日期格式错误或数值错误: {e}")
            except Exception as e:
                print(f"回测运行错误: {e}")
            print("\n--- 投资组合回测运行完成 ---")
        elif choice == '5':
            ticker = get_ticker_input()
            print(f"\n--- 启动实时监控脚本 (股票代码: {ticker}) ---")
            run_live_monitor(ticker)
            print("\n--- 实时监控脚本已停止 ---")
        elif choice == '0':
            print("退出程序。")
            sys.exit(0)
        else:
            print("无效的选择，请重新输入。")

if __name__ == '__main__':
    main()
