import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import pymysql
import sqlalchemy
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
    nasdaq_event_FFR_df[['Date', 'FedRate', 'FedRateChange']],
    on='Date',
    how='left',
    suffixes=('', '_ffr')
)
nasdaq_merge_df['FedRate'] = nasdaq_merge_df['FedRate_ffr'].ffill()


# ── 1. 연준의 기준금리와 주가의 관계 ──────────────────────────────────────────
print("1. 연준의 기준금리와 주가의 관계 (chart)")
print()
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
print("2. 금리인상 직후 수익률 변화")
print()
# 연산
rate_up = nasdaq_event_FFR_df[nasdaq_event_FFR_df['FedRateChange'] > 0 ] # FedRateChage = 전날대비 금리 변화 (평소에는 0). 즉 금리가 상승한 날

rate_up_price_result = []
for date in rate_up['Date']:
    before = nasdaq_csv_df[nasdaq_csv_df['Date'] == date]['Close']
    after = nasdaq_csv_df[nasdaq_csv_df['Date'] == date + pd.Timedelta(days=30)]['Close']

    if len(before) > 0 and len(after) > 0: # 해당 날짜의 데이터 존재 여부 확인 (주말/공휴일이면 빈 Series -> len=0)
        change_price = (after.values[0] - before.values[0]) / before.values[0] * 100
        rate_up_price_result.append({'Date': date, 'Change(%)': round(change_price, 2)})

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
print("3. 금리인하 직후 수익률 변화")
print()
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
print()
print("평균 수익률 :", results_rate_down_after30_df['Change(%)'].mean().round(2), "%")
print()

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
print("4. 연도별 QQQ 평균 수익률 (chart)")
print()
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

# ── 5. 금리 구간별(4구간) 수익률/변동성 비교 ──────────────────────────────────────────
print("5-2. 금리 구간별(4구간) 수익률/변동성 비교")
print()
ffr_zero_group = nasdaq_merge_df[(nasdaq_merge_df['FedRate'] >= 0) & (nasdaq_merge_df['FedRate'] < 1)]['Return'].dropna()
ffr_low_group = nasdaq_merge_df[(nasdaq_merge_df['FedRate'] >= 1) & (nasdaq_merge_df['FedRate'] < 3)]['Return'].dropna()
ffr_mid_group = nasdaq_merge_df[(nasdaq_merge_df['FedRate'] >= 3) & (nasdaq_merge_df['FedRate'] < 5)]['Return'].dropna()
ffr_high_group = nasdaq_merge_df[nasdaq_merge_df['FedRate'] >= 5]['Return'].dropna()

group_labels = ['0~1%\n(Zero)', '1~3%\n(Low)', '3~5%\n(Medium)', '5%+\n(High)']
group_data = [ffr_zero_group, ffr_low_group, ffr_mid_group, ffr_high_group]

group_returns = [round(g.mean(), 4) for g in group_data]
group_volatility = [round(g.std(), 4) for g in group_data]

for label, g, r, v in zip(group_labels, group_data, group_returns, group_volatility):
    print(f"=== {label.replace(chr(10), ' ')} 구간 ===")
    print(f"평균 수익률: {r:.4f}%, 변동성(표준편차): {v:.4f}%  (n={len(g)})")
    print()

# 차트
x = range(len(group_labels))
width = 0.35

fig, ax_group = plt.subplots(figsize=(10, 6))
ax_group.bar([i - width/2 for i in x], group_returns, width, label='Avg Return(%)', color='blue')
ax_group.bar([i + width/2 for i in x], group_volatility, width, label='Volatility(%)', color='red')
ax_group.set_xticks(x)
ax_group.set_xticklabels(group_labels)
ax_group.set_ylabel('%')
ax_group.set_title('QQQ Return & Volatility by Fed Rate Group')
ax_group.legend()
plt.grid(True, axis='y', alpha=0.3)
plt.tight_layout()
plt.show()

# ── 변동성 차이 통계 검정 (Levene's test — 분산 비교에 특화) ──────────────────────
levene_stat, levene_p = stats.levene(ffr_zero_group, ffr_high_group)

print("=== FFR 0%p vs 5%p 변동성(분산) 차이 Levene 검정 ===")
print()
print(f"0% 구간 표준편차: {group_volatility[0]:.3f}%  (n={len(ffr_zero_group)})")
print(f"5% 구간 표준편차: {group_volatility[3]:.3f}%  (n={len(ffr_high_group)})")
print()
print(f"Levene statistic: {levene_stat:.3f}")
print()
print(f"p-value: {levene_p:.3f}")
print()

if levene_p < 0.05:
    print("→ 두 구간의 변동성 차이는 통계적으로 유의미함 (p < 0.05)")
else:
    print("→ 두 구간의 변동성 차이는 통계적으로 유의미하지 않음 (p >= 0.05)")

print()

# 인상 후 30일 수익률 vs 인하 후 30일 수익률 비교 (t - test)
t_stat, p_value = stats.ttest_ind(
    results_rate_up_after30_df['Change(%)'],
    results_rate_down_after30_df['Change(%)'],
    equal_var=False  # 두 그룹의 분산이 같다고 가정하지 않음 (Welch's t-test)
)

print("=== 금리 인상 vs 인하 후 30일 수익률 t-test ===")
print()
print(f"인상 그룹 평균: {results_rate_up_after30_df['Change(%)'].mean():.2f}%  (n={len(results_rate_up_after30_df)})")
print(f"인하 그룹 평균: {results_rate_down_after30_df['Change(%)'].mean():.2f}%  (n={len(results_rate_down_after30_df)})")
print()
print(f"t-statistic: {t_stat:.3f}")
print()
print(f"p-value: {p_value:.3f}")
print()

if p_value < 0.05:
    print("→ 통계적으로 유의미한 차이 있음 (p < 0.05)")
else:
    print("→ 통계적으로 유의미한 차이 없음 (p >= 0.05)")

print()

# ── 6. 금리 동결 구간 vs 변동(인상+인하) 구간 평균 수익률 비교 ──────────────────────
print("6. 금리 동결 구간 vs 변동(인상+인하) 구간 평균 수익률 비교")

frozen_group = nasdaq_merge_df[nasdaq_merge_df['FedRateChange'] == 0]['Return'].dropna()
changed_group = nasdaq_merge_df[nasdaq_merge_df['FedRateChange'] != 0]['Return'].dropna()

print(f"동결 그룹 평균: {frozen_group.mean():.3f}%  (n={len(frozen_group)})")
print(f"변동 그룹 평균: {changed_group.mean():.3f}%  (n={len(changed_group)})")
print()

t_stat3, p_value3 = stats.ttest_ind(frozen_group, changed_group, equal_var=False)

print(f"t-statistic: {t_stat3:.3f}")
print(f"p-value: {p_value3:.3f}")
print()


if p_value3 < 0.05:
    print("→ 통계적으로 유의미한 차이 있음 (p < 0.05)")
else:
    print("→ 통계적으로 유의미한 차이 없음 (p >= 0.05)")
print()

# ── 7. 월별 평균 수익률 차이 (ANOVA) ──────────────────────────────────────────

print("7. 월별 평균 수익률 차이 (ANOVA)")
print()

nasdaq_merge_df['Month'] = nasdaq_merge_df['Date'].dt.month

monthly_groups = [
    nasdaq_merge_df[nasdaq_merge_df['Month'] == m]['Return'].dropna()
    for m in range(1, 13)
]

f_stat, p_value4 = stats.f_oneway(*monthly_groups)


monthly_avg = nasdaq_merge_df.groupby('Month')['Return'].mean().round(3)
print(monthly_avg)
print()
print(f"F-statistic: {f_stat:.3f}")
print(f"p-value: {p_value4:.3f}")
print()

if p_value4 < 0.05:
    print("→ 월별 평균 수익률에 통계적으로 유의미한 차이 있음 (p < 0.05)")
else:
    print("→ 월별 평균 수익률에 통계적으로 유의미한 차이 없음 (p >= 0.05)")

print()

# 차트
fig_monthly, ax_monthly = plt.subplots(figsize=(14, 6))
colors = ['red' if x > 0 else 'blue' for x in monthly_avg]
ax_monthly.bar(monthly_avg.index, monthly_avg.values, color=colors)
ax_monthly.axhline(y=0, color='black', linewidth=0.8)
ax_monthly.set_title('QQQ Average Return by Month (2010-2024)')
ax_monthly.set_xlabel('Month')
ax_monthly.set_ylabel('Average Return (%)')
ax_monthly.set_xticks(range(1, 13))
plt.grid(True)
plt.tight_layout()
plt.show()

# ── 8. 전일 상승/하락과 당일 상승/하락의 관련성 (카이제곱 검정) ──────────────────────

print("8. 전일 상승/하락과 당일 상승/하락의 관련성 (카이제곱 검정)")
print()

# 1. 상승/하락 범주 만들기 (Return > 0이면 up, 아니면 down)
nasdaq_merge_df['Direction'] = nasdaq_merge_df['Return'].apply(lambda x: 'up' if x > 0 else 'down')

# 2. 전일 방향 컬럼 만들기 (shift로 하루 밀기)
nasdaq_merge_df['Prev_Direction'] = nasdaq_merge_df['Direction'].shift(1)

# 3. 결측치(첫 행) 제거
chi_df = nasdaq_merge_df.dropna(subset=['Direction', 'Prev_Direction'])

# 4. 교차표 만들기
cross_tab = pd.crosstab(chi_df['Prev_Direction'], chi_df['Direction'])
print("=== 교차표 ===")
print()
print(cross_tab)
print()

# 5. 카이제곱 검정
chi2_stat, p_value5, dof, expected = stats.chi2_contingency(cross_tab)

print(f"chi2-statistic: {chi2_stat:.3f}")
print(f"p-value: {p_value5:.3f}")
print()

if p_value5 < 0.05:
    print("→ 전일-당일 방향에 통계적으로 유의미한 관련성 있음 (p < 0.05)")
else:
    print("→ 전일-당일 방향에 통계적으로 유의미한 관련성 없음 (p >= 0.05)")

print()