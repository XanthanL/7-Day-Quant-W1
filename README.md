# 7-Day-Quant

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Backtrader](https://img.shields.io/badge/Backtrader-v1.9-green.svg)](https://www.backtrader.com/)
[![Akshare](https://img.shields.io/badge/Akshare-Latest-brightgreen.svg)](https://akshare.akfamily.xyz/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Introduction

这是一个从零构建的 Python 本地量化交易系统。项目旨在通过工程化的手段，解决从**海量数据管理**、**多因子选股**到**投资组合回测**的完整链路问题。

系统已从最初的单脚本演进为模块化架构，实现了基于 **SQLite** 的全市场数据存储、基于 **Backtrader** 的单股策略验证，以及自定义的**多股票动态再平衡**回测引擎。

## Features

### 1. 工程化数据底座
-   **全市场覆盖**: 基于 `Akshare` 获取 A 股 5000+ 股票的历史与实时行情。
-   **高效存储**: 摒弃 CSV，采用 **SQLite + SQLAlchemy** 构建本地数据库 (`quant.db`)，支持索引查询与 ACID 事务。
-   **并发增量更新**: 内置多线程下载器 (`src/data/downloader.py`)，支持断点续传与智能增量更新，大幅缩短数据同步时间。

### 2. 策略与选股 (Alpha Generation)
-   **多因子模型**: 实现基于横截面数据的选股逻辑 (`src/strategies/alpha_model.py`)。
    -   *当前因子*: **动量 (Momentum)** 与 **低波动 (Low Volatility)** 的加权评分。
-   **经典技术策略**: 内置双均线趋势跟踪 (Trend Following) 与 RSI 均值回归 (Mean Reversion) 策略。

### 3. 多维回测引擎
-   **投资组合回测 (Portfolio Backtest)**: 自研回测引擎，支持**多股票持仓**、**定期动态调仓 (Rebalancing)**、资金利用率模拟及交易成本扣除。
-   **单股深度回测**: 集成 `Backtrader` 框架，提供夏普比率、最大回撤等专业绩效分析及参数网格搜索 (Grid Search) 优化。

### 4. 实盘辅助
-   **实时监控**: 模拟实盘环境，轮询最新行情并触发策略信号报警。

## Tech Stack

-   **Core**: Python 3.8+
-   **Data**: Pandas, NumPy, Akshare, SQLAlchemy (SQLite)
-   **Backtest**: Backtrader (Event-driven), Custom Portfolio Engine (Vectorized)
-   **Viz**: Matplotlib, Seaborn
-   **Concurrency**: concurrent.futures

## Installation & Setup

1.  **克隆项目**:
    ```bash
    git clone https://github.com/XanthanL/7-Day-Quant-W1.git
    cd 7-Day-Quant-W1
    ```

2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **数据初始化 (关键步骤)**:
    首次运行前，需初始化本地数据库并下载数据。
    运行 `python main.py`，选择 **`1. 数据管理` -> `1. 全市场股票数据增量下载`**。

## Usage Guide

所有功能集成于统一的 CLI 入口：

```bash
python main.py
```

### 核心功能菜单

-   **1. 数据管理 (Data Management)**
    -   一键同步全市场数据，或检查数据库健康状态（记录数/最新日期）。

-   **2. 单股票策略回测 (Single Stock Strategy)**
    -   针对单只股票运行 Backtrader 回测（支持双均线/RSI），或进行参数优化。

-   **3. 多因子选股 (Alpha Model)**
    -   计算最新交易日的因子得分，输出当前市场最值得关注的 Top N 股票。

-   **4. 投资组合回测 (Portfolio Backtest)**
    -   **核心功能**：模拟“选股-买入-持有-换仓”的完整周期。验证多因子策略在历史时间段内的超额收益能力。

-   **5. 实时监控 (Live Monitor)**
    -   启动实盘信号监听服务。

## Deployment (Docker)

为了方便部署和环境隔离，本项目提供了 Docker 支持。

### 1. 构建 Docker 镜像

在项目根目录下执行以下命令构建 Docker 镜像。镜像名称可以自定义，例如 `quant-app`。

```bash
docker build -t quant-app .
```

### 2. 运行 Docker 容器

构建完成后，可以通过以下命令运行 Docker 容器。请注意，`quant.db` 文件通过 Volume 挂载到容器内部，以确保数据持久化且独立于容器生命周期。Streamlit 仪表盘将在容器的 8501 端口运行，并通过 `-p` 参数映射到宿主机的 8501 端口。

```bash
docker run -p 8501:8501 -v $(pwd)/quant.db:/app/quant.db --name quant-dashboard quant-app
```

**说明**:
-   `-p 8501:8501`: 将宿主机的 8501 端口映射到容器的 8501 端口。
-   `-v $(pwd)/quant.db:/app/quant.db`: 将当前目录下的 `quant.db` 文件挂载到容器内的 `/app/quant.db`。这样，你的数据将存储在宿主机上，即使容器被删除，数据也不会丢失。
-   `--name quant-dashboard`: 为你的容器指定一个名称，方便管理。
-   `quant-app`: 你构建的 Docker 镜像名称。

运行成功后，在浏览器中访问 `http://localhost:8501` 即可使用 Streamlit 仪表盘。

## Project Structure

```text
Quantifying_Test/
├── src/
│   ├── backtesting/          # 回测核心模块
│   │   ├── core.py           # Backtrader 包装类
│   │   ├── optimizer.py      # 参数优化器
│   │   └── portfolio_backtest.py # [Core] 投资组合回测引擎
│   │
│   ├── data/                 # 数据工程模块
│   │   ├── database.py       # [Core] 数据库管理器 (SQLAlchemy)
│   │   └── downloader.py     # [Core] 并发数据下载器
│   │
│   ├── strategies/           # 策略逻辑模块
│   │   ├── alpha_model.py    # [Core] 多因子选股模型
│   │   ├── backtrader_ma.py  # Backtrader 策略类
│   │   └── rsi.py            # Backtrader 策略类
│   │
│   └── monitoring/           # 实盘模块
│       └── live_monitor.py   # 实时监控脚本
│
├── quant.db                 # 本地数据库 (自动生成，git忽略)
├── main.py                  # CLI 入口
├── requirements.txt         # 依赖列表
├── README.md                # 文档
└── .gitignore               # 配置
```

## Disclaimer

**本项目仅用于计算机科学与量化交易的学习研究。** 
回测结果不代表未来收益。股市有风险，入市需谨慎。

## License

[MIT License](LICENSE)