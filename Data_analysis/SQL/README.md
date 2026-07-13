# SQL 분석

pandas로 수행한 통계 분석 일부를 SQL로 재현하여, 데이터베이스 조작 및 분석 역량을 보여주는 섹션입니다.

- 데이터베이스: `nasdaq_portfolio` (MySQL)
- 테이블: `nasdaq` (일별 시세 + Fed 금리), `nasdaq_event_ffr_ver_3` (금리 변경 이벤트)
- 전체 쿼리 코드: [`nasdaqGP.sql`](./nasdaqGP.sql)

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
| 0~1% (제로금리) | 4,699 | 0.0387% | 0.88 |
| 1~3% (저금리) | 1,702 | 0.0234% | 1.00 |
| 3~5% (중금리) | 250 | 0.0382% | 1.25 |
| 5%+ (고금리) | 806 | 0.0621% | 0.76 |

**인사이트:** 고금리(5%+) 구간에서 오히려 평균 수익률이 가장 높고 변동성은 가장 낮음. 거래일 분포가 극단(제로금리 4,699일 vs 중금리 250일)에 몰려있어, 금리 수준 단독으로는 뚜렷한 패턴이 확인되지 않음.

---

## Q2. 금리 인상/인하 이벤트 후 30일 나스닥 수익률 비교

**분석 질문:** 금리 인상/인하 발표 후 30일간 나스닥 수익률에 차이가 있는가? (pandas t-test 결과 검증)

**사용 기법:** self-join(같은 테이블 두 번 조인)으로 이벤트 당일 vs 30일 후 종가 비교, 서브쿼리로 `MIN(Date)` 찾아 비거래일 보정

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
    SELECT MIN(Date) FROM nasdaq WHERE Date >= DATE_ADD(e.Date,
