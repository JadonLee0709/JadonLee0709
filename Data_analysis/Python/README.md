# Python 분석

pandas 기반 데이터 전처리, 시각화, 그리고 scipy를 활용한 5가지 통계 검정을 수행한 폴더입니다.

- **분석 코드:** [`pythonProject/nasdaqGP.py`](./pythonProject/nasdaqGP.py)
- **사용 라이브러리:** pandas, matplotlib, scipy.stats
- **프로젝트 전체 개요:** [루트 README](../README.md) 참고

---

## 1. 데이터 전처리

거래일 기준(QQQ 시세)과 이벤트 기준(FFR 금리)의 두 데이터를 날짜로 병합했습니다.

```python
nasdaq_merge_df = pd.merge(
    nasdaq_csv_df,
    nasdaq_event_FFR_df[['Date', 'FedRate', 'FedRateChange']],
    on='Date',
    how='left',
    suffixes=('', '_ffr')
)
nasdaq_merge_df['FedRate'] = nasdaq_merge_df['FedRate_ffr'].ffill()
```

**포인트:** 금리 데이터에 `ffill()`을 쓴 이유 — 금리는 "발표 후 다음 변경까지 유지"되는 값이라, 빈 날짜를 직전 값으로 채우는 것이 데이터 성격에 부합.

```python
# 일별 수익률 파생변수
nasdaq_merge_df['Return'] = nasdaq_merge_df['Close'].pct_change() * 100
```

---

## 2. 시각화

| 차트 | 기법 | 목적 |
|---|---|---|
| QQQ 종가 vs Fed 금리 | `twinx()` 이중축 (`ax_trend_1`, `ax_trend_2`) | 단위가 다른 두 시계열을 한 화면에 비교 |
| 인상/인하 후 30일 수익률 | 이벤트별 막대 + 조건부 색상 | 개별 이벤트의 수익률 분포 확인 |
| 연간 수익률 | `groupby('Year')['Return'].mean()` + bar | 연도별 성과 (2022년 유일 마이너스 확인) |
| 월별 평균 수익률 | `groupby('Month')` + 조건부 색상 | 계절성 시각 확인 |

*(차트 이미지는 추후 `image/` 폴더에 추가 예정)*

---

## 3. 통계 검정 (5가지 가설 검증)

### 질문 1. 금리 인상 후 30일 vs 인하 후 30일 수익률 차이 — 독립표본 t-test

이벤트 날짜 기준 30일 후 종가로 수익률을 계산했습니다. 정확히 30일 후가 비거래일(주말/공휴일)인 이벤트는 계산에서 제외하는 방식을 사용했습니다.

```python
rate_up = nasdaq_event_FFR_df[nasdaq_event_FFR_df['FedRateChange'] > 0]

rate_up_price_result = []
for date in rate_up['Date']:
    before = nasdaq_csv_df[nasdaq_csv_df['Date'] == date]['Close']
    after = nasdaq_csv_df[nasdaq_csv_df['Date'] == date + pd.Timedelta(days=30)]['Close']

    if len(before) > 0 and len(after) > 0:  # 비거래일이면 빈 Series → 제외
        change_price = (after.values[0] - before.values[0]) / before.values[0] * 100
        rate_up_price_result.append({'Date': date, 'Change(%)': round(change_price, 2)})
```

```python
t_stat, p_value = stats.ttest_ind(
    results_rate_up_after30_df['Change(%)'],
    results_rate_down_after30_df['Change(%)'],
    equal_var=False  # Welch's t-test (두 그룹 분산이 같다고 가정하지 않음)
)
# 결과: p = 0.594
```

- 인하 후 평균 +3.33% vs 인상 후 +0.45% — 수치상 차이는 있으나 **유의하지 않음**
- 원인: 인하 표본이 6건에 불과해 검정력 부족 → 질문 3으로 보완 설계

### 질문 2. 금리 0%대 vs 5%대 구간 변동성 차이 — Levene's test

```python
ffr_0_group = nasdaq_merge_df[(nasdaq_merge_df['FedRate'] >= 0) & (nasdaq_merge_df['FedRate'] < 1)]['Return'].dropna()
ffr_5_group = nasdaq_merge_df[(nasdaq_merge_df['FedRate'] >= 5) & (nasdaq_merge_df['FedRate'] < 6)]['Return'].dropna()

levene_stat, levene_p = stats.levene(ffr_0_group, ffr_5_group)
# 결과: p = 0.288
```

