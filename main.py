# 导入所需库
from datetime import datetime
import sys
import re # 导入正则表达式库
import os # 导入 os 模块以检查文件是否存在

# 从新的包路径导入模块
from src.data.provider import MarketDataProvider
from src.backtesting.core import run_backtest # 导入通用的回测运行函数
from src.backtesting.optimizer import run_optimization # 导入优化运行函数
from src.strategies.backtrader_ma import DualMAStrategy # 导入 DualMAStrategy
from src.strategies.rsi import RSIStrategy # 导入 RSIStrategy
from src.monitoring.live_monitor import main as run_live_monitor # 导入 live_monitor 的 main 函数
from src.analysis.technical_analysis import run_technical_analysis # 导入 technical_analysis 的运行函数
from src.data.database import DBManager # 导入数据库管理器
from src.data.downloader import StockDownloader # 导入股票下载器
from src.strategies.alpha_model import AlphaModel # 导入 AlphaModel
from src.backtesting.portfolio_backtest import PortfolioBacktester # 导入 PortfolioBacktester

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

def main():
    """
    项目主入口函数。
    可以用于下载数据，运行策略回测，参数优化或启动实时监控。
    """
    print("--- 量化交易项目主程序 ---")
    provider = MarketDataProvider(data_dir='./market_data')
    db_manager = DBManager() # Initialize DBManager
    # Note: StockDownloader is initialized within its specific choice block to avoid early Akshare calls.

    while True: # 让用户可以多次操作
        print("\n请选择要执行的操作:")
        print("  1. 下载最新数据 (旧的CSV方式)")
        print("  2. 运行 DualMAStrategy 回测 (使用数据库数据)")
        print("  3. 运行 RSIStrategy 回测 (使用数据库数据)")
        print("  4. 运行 DualMAStrategy 参数优化 (使用数据库数据)")
        print("  5. 启动实时监控脚本 (RSI 策略)")
        print("  6. 运行技术分析和绘图 (使用数据库数据)")
        print("  7. 检查数据库状态")
        print("  8. 全市场股票数据增量下载 (使用数据库)")
        print("  9. 运行多因子选股模型 (Alpha Model)")
        print("  10. 运行投资组合回测 (Portfolio Backtest)")
        print("  0. 退出")

        choice = input("请输入您的选择 (0-8): ")

        if choice == '1':
            print("\n--- 正在下载最新数据 (CSV方式) ---")
            tickers_to_download_str = input("请输入要下载的股票代码，多个代码请用逗号分隔 (例如: 600519,300750): ")
            tickers_to_test = [t.strip() for t in tickers_to_download_str.split(',') if re.match(r'^\d{6}$', t.strip())]
            
            if not tickers_to_test:
                print("未输入有效的股票代码。")
                continue

            start_date = '2020-01-01'
            end_date = datetime.today().strftime('%Y-%m-%d')
            
            print(f"\n将要下载以下A股 Tickers 的数据: {tickers_to_test}")
            print(f"时间范围: {start_date} 到 {end_date}")

            for ticker in tickers_to_test:
                provider.download_data(ticker=ticker, start_date=start_date, end_date=end_date)
            
            print("\n--- 所有数据下载完成 ---")

        elif choice in ['2', '3', '4', '6']:
            ticker = get_ticker_input()
            # 从数据库加载数据
            stock_data = db_manager.get_daily_data(ticker)

            if stock_data.empty:
                print(f"错误: 数据库中找不到 {ticker} 的数据。请先使用选项 '1' 下载数据或 'scripts/migrate_csv_to_db.py' 迁移数据。")
                continue
            
            print(f"\n正在为 {ticker} 加载数据库数据...")
            
            if choice == '2':
                print(f"\n--- 运行 DualMAStrategy 回测 (股票代码: {ticker}) ---")
                run_backtest(DualMAStrategy, stock_data.copy(), plot=True)
                print("\n--- DualMAStrategy 回测完成 ---")

            elif choice == '3':
                print(f"\n--- 运行 RSIStrategy 回测 (股票代码: {ticker}) ---")
                run_backtest(RSIStrategy, stock_data.copy(), plot=True)
                print("\n--- RSIStrategy 回测完成 ---")

            elif choice == '4':
                print(f"\n--- 运行 DualMAStrategy 参数优化 (股票代码: {ticker}) ---")
                run_optimization(stock_data.copy(), maxcpus=1)
                print("\n--- 参数优化完成 ---")
                
            elif choice == '6':
                print(f"\n--- 运行技术分析和绘图 (股票代码: {ticker}) ---")
                run_technical_analysis(stock_data.copy(), ticker)
                print("\n--- 技术分析和绘图完成 ---")

        elif choice == '5':
            ticker = get_ticker_input()
            print(f"\n--- 启动实时监控脚本 (股票代码: {ticker}) ---")
            run_live_monitor(ticker)
            print("\n--- 实时监控脚本已停止 ---")
        
        elif choice == '7':
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
                    sorted_latest_dates = sorted(latest_dates.items()) # Sort for consistent head/tail
                    num_symbols = len(sorted_latest_dates)
                    
                    if num_symbols > 10:
                        # Print first 5
                        for symbol, trade_date in sorted_latest_dates[:5]:
                            print(f"  - {symbol}: {trade_date}")
                        print("  ... (省略部分) ...")
                        # Print last 5
                        for symbol, trade_date in sorted_latest_dates[-5:]:
                            print(f"  - {symbol}: {trade_date}")
                    else:
                        # Print all if 10 or fewer
                        for symbol, trade_date in sorted_latest_dates:
                            print(f"  - {symbol}: {trade_date}")
                else:
                    print("  (无数据)")

        elif choice == '8':
            print("\n--- 全市场股票数据增量下载 ---")
            downloader = StockDownloader(db_manager)
            
            max_workers_input = input("请输入并发下载线程数 (默认 5): ")
            max_workers = int(max_workers_input) if max_workers_input.isdigit() else 5

            limit_input = input("请输入下载股票数量限制 (用于测试, 0 表示全部, 默认 0): ")
            limit = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else None
            
            downloader.download_all_stocks(max_workers=max_workers, limit=limit)

        elif choice == '9':
            print("\n--- 运行多因子选股模型 (Alpha Model) ---")
            db_manager = DBManager() # Ensure db_manager is initialized if not already
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

        elif choice == '10':
            print("\n--- 运行投资组合回测 (Portfolio Backtest) ---")
            db_manager = DBManager()
            alpha_model = AlphaModel(db_manager) # AlphaModel requires DBManager
            portfolio_backtester = PortfolioBacktester(db_manager, alpha_model)

            # Get inputs for backtest
            start_date_str = input("请输入回测开始日期 (YYYY-MM-DD, 例如: 2023-01-01): ")
            end_date_str = input("请输入回测结束日期 (YYYY-MM-DD, 例如: 2023-12-31): ")
            rebalance_freq_str = input("请输入调仓频率 (交易日天数, 默认 20): ")
            top_k_str = input("请输入每次选股的Top K数量 (默认 5): ")

            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                rebalance_freq = int(rebalance_freq_str) if rebalance_freq_str.isdigit() else 20
                top_k = int(top_k_str) if top_k_str.isdigit() else 5

                portfolio_backtester.run_backtest(start_date, end_date, rebalance_freq, top_k)
                portfolio_backtester.plot_performance()

            except ValueError as e:
                print(f"输入日期格式错误或数值错误: {e}")
            except Exception as e:
                print(f"回测运行错误: {e}")
            print("\n--- 投资组合回测运行完成 ---")

        elif choice == '0':
            print("退出程序。")
            sys.exit(0)
        else:
            print("无效的选择，请重新输入。")

if __name__ == '__main__':
    main()