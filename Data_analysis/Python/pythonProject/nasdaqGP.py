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

fig_trend, ax_trend_1 = plt.subplots(figsize=(14, 6))
ax_trend_2 = ax_trend_1.twinx()

ax_trend_1.plot(nasdaq_merge_df['Date'], nasdaq_merge_df['Close'], color='blue', label='QQQ Close') # 날짜에 따른 종가의 변화
ax_trend_2.plot(nasdaq_merge_df['Date'], nasdaq_merge_df['FedRate'], color='red', label='Fed Rate') # 날짜에 따른 연준금리의 변화

ax_trend_1.set_ylabel('QQQ Price (USD)', color='black')
ax_trend_2.set_ylabel('Fed Rate (%)', color='black')

plt.title('QQQ ETF Price Movement')
plt.xlabel('Date')
plt.ylabel('Fed Rate (%)')
lines1, labels1 = ax_trend_1.get_legend_handles_labels()
lines2, labels2 = ax_trend_2.get_legend_handles_labels()
plt.legend(lines1+lines2, labels1+labels2, loc='upper left')
plt.grid(True)
plt.show()



# ── 2. 금리인상 직후 수익률 변화 ──────────────────────────────────────────


# 연산
rate_up = nasdaq_event_FFR_df[nasdaq_event_FFR_df['FedRateChange'] > 0 ] # FedRateChage = 전날대비 금리 변화 (평소에는 0). 즉 금리가 상승한 날

rate_up_price_result = []
for date in rate_up['Date']:
    before = nasdaq_csv_df[nasdaq_csv_df['Date'] == date]['Close']
    after = nasdaq_csv_df[nasdaq_csv_df['Date'] == date + pd.Timedelta(days=30)]['Close']

    if len(before) > 0 and len(after) > 0: # 해당 날짜의 데이터 존재 여부 확인 (주말/공휴일이면 빈 Series -> len=0)
        change_price = (after.values[0] - before.values[0]) / before.values[0] * 100
        rate_up_price_result.append({'Date': date, 'Change(%)': round(change_price, 2)})

print("Rate up price movement")
print()
print(pd.DataFrame(rate_up_price_result))
print()

results_rate_up_after30_df = pd.DataFrame(rate_up_price_result)

# 금리 변동 후 30일간 QQQ 수익률 표

fig_rate_up_after30, ax_rate_up_after30 = plt.subplots(figsize=(8, 6))
ax_rate_up_after30.axis('off')
rate_up_after30_table_gp = ax_rate_up_after30.table(
    cellText=results_rate_up_after30_df.values,
    colLabels=results_rate_up_after30_df.columns,
    loc='center',
    cellLoc='center')

rate_up_after30_table_gp.auto_set_font_size(False)
rate_up_after30_table_gp.set_fontsize(10)
rate_up_after30_table_gp.scale(1.2, 1.5)
ax_rate_up_after30.set_title('QQQ ETF Price Movement for 30 days after announced FFR ', color='black')
plt.show()


## 차트
fig_rate_up_after30_chart, ax_rate_up_after30_chart = plt.subplots(figsize=(14, 6))

# 그래프 곡선
colors = ['blue' if x < 0 else 'red' for x in results_rate_up_after30_df['Change(%)']]
ax_rate_up_after30_chart.bar(results_rate_up_after30_df['Date'].astype(str), results_rate_up_after30_df['Change(%)'], color=colors)

# 그래프 범례
ax_rate_up_after30_chart.axhline(y=0, color='black', linewidth=0.8)

# 그래프
ax_rate_up_after30_chart.set_title('QQQ ETF Price Movement for 30 days after announced FFR')
ax_rate_up_after30_chart.set_xlabel('Date', color='black')
ax_rate_up_after30_chart.set_ylabel('Change (%)', color='black')

plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(True)
plt.show()

# ── 3. 금리인하 직후 수익률 변화 ──────────────────────────────────────────
rate_down = nasdaq_event_FFR_df[nasdaq_event_FFR_df['FedRateChange'] < 0 ]


rate_down_after30_result = []
for date in rate_down['Date']:
    before = nasdaq_csv_df[nasdaq_csv_df['Date'] == date]['Close']
    after = nasdaq_csv_df[nasdaq_csv_df['Date'] == date + pd.Timedelta(days=30)]['Close']

    if len(before) > 0 and len(after) > 0:
        change_price = (after.values[0] - before.values[0]) / before.values[0] * 100
        rate_down_after30_result.append({'Date': date, 'Change(%)': round(change_price, 2)})

results_rate_down_after30_df = pd.DataFrame(rate_down_after30_result)
print(results_rate_down_after30_df)
print("평균 수익률 :", results_rate_down_after30_df['Change(%)'].mean().round(2), "%")

# 차트
fig_rate_down_after30_chart, ax_rate_down_after30_chart = plt.subplots(figsize=(14, 6))
colors = ['blue' if x<0 else 'red' for x in results_rate_down_after30_df['Change(%)']]
ax_rate_down_after30_chart.bar(results_rate_down_after30_df['Date'].astype(str), results_rate_down_after30_df['Change(%)'], color=colors)
ax_rate_down_after30_chart.axhline(y=0, color='black', linewidth=0.8)
ax_rate_down_after30_chart.set_title('QQQ ETF Price Movement for 30 days after FFR Cut')
ax_rate_down_after30_chart.set_xlabel('Date', color ='black')
ax_rate_down_after30_chart.set_ylabel('Change (%)', color ='black')
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(True)
plt.show()

# 표

results_rate_down_after30_df = pd.DataFrame(rate_down_after30_result)

fig_rate_down_after30_table, ax_rate_down_after30_table = plt.subplots(figsize=(8, 6))
ax_rate_down_after30_table.axis('off')
rate_down_after30_table_gp = ax_rate_down_after30_table.table(
    cellText=results_rate_down_after30_df.values,
    colLabels=results_rate_down_after30_df.columns,
    loc='center',
    cellLoc='center')

rate_down_after30_table_gp.auto_set_font_size(False)
rate_down_after30_table_gp.set_fontsize(10)
rate_down_after30_table_gp.scale(1.2, 1.5)
ax_rate_down_after30_table.set_title('QQQ ETF Price Movement for 30 days after announced FFR ', color='black')
plt.show()


# ── 4. 연도별 QQQ 평균 수익률 ──────────────────────────────────────────

nasdaq_merge_df['Return'] = nasdaq_merge_df['Close'].pct_change() * 100 # ex) pct_change() (다음행-현재행)/현재행 즉 변화율
nasdaq_merge_df['Year'] = nasdaq_merge_df['Date'].dt.year
nasdaq_groupby = nasdaq_merge_df.groupby('Year')['Return'].mean().round(2)

# 차트
fig_annual_average_chart, ax_annual_average_chart = plt.subplots(figsize=(14, 6))
colors = ['red' if x > 0 else 'blue' for x in nasdaq_groupby]
ax_annual_average_chart.bar(nasdaq_groupby.index, nasdaq_groupby.values, color=colors)
ax_annual_average_chart.axhline(y=0, color='black', linewidth=0.8)
ax_annual_average_chart.set_title('QQQ Annual Performance by Year')
ax_annual_average_chart.set_xlabel('Year', color='black')
ax_annual_average_chart.set_ylabel('Return (%)', color='black')
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
# nasdaq_merge_df['Return'] = nasdaq_merge_df['Close'].pct_change() * 100
# nasdaq_FedRate_0 = nasdaq_merge_df[nasdaq_merge_df ['FedRate'] < 0.5]
# nasdaq_FedRate_5 = nasdaq_merge_df[nasdaq_merge_df ['FedRate'] > 5 ]
# #
# print("금리 0% 구간 평균 수익률",nasdaq_FedRate_0['Return'].mean().round(2),"%")
# print(nasdaq_FedRate_0['Return'].std().round(2))
# print("금리 5% 구간 평균 수익률",nasdaq_FedRate_5['Return'].mean().round(2),"%")
# print(nasdaq_FedRate_5['Return'].std().round(2))
#
# nasdaq_merge_df['Year'] = nasdaq_merge_df['Date'].dt.year
# nasdaq_groupby = nasdaq_merge_df.groupby('Year')['Return'].mean().round(2)
# print(nasdaq_groupby)
