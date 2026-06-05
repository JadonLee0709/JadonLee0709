import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
# import yfinance as yf


# ── 데이터 로드 ──────────────────────────────────────────
# qqq = yf.download('QQQ', start='2010-01-04', end='2024-10-26', auto_adjust=True)
# qqq.columns = qqq.columns.get_level_values(0)
# qqq.reset_index().to_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq.csv', index=False)

nasdaq_csv_df = pd.read_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq.csv')
nasdaq_event_FFR_df = pd.read_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq_event_FFR_ver_3.csv')

nasdaq_csv_df['Date'] = pd.to_datetime(nasdaq_csv_df['Date'])
nasdaq_event_FFR_df['Date'] = pd.to_datetime(nasdaq_event_FFR_df['Date'])
# ── 1. 연준의 기준금리와 주가의 관계 ──────────────────────────────────────────

fig, ax1 = plt.subplots(figsize=(14, 6))
ax2 = ax1.twinx()

ax1.plot(nasdaq_csv_df['Date'], nasdaq_csv_df['Close'], color='blue', label='QQQ Close')
ax2.plot(nasdaq_csv_df['Date'], nasdaq_csv_df['FedRate'], color='red', label='Fed Rate')

ax1.set_ylabel('QQQ Price (USD)', color='blue')
ax2.set_ylabel('Fed Rate (%)', color='red')

plt.title('Nasdaq Price Movement')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.grid(True)
plt.show()






# ── 최종 결과 (그래프) ──────────────────────────────────────────
plt.plot(nasdaq_csv_df['Date'], nasdaq_csv_df['Close'], label='Close')