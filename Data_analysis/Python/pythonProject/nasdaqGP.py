import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
# import yfinance as yf


# ── 데이터 로드 ──────────────────────────────────────────
# qqq = yf.download('QQQ', start='2010-01-04', end='2024-10-26', auto_adjust=True)
# qqq.columns = qqq.columns.get_level_values(0)
# qqq.reset_index().to_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq.csv', index=False)

nasdaq_csv_df = pd.read_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq.csv') #맥미니용
nasdaq_event_FFR_df = pd.read_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq_event_FFR_ver_3.csv') #맥미니용

# # nasdaq_csv_df = pd.read_csv('/Users/ihyeonho/JadonLee0709/Data_analysis/Python/pythonProject/nasdaq.csv') #맥북용
# nasdaq_event_FFR_df = pd.read_csv('/Users/ihyeonho/JadonLee0709/Data_analysis/Python/pythonProject/nasdaq_event_FFR_ver_3.csv') #맥북용

nasdaq_csv_df['Date'] = pd.to_datetime(nasdaq_csv_df['Date'])
nasdaq_event_FFR_df['Date'] = pd.to_datetime(nasdaq_event_FFR_df['Date'])
# ── 1. 연준의 기준금리와 주가의 관계 ──────────────────────────────────────────

fig_a1, ax1 = plt.subplots(figsize=(14, 6))
ax2 = ax1.twinx()

ax1.plot(nasdaq_csv_df['Date'], nasdaq_csv_df['Close'], color='blue', label='QQQ Close')
ax2.plot(nasdaq_csv_df['Date'], nasdaq_csv_df['FedRate'], color='red', label='Fed Rate')

ax1.set_ylabel('QQQ Price (USD)', color='black')
ax2.set_ylabel('Fed Rate (%)', color='black')

plt.title('Nasdaq Price Movement')
plt.xlabel('Date')
plt.ylabel('Fed Rate (%)')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
plt.legend(lines1+lines2, labels1+labels2, loc='upper left')
plt.grid(True)
plt.show()


# ── 2. 금리인상 직후 거래량 변화 ──────────────────────────────────────────


# 연산
rate_up = nasdaq_event_FFR_df[nasdaq_event_FFR_df['FedRateChange'] > 0 ]

rate_up_price_result = []
for date in rate_up['Date']:
    before = nasdaq_csv_df[nasdaq_csv_df['Date'] == date]['Close']
    after = nasdaq_csv_df[nasdaq_csv_df['Date'] == date + pd.Timedelta(days=30)]['Close']

    if len(before) > 0 and len(after) > 0:
        change_volume = (after.values[0] - before.values[0]) / before.values[0] * 100
        rate_up_price_result.append({'Date': date, 'Change(%)': round(change_volume, 2)})

print(pd.DataFrame(rate_up_price_result))

results_df = pd.DataFrame(rate_up_price_result)

fig5, ax5 = plt.subplots(figsize=(8, 6))
ax5.axis('off')
table = ax5.table(
    cellText=results_df.values,
    colLabels=results_df.columns,
    loc='center',
    cellLoc='center'
)
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.5)
ax5.set_title('Nasdaq movement for 30 days after announced FFR ', color='black')
plt.show()


# 차트
fig_a3, ax3 = plt.subplots(figsize=(14, 6))
ax4 = ax3.twinx()

# 그래프 곡선
ax3.plot(nasdaq_csv_df['Date'], nasdaq_csv_df['Volume'], color='blue', label='Volume')
ax4.plot(nasdaq_csv_df['Date'], nasdaq_csv_df['FedRate'], color='red', label='FedRate')
# 그래프 범례
lines3, labels3 = ax3.get_legend_handles_labels()
lines4, labels4 = ax4.get_legend_handles_labels()
plt.legend(lines3+lines4, labels3+labels4, loc='upper left')

# 그래프
ax3.set_title('Nasdaq Volume')
ax3.set_xlabel('Date',color='black')
ax3.set_ylabel('Volume (USD)', color='black')
ax4.set_ylabel('Fed Rate (%)', color='black')

plt.grid(True)
plt.show()


