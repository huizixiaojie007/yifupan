import akshare as ak
import baostock as bs
import matplotlib.pyplot as plt
import pandas as pd


def aa():
    # 1. 登录Baostock获取数据
    lg = bs.login()
    # 获取贵州茅台(600519)2020-2025年日线数据
    rs = bs.query_history_k_data_plus(
        "600519.SH",
        "date,open,high,low,close,volume",
        start_date="2020-01-01",
        end_date="2025-01-01",
        frequency="d",
        adjustflag="2"  # 前复权
    )
    # 转为DataFrame
    df = pd.DataFrame(rs.get_data(), columns=rs.fields)
    # 数据类型转换
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(int)
    bs.logout()

    # 2. 计算双均线（替代TA-Lib，纯pandas实现）
    df["MA5"] = df["close"].rolling(5).mean()
    df["MA20"] = df["close"].rolling(20).mean()

    # 3. 生成买卖信号
    df["signal"] = 0
    # 金叉：MA5上穿MA20
    golden_cross = (df["MA5"] > df["MA20"]) & (df["MA5"].shift(1) <= df["MA20"].shift(1))
    # 死叉：MA5下穿MA20
    death_cross = (df["MA5"] < df["MA20"]) & (df["MA5"].shift(1) >= df["MA20"].shift(1))
    df.loc[golden_cross, "signal"] = 1
    df.loc[death_cross, "signal"] = -1

    # 4. 可视化结果
    plt.figure(figsize=(12, 6))
    plt.plot(df["date"], df["close"], label="收盘价", color="blue")
    plt.plot(df["date"], df["MA5"], label="MA5", color="red")
    plt.plot(df["date"], df["MA20"], label="MA20", color="green")
    # 标记买入信号（红点）
    buy_signals = df[df["signal"] == 1]
    plt.scatter(buy_signals["date"], buy_signals["close"], color="red", marker="^", s=100)
    # 标记卖出信号（绿点）
    sell_signals = df[df["signal"] == -1]
    plt.scatter(sell_signals["date"], sell_signals["close"], color="green", marker="v", s=100)
    plt.legend()
    plt.xticks(rotation=45)
    plt.title("贵州茅台双均线策略")
    plt.tight_layout()
    plt.show()

    # 输出信号统计
    print("买入信号次数：", len(buy_signals))
    print("卖出信号次数：", len(sell_signals))
if __name__ == '__main__':
    # 测试akshare获取数据
    df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20200101", end_date="20250101")
    print(f"贵州茅台数据行数：{len(df)}")

    # 测试baostock获取数据
    lg = bs.login()
    rs = bs.query_hs300_stocks()
    print("沪深300成分股获取成功", rs)
    bs.logout()
    # aa()