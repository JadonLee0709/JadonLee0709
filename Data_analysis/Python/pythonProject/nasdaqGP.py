import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
# import yfinance as yf


# ── 데이터 로드 ──────────────────────────────────────────
# qqq = yf.download('QQQ', start='2010-01-04', end='2024-10-26', auto_adjust=True)
# qqq.columns = qqq.columns.get_level_values(0)
# qqq.reset_index().to_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq.csv', index=False)

#nasdaq_csv_df = pd.read_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq.csv') #맥미니용
#nasdaq_event_FFR_df = pd.read_csv('/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq_event_FFR_ver_3.csv') #맥미니용

nasdaq_csv_df = pd.read_csv('/Users/ihyeonho/JadonLee0709/Data_analysis/Python/pythonProject/nasdaq.csv') #맥북용
nasdaq_event_FFR_df = pd.read_csv('/Users/ihyeonho/JadonLee0709/Data_analysis/Python/pythonProject/nasdaq_event_FFR_ver_3.csv') #맥북용

nasdaq_csv_df['Date'] = pd.to_datetime(nasdaq_csv_df['Date'])
nasdaq_event_FFR_df['Date'] = pd.to_datetime(nasdaq_event_FFR_df['Date'])


nasdaq_merge_df = pd.merge(
    nasdaq_csv_df,
    nasdaq_event_FFR_df[['Date', 'FedRate']],
    on='Date',
    how='left',
    suffixes=('', '_ffr')
)
nasdaq_merge_df['FedRate'] = nasdaq_merge_df['FedRate_ffr'].ffill()


# ── 1. 연준의 기준금리와 주가의 관계 ──────────────────────────────────────────

fig_a1, ax1 = plt.subplots(figsize=(14, 6))
ax2 = ax1.twinx()

ax1.plot(nasdaq_merge_df['Date'], nasdaq_merge_df['Close'], color='blue', label='QQQ Close')
ax2.plot(nasdaq_merge_df['Date'], nasdaq_merge_df['FedRate'], color='red', label='Fed Rate')

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
        change_price = (after.values[0] - before.values[0]) / before.values[0] * 100
        rate_up_price_result.append({'Date': date, 'Change(%)': round(change_price, 2)})

print(pd.DataFrame(rate_up_price_result))

results_df = pd.DataFrame(rate_up_price_result)

# 금리 변동 후 30일간 나스닥 수익률 표
fig4, ax4 = plt.subplots(figsize=(8, 6))
ax4.axis('off')
table = ax4.table(
    cellText=results_df.values,
    colLabels=results_df.columns,
    loc='center',
    cellLoc='center')

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1.2, 1.5)
ax4.set_title('Nasdaq movement for 30 days after announced FFR ', color='black')
plt.show()


## 차트
fig_a3, ax3 = plt.subplots(figsize=(14, 6))

# 그래프 곡선
colors = ['blue' if x < 0 else 'red' for x in results_df['Change(%)']]
ax3.bar(results_df['Date'].astype(str), results_df['Change(%)'], color=colors)

# 그래프 범례
ax3.axhline(y=0, color='black', linewidth=0.8)

# 그래프
ax3.set_title('Nasdaq movement for 30 days after announced FFR')
ax3.set_xlabel('Date', color='black')
ax3.set_ylabel('Change (%)', color='black')

plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(True)
plt.show()

# ── 3. 연도별 QQQ 평균 수익률 ──────────────────────────────────────────

nasdaq_merge_df['Return'] = nasdaq_merge_df['Close'].pct_change() * 100
nasdaq_merge_df['Year'] = nasdaq_merge_df['Date'].dt.year
nasdaq_groupby = nasdaq_merge_df.groupby('Year')['Return'].mean().round(2)

fig_a4, ax4_bar = plt.subplots(figsize=(14, 6))
colors = ['red' if x >0 else 'blue' for x in nasdaq_groupby]
ax4_bar.bar(nasdaq_groupby.index, nasdaq_groupby.values, color=colors)
ax4_bar.axhline(y=0, color='black', linewidth=0.8)
ax4_bar.set_title('QQQ Annual Average Daily Return by Year')
ax4_bar.set_xlabel('Year', color='black')
ax4_bar.set_ylabel('Return (%)', color='black')
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(True)
plt.show()

# ## 아래는 계산 아이디어 끄적거린것임
#
# # 금리 오른날 찾기
# print("전날보다 금리가 오른 날")
# nasdaq_FFR_diff = nasdaq_csv_df[nasdaq_csv_df['FedRate'].diff() > 0 ][['Date','FedRate']]
# print(nasdaq_FFR_diff)
#
# # 금리 인상일 전 후 5일간 Close값 비교
#
# rate_up_idx_5days = nasdaq_csv_df[nasdaq_csv_df['FedRate'].diff() > 0 ].index
#
# results_rate_up_idx_5days = []
# for idx in rate_up_idx_5days:
#     before = nasdaq_csv_df.iloc[idx-5:idx]['Close'].mean()
#     after = nasdaq_csv_df.iloc[idx:idx+5]['Close'].mean()
#     date = nasdaq_csv_df.iloc[idx]['Date']
#     results_rate_up_idx_5days.append({'Date': date, 'Before': round(before, 2), 'After': round(after, 2)})
#
# print(pd.DataFrame(results_rate_up_idx_5days))
#
# # 금리 인상일 전 후 30일단 Close값 비교
#
# rate_up_idx_30days = nasdaq_csv_df[nasdaq_csv_df['FedRate'].diff() > 0 ].index
#
# results_rate_up_idx_30days = []
# for idx in rate_up_idx_30days:
#     before = nasdaq_csv_df.iloc[idx-30:idx]['Close'].mean()
#     after = nasdaq_csv_df.iloc[idx:idx+30]['Close'].mean()
#     date = nasdaq_csv_df.iloc[idx]['Date']
#     results_rate_up_idx_30days.append({'Date': date, 'Before': round(before, 2), 'After': round(after, 2)})
#
# print(pd.DataFrame(results_rate_up_idx_30days))
#
# # 금리 인상 후 30일간 Close 변화율(%)
#
# df_30 = pd.DataFrame(results_rate_up_idx_30days)
# df_30['Change(%)'] = ((df_30['After'] - df_30['Before']) / df_30['Before'] * 100).round(2)
# print(df_30)
# print("평균 변화율 :", df_30['Change(%)'].mean().round(2), "%")

# print()
nasdaq_merge_df['Return'] = nasdaq_merge_df['Close'].pct_change() * 100
# nasdaq_FedRate_0 = nasdaq_merge_df[nasdaq_merge_df ['FedRate'] < 0.5]
# nasdaq_FedRate_5 = nasdaq_merge_df[nasdaq_merge_df ['FedRate'] > 5 ]
#
# print("금리 0% 구간 평균 수익률",nasdaq_FedRate_0['Return'].mean().round(2),"%")
# print("금리 5% 구간 평균 수익률",nasdaq_FedRate_5['Return'].mean().round(2),"%")

nasdaq_merge_df['Year'] = nasdaq_merge_df['Date'].dt.year
nasdaq_groupby = nasdaq_merge_df.groupby('Year')['Return'].mean().round(2)
print(nasdaq_groupby)