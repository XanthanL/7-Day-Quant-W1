# 7-Day-Quant-Challenge

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Backtrader](https://img.shields.io/badge/Backtrader-v1.9-green.svg)](https://www.backtrader.com/)
[![Akshare](https://img.shields.io/badge/Akshare-Latest-brightgreen.svg)](https://akshare.akfamily.xyz/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Introduction

这是一个为期7天的量化交易挑战项目，旨在从零构建一个基于 Python 的本地量化回测与模拟实盘系统。项目正逐步涵盖从**高效数据管理**、**多因子选股**、**投资组合回测**到策略开发、参数优化与模拟实时监控的整个流程，旨在帮助初学者快速掌握量化交易系统的基本构建与进阶应用。

## Features

-   **数据源与管理**:
    -   对接 `Akshare`，稳定获取 A 股（沪深股票）历史行情数据和实时行情数据。
    -   **本地 SQLite 数据库集成 (`quant.db`)**：取代 CSV 文件，实现结构化存储，支持高效查询与增量更新。
    -   **多线程全市场下载器 (`src/data/downloader.py`)**：高效、增量地下载并更新全市场股票数据到本地数据库。
    -   自动化的 ETL (Extract, Transform, Load) 流程，将原始数据清洗并存储。

-   **多因子选股模型 (Alpha Model)**:
    -   **`src/strategies/alpha_model.py`**：实现基于多因子的选股逻辑。
    -   当前因子包括：**动量 (Momentum_20)** 和 **波动率 (Volatility_20)**。
    -   支持计算最新交易日的因子值，并根据综合评分选出 Top N 股票。

-   **投资组合回测引擎 (`src/backtesting/portfolio_backtest.py`)**:
    -   支持**多只股票**的组合回测，模拟真实交易场景。
    -   实现**定期调仓**功能（基于交易日频率），根据 Alpha Model 的选股结果进行换仓操作。
    -   完整模拟资金管理、交易佣金扣除，并记录每日投资组合净值。

-   **策略支持**:
    -   **双均线趋势策略 (Dual Moving Average Crossover - Trend Following)**: 经典趋势跟踪策略，通过短期与长期均线的金叉死叉进行买卖决策。
    -   **RSI 均值回归策略 (RSI Mean Reversion)**: 经典均值回归策略，利用 RSI 指标的超买超卖信号进行反向操作。

-   **回测与优化**:
    -   基于 `Backtrader` 框架构建的回测引擎，支持事件驱动的回测。
    -   提供专业的性能指标（如夏普比率、最大回撤）和可视化图表。
    -   利用 `Backtrader` 的优化功能，通过网格搜索 (Grid Search) 寻找策略的最佳参数组合。

-   **模拟实盘**: 独立的监控脚本，模拟实时获取行情数据，并根据预设策略逻辑发出交易信号报警，辅助决策。

## Tech Stack

-   **Python**: 核心编程语言 (3.8+)
-   **Pandas**: 强大的数据处理和分析库
-   **NumPy**: 支持大型多维数组和矩阵运算
-   **Akshare**: 开源免费的财经数据接口库
-   **SQLAlchemy**: Python SQL 工具包和 ORM，用于数据库操作
-   **Matplotlib**: 数据可视化库 (用于绘制K线图、回测净值曲线等)
-   **Seaborn**: 基于 Matplotlib 的统计数据可视化库 (用于美化图表)
-   **Backtrader**: Python 量化回测框架
-   **Mplfinance**: 基于 Matplotlib 的金融数据可视化库
-   **Time / Datetime**: 时间相关功能

## Installation & Setup

1.  **克隆项目仓库**:
    ```bash
    git clone https://github.com/XanthanL/7-Day-Quant-W1.git
    cd 7-Day-Quant-W1
    ```

2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **初始化数据库 (可选)**:
    *   如果你希望从头开始构建数据库，或者确保数据库结构最新：
        ```bash
        # 运行 main.py 后，选择 "8. 全市场股票数据增量下载" 将会自动初始化数据库
        # 或者直接运行 scripts/migrate_csv_to_db.py 如果有历史CSV数据需要迁移
        ```
    *   **建议**: 运行 `python main.py`，然后选择 `8` 进行全市场数据下载，这将自动创建并填充 `quant.db`。

## Usage Guide

所有操作均可通过运行项目根目录下的 `main.py` 脚本进行交互式选择。

```bash
python main.py
```

运行后，您将看到一个菜单，请根据提示输入对应的数字进行操作。

### 菜单选项详解 (更新至 Day 4):

-   **1. 下载最新数据 (旧的CSV方式)**:
    -   程序将使用 `Akshare` 下载指定股票的历史数据，并保存到 `market_data/` 目录中。
    -   *注意：此为旧版CSV数据下载方式，建议使用选项 8 进行数据库数据下载。*

-   **2. 运行 DualMAStrategy 回测 (使用数据库数据)**:
    -   使用 `Backtrader` 框架运行双均线策略的回测，从 `quant.db` 读取数据。
    -   输出性能指标，并展示回测结果图。

-   **3. 运行 RSIStrategy 回测 (使用数据库数据)**:
    -   使用 `Backtrader` 框架运行 RSI 策略的回测，从 `quant.db` 读取数据。
    -   输出性能指标，并展示回测结果图。

-   **4. 运行 DualMAStrategy 参数优化 (使用数据库数据)**:
    -   对双均线策略的短周期和长周期参数进行网格搜索优化，从 `quant.db` 读取数据。
    -   输出每个参数组合的回测结果，并给出最佳参数组合。

-   **5. 启动实时监控脚本 (RSI 策略)**:
    -   启动一个模拟实盘监控脚本，实时获取指定股票行情，计算 RSI 并发出交易信号提示。
    -   **此脚本将持续运行，您需要手动使用 `Ctrl+C` 停止。**

-   **6. 运行技术分析和绘图 (使用数据库数据)**:
    -   加载指定股票的历史数据，计算移动平均线、对数收益率、滚动波动率等。
    -   使用 `mplfinance` 绘制带有这些指标的 K 线图。

-   **7. 检查数据库状态**:
    -   显示 `quant.db` 的概况，包括总记录数、不同股票数量及各股票的最新交易日期。

-   **8. 全市场股票数据增量下载 (使用数据库)**:
    -   通过 `src/data/downloader.py`，高效、增量地下载并更新**全市场所有股票**的日线数据到 `quant.db`。
    -   支持多线程并发下载，大幅提高效率。

-   **9. 运行多因子选股模型 (Alpha Model)**:
    -   通过 `src/strategies/alpha_model.py` 运行多因子选股模型。
    -   基于最新的市场数据，计算动量和波动率因子，并选出评分最高的 Top N 股票。

-   **10. 运行投资组合回测 (Portfolio Backtest)**:
    -   通过 `src/backtesting/portfolio_backtest.py` 启动一个多股票、定期调仓的投资组合回测。
    -   输入回测日期范围、调仓频率和选股数量，查看投资组合的净值表现和总回报率。

## Structure

```
Quantifying_Test/
├── src/
│   ├── analysis/             # 数据分析与可视化模块
│   │   └── technical_analysis.py # 技术分析和绘图
│   │
│   ├── backtesting/          # 回测框架和优化模块
│   │   ├── core.py           # Backtrader 回测核心运行逻辑
│   │   ├── optimizer.py      # Backtrader 参数优化逻辑
│   │   └── portfolio_backtest.py # **多股票投资组合回测引擎**
│   │
│   ├── data/                 # 数据处理模块
│   │   ├── database.py       # **SQLite 数据库管理与数据读取 (`DBManager`, `load_panel_data`)**
│   │   ├── downloader.py     # **全市场股票数据增量下载器**
│   │   └── provider.py       # 数据获取、清洗和加载 (基于 Akshare)
│   │
│   ├── monitoring/           # 实时监控模块
│   │   └── live_monitor.py   # 模拟实盘监控
│   │
│   ├── strategies/           # 策略定义模块
│   │   ├── alpha_model.py    # **多因子选股模型 (Momentum, Volatility)**
│   │   ├── backtrader_ma.py  # Backtrader 双均线策略类
│   │   ├── dual_ma.py        # 向量化双均线策略
│   │   └── rsi.py            # Backtrader RSI 策略类
│   │
│   └── utils/                # 通用工具函数模块
│       └── indicators.py     # 通用指标计算函数
│
├── market_data/             # 存放旧版本地 CSV 数据文件 (逐渐被 quant.db 替代)
│   ├── 300750.csv
│   └── 600519.csv
│
├── quant.db                 # **本地 SQLite 数据库文件 (存储全市场日线数据)**
├── main.py                  # 项目主入口，交互式菜单
├── requirements.txt         # Python 依赖列表
├── README.md                # 项目说明文档
├── LICENSE                  # 项目许可证
└── .gitignore               # Git 版本控制忽略文件
```
