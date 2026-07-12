# SQL 분석

pandas로 수행한 통계 분석 일부를 SQL로 재현하여, 데이터베이스 조작 및 분석 역량을 보여주는 섹션입니다.

- **데이터베이스:** `nasdaq_portfolio` (MySQL)
- **테이블:** `nasdaq` (일별 시세 + Fed 금리, 3,729행), `nasdaq_event_ffr_ver_3` (금리 변경 이벤트 26건 포함)
- **데이터 범위:** 2010-01-04 ~ 2024-10-25
- **전체 쿼리 코드:** [`nasdaqGP.sql`](./nasdaqGP.sql)

> **집계 기준 참고**
> - 일별 수익률은 `LAG()`로 전일 종가 대비 계산하며, 첫 거래일은 전일이 없어 제외됩니다 (유효 표본 3,728일).
> - MySQL의 `STDDEV()`는 모표준편차(population) 기준입니다. pandas `.std()`(기본 ddof=1, 표본표준편차)와는 표본이 작을수록 값이 달라질 수 있습니다.

---

## Q1. 금리 구간별 나스닥 수익률·변동성 비교

**분석 질문:** Fed 금리 수준(0~1% / 1~3% / 3~5% / 5%+)에 따라 나스닥 일별 수익률과 변동성에 차이가 있는가?

**사용 기법:** `LAG()` 윈도우 함수로 일별 수익률 계산, `CASE WHEN`으로 금리 구간 분류, 서브쿼리 + `GROUP BY`로 구간별 집계

```sql
SELECT
    RateGroup,
    COUNT(*) AS TradingDays,
    ROUND(AVG(DailyReturn), 4) AS AvgReturn_pct,
    ROUND(STDDEV(DailyReturn), 4) AS Volatility
FROM (
    SELECT
        Date,
        FedRate,
        (Close - LAG(Close) OVER (ORDER BY Date)) 
            / LAG(Close) OVER (ORDER BY Date) * 100 AS DailyReturn,
        CASE
            WHEN FedRate < 1 THEN 1
            WHEN FedRate < 3 THEN 2
            WHEN FedRate < 5 THEN 3
            ELSE 4
        END AS RateGroupOrder,
        CASE
            WHEN FedRate < 1 THEN '0~1% (Zero Rate)'
            WHEN FedRate < 3 THEN '1~3% (Low Rate)'
            WHEN FedRate < 5 THEN '3~5% (Medium Rate)'
            ELSE '5%+ (High Rate)'
        END AS RateGroup
    FROM nasdaq
) AS sub
WHERE DailyReturn IS NOT NULL
GROUP BY RateGroup, RateGroupOrder
ORDER BY RateGroupOrder;
```

**결과:**

| 구간 | 거래일 수 | 평균 수익률 | 변동성 |
|---|---|---|---|
| 0~1% (제로금리) | 2,349 | 0.0774% | 1.2434 |
| 1~3% (저금리) | 851 | 0.0467% | 1.4144 |
| 3~5% (중금리) | 125 | 0.0764% | 1.7669 |
| 5%+ (고금리) | 403 | 0.1242% | 1.0737 |

*구간별 거래일 합계 3,728일 = 전체 유효 표본과 일치 (누락 없음 검증)*

**인사이트:**
- 고금리(5%+) 구간의 평균 수익률이 가장 높고(0.1242%), 변동성은 3~5%(중금리) 구간이 가장 높음(1.7669).
- 다만 5%+ 구간은 대부분 2023~2024년(나스닥 강세장)에 해당하여, 이 결과가 금리의 효과라기보다 **시기 효과일 가능성**이 큼 (교란 변수 존재).
- 거래일 분포가 극단(제로금리 2,349일 vs 중금리 125일)에 몰려 있어, 금리 수준 단독으로는 뚜렷한 패턴이 확인되지 않음.

---

## Q2. 금리 인상/인하 이벤트 후 30일 나스닥 수익률 비교

**분석 질문:** 금리 인상/인하 발표 후 30일간 나스닥 수익률에 차이가 있는가?

**사용 기법:** self-join(같은 테이블을 이벤트 당일 `n1`, 30일 후 `n2`로 두 번 조인), 스칼라 서브쿼리 `MIN(Date)`로 비거래일 보정

> "30일 후"는 **캘린더 기준 30일 경과 후 첫 거래일**의 종가를 사용 (주말/공휴일 보정).

```sql
-- 이벤트별 상세 내역
SELECT
    e.Date AS EventDate,
    e.FedRateChange,
    CASE 
        WHEN e.FedRateChange > 0 THEN 'Rate UP'
        ELSE 'Rate Down'
    END AS ChangeType,
    n1.Close AS CloseOnEvent,
    n2.Close AS CloseAfter30d,
    ROUND((n2.Close - n1.Close) / n1.Close * 100, 2) AS Return30d_pct
FROM nasdaq_event_ffr_ver_3 e
JOIN nasdaq n1 ON n1.Date = e.Date
JOIN nasdaq n2 ON n2.Date = (
    SELECT MIN(Date) FROM nasdaq WHERE Date >= DATE_ADD(e.Date, INTERVAL 30 DAY)
)
WHERE e.FedRateChange != 0
ORDER BY e.Date;

-- 인상/인하 그룹별 평균 요약
SELECT
    ChangeType,
    COUNT(*) AS EventCount,
    ROUND(AVG(Return30d_pct), 2) AS AvgReturn30d_pct,
    ROUND(STDDEV(Return30d_pct), 2) AS StdDev
FROM ( /* 위와 동일한 서브쿼리 */ ) AS sub
GROUP BY ChangeType;
```

**결과:**

| 유형 | 이벤트 수 | 평균 30일 수익률 | 표준편차 |
|---|---|---|---|
| 인상 | 20 | +0.45% | 5.75 |
| 인하 | 6 | +3.33% | 10.61 |

*이벤트 26건 전부 시세 테이블과 정상 조인됨 (누락 없음 검증)*

**인사이트:**
- 인하 후 평균 수익률(+3.33%)이 인상 후(+0.45%)보다 높으나, 편차가 크고 인하 표본이 6건에 불과해 차이를 일반화하기 어려움.
- **인하 그룹 평균 +3.33%는 pandas 분석에서 산출한 값과 일치** — 동일 분석을 두 도구로 교차 검증함.
- 통계적 유의성 검정(독립표본 t-test)은 pandas(scipy)에서 수행: p=0.594로 유의미한 차이 아님.

---

## Q3. 연도별 나스닥 평균 일별 수익률 및 변동성

**분석 질문:** 연도별로 나스닥 수익률/변동성에 어떤 트렌드가 있는가?

**사용 기법:** `LAG()`로 일별 수익률 계산, `YEAR()` 함수로 연도별 `GROUP BY`

```sql
SELECT
    YEAR(Date) AS Year,
    COUNT(*) AS TradingDays,
    ROUND(AVG(DailyReturn), 4) AS AvgDailyReturn_pct,
    ROUND(STDDEV(DailyReturn), 4) AS Volatility
FROM (
    SELECT
        Date,
        (Close - LAG(Close) OVER (ORDER BY Date))
            / LAG(Close) OVER (ORDER BY Date) * 100 AS DailyReturn
    FROM nasdaq
) AS sub
WHERE DailyReturn IS NOT NULL
GROUP BY YEAR(Date)
ORDER BY Year;
```

**결과 (전체 15개 연도):**

| 연도 | 거래일 수 | 평균 일별 수익률 | 변동성 |
|---|---|---|---|
| 2010 | 251 | 0.0747% | 1.2128 |
| 2011 | 252 | 0.0247% | 1.4899 |
| 2012 | 250 | 0.0712% | 0.9638 |
| 2013 | 252 | 0.1269% | 0.7691 |
| 2014 | 252 | 0.0734% | 0.8693 |
| 2015 | 252 | 0.0421% | 1.1237 |
| 2016 | 252 | 0.0324% | 1.0169 |
| 2017 | 251 | 0.1148% | 0.6485 |
| 2018 | 251 | 0.0099% | 1.4392 |
| 2019 | 252 | 0.1358% | 1.0179 |
| 2020 | 253 | 0.1815% | 2.2402 |
| 2021 | 252 | 0.1028% | 1.1454 |
| **2022** | 251 | **-0.1365%** | 2.0212 |
| 2023 | 250 | 0.1814% | 1.1232 |
| 2024* | 207 | 0.1004% | 1.1257 |

*2024년은 10월 25일까지 데이터 기준 (연간 미완결)*

**인사이트:**
- 2010~2024년 중 **2022년만 유일하게 마이너스 평균 수익률**을 기록 — pandas 연도별 집계에서 확인한 핵심 결론과 일치.
- 2022년 변동성(2.0212)은 2020년 코로나 시기(2.2402)에 이어 두 번째로 높아, 급격한 금리 인상 시기의 시장 충격을 보여줌.

---

## Q4. LAG() + 사용자 변수를 활용한 금리 변화 시점 감지

**분석 질문:** 이벤트 테이블 없이, 원본 시세 데이터만으로 금리 변화 시점을 감지할 수 있는가?

**사용 기법:** `LAG()`로 전일 대비 값 비교, 사용자 변수(`@변수`, `:=`)로 순번 부여

```sql
SET @change_count = 0;

SELECT
    Date,
    FedRate,
    PrevFedRate,
    ROUND(FedRate - PrevFedRate, 2) AS RateChange,
    (@change_count := @change_count + 1) AS ChangeSequence
FROM (
    SELECT
        Date,
        FedRate,
        LAG(FedRate) OVER (ORDER BY Date) AS PrevFedRate
    FROM nasdaq
) AS sub
WHERE FedRate != PrevFedRate
ORDER BY Date;
```

**결과:** 원본 `nasdaq` 테이블만으로 **총 26건**의 금리 변화 시점을 감지 — 이벤트 테이블(`nasdaq_event_ffr_ver_3`)의 금리 변경 26건(인상 20 / 인하 6)과 **100% 일치**. 가공된 이벤트 데이터 없이도 윈도우 함수만으로 동일한 정보를 도출할 수 있음을 확인.

---

## 데이터 정합성 검증 노트

작업 과정에서 초기 적재 시 `nasdaq` 테이블에 데이터가 중복 적재(7,458행 = 2배)된 것을 구간별 거래일 합계 검증으로 발견하고, `TRUNCATE` 후 단일 재적재(3,729행)로 정정했습니다. 이후 두 환경(Mac mini / MacBook)에서 동일 쿼리를 실행하여 모든 결과값이 일치함을 확인했습니다.

**교차 검증 요약:**

| 검증 항목 | 결과 |
|---|---|
| Q1 구간별 거래일 합계 = Q3 연도별 거래일 합계 = 3,728 | ✅ 일치 |
| Q2 이벤트 수(20+6) = Q4 감지 건수(26) = 이벤트 테이블 건수 | ✅ 일치 |
| Q2 인하 평균(+3.33%) = pandas 분석 값 | ✅ 일치 |
| Q3 "2022년 유일 마이너스" = pandas 핵심 결론 | ✅ 일치 |
| 두 환경(Mac mini / MacBook) 간 전체 결과 | ✅ 일치 |