- 0%대 변동성 1.244 vs 5%대 1.075 — **통계적으로 유의하지 않음**
- t-test가 아닌 Levene을 쓴 이유: 비교 대상이 평균이 아니라 **분산(변동성)**이기 때문

### 질문 3. 금리 동결 구간 vs 변동 구간 평균 수익률 — 독립표본 t-test

```python
frozen_group = nasdaq_merge_df[nasdaq_merge_df['FedRateChange'] == 0]['Return'].dropna()
changed_group = nasdaq_merge_df[nasdaq_merge_df['FedRateChange'] != 0]['Return'].dropna()

t_stat3, p_value3 = stats.ttest_ind(frozen_group, changed_group, equal_var=False)
# 결과: p = 0.443
```

- 질문 1의 표본 부족(인하 6건)을 보완하기 위해 인상+인하를 묶어 변동 그룹(n=26)으로 확장
- 동결 평균 0.079% vs 변동 -0.388% — 여전히 **유의하지 않음**

### 질문 4. 월별(1~12월) 평균 수익률 차이 — ANOVA

```python
nasdaq_merge_df['Month'] = nasdaq_merge_df['Date'].dt.month

monthly_groups = [
    nasdaq_merge_df[nasdaq_merge_df['Month'] == m]['Return'].dropna()
    for m in range(1, 13)
]

f_stat, p_value4 = stats.f_oneway(*monthly_groups)
# 결과: p = 0.711
```

- 12개 그룹을 동시에 비교해야 하므로 t-test 반복이 아닌 **ANOVA** 사용 (다중비교 문제 회피)
- 7월(+0.199%) 최고, 9월(-0.034%) 유일한 마이너스 — **유의하지 않음**

### 질문 5. 전일 상승/하락과 당일 상승/하락의 연관성 — 카이제곱 검정

```python
nasdaq_merge_df['Direction'] = nasdaq_merge_df['Return'].apply(lambda x: 'up' if x > 0 else 'down')
nasdaq_merge_df['Prev_Direction'] = nasdaq_merge_df['Direction'].shift(1)

chi_df = nasdaq_merge_df.dropna(subset=['Direction', 'Prev_Direction'])
cross_tab = pd.crosstab(chi_df['Prev_Direction'], chi_df['Direction'])

chi2_stat, p_value5, dof, expected = stats.chi2_contingency(cross_tab)
# 결과: p = 0.858
```

- 수익률 크기가 아닌 **방향(범주형)** 간 독립성 검정이므로 카이제곱 사용
- 전일 방향과 당일 방향은 **독립** — 단기 모멘텀 없음

---

## 4. 종합 해석

5개 검정 모두 non-significant라는 결과는 실패가 아니라 그 자체로 결론입니다:

> **금리 단일 변수로는 나스닥 단기 수익률/변동성을 유의미하게 설명하기 어렵다.**

이는 시장이 금리 발표를 사전에 가격에 반영(pricing-in)한다는 효율적 시장 관점과도 부합합니다. 각 검정에서 어떤 방법을 왜 선택했는지 — 평균 비교→t-test, 분산 비교→Levene, 다중 그룹→ANOVA, 범주 독립성→카이제곱 — 가 이 분석의 핵심입니다.

---

## SQL 분석과의 차이 참고

- **30일 수익률 계산 방식**: Python은 "정확히 30일 후가 거래일인 이벤트만 계산"하는 방식, SQL(Q2)은 "30일 경과 후 첫 거래일로 보정"하는 방식으로 접근이 다름. 두 방식 모두 인하 그룹 평균 +3.33%로 동일한 결론에 도달함
- **변동성 계산**: pandas `.std()`는 표본표준편차(ddof=1), MySQL `STDDEV()`는 모표준편차 기준

---

## 한계점

- 이벤트 표본 소수(인상 20건, 인하 6건)로 검정력 낮음
- 상관관계 분석이며 인과 증명 아님
- 전체 한계점 및 개선 방향은 [루트 README](../README.md) 참고