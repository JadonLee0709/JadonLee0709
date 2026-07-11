-- ── 1. 데이터베이스 생성 및 선택 ──────────────────────────
-- CREATE DATABASE IF NOT EXISTS nasdaq_portfolio;
-- USE nasdaq_portfolio;

-- ── 2. 테이블 생성 ──────────────────────────
-- CREATE TABLE nasdaq (
--     Date DATE,
--     Close DECIMAL(12,6),
--     High DECIMAL(12,6),
--     Low DECIMAL(12,6),
--     Open DECIMAL(12,6),
--     Volume BIGINT,
--     FedRate DECIMAL(5,2)
-- );

-- CREATE TABLE nasdaq_event_ffr_ver_3 (
--     Date DATE,
--     FedRate DECIMAL(5,2),
--     FedRateChange DECIMAL(5,2),
--     EventType VARCHAR(100),
--     EventTitle VARCHAR(255),
--     EventDescription TEXT,
--     MarketImpact VARCHAR(100),
--     Severity INT
-- );

-- ── 3. local_infile 설정 확인 및 활성화 ──────────────────────────
-- SHOW GLOBAL VARIABLES LIKE 'local_infile';
-- SET GLOBAL local_infile = 1;

-- ── 4. CSV 데이터 로드 ──────────────────────────
-- LOAD DATA LOCAL INFILE '/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq.csv'
-- INTO TABLE nasdaq
-- FIELDS TERMINATED BY ','
-- ENCLOSED BY '"'
-- LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS;

-- LOAD DATA LOCAL INFILE '/Users/ihyeonho/Desktop/Portfolio_DB/nasdaq_data_file/nasdaq_event_FFR_ver_3.csv'
-- INTO TABLE nasdaq_event_ffr_ver_3
-- FIELDS TERMINATED BY ','
-- ENCLOSED BY '"'
-- LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS;

-- ── 5. 데이터 확인 ──────────────────────────

-- Q.1 : 금리 구간별(0~1% / 1~3% / 3~5% / 5%+) 나스닥 평균 수익률·변동성 비교
-- ============================================
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

-- 결과: 0~1%(제로금리) 평균 0.0387% / 1~3%(저금리) 0.0234% / 3~5%(중금리) 0.0382% / 5%+(고금리) 0.0621%
-- 고금리(5%+) 구간에서 오히려 평균 수익률이 가장 높고 변동성은 가장 낮음(0.76)
-- 거래일 분포가 극단(제로금리 기간 4699일 vs 중금리 기간 250일)에 몰려있어 금리 수준 단독으로는 뚜렷한 패턴 확인 어려움


-- Q.2 : 금리 인상/인하 이벤트 후 30일 나스닥 수익률 비교
-- ============================================

-- (2-1) 이벤트별 상세 내역
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

-- (2-2) 인상/인하 그룹별 평균 요약
SELECT
    ChangeType,
    COUNT(*) AS EventCount,
    ROUND(AVG(Return30d_pct), 2) AS AvgReturn30d_pct,
    ROUND(STDDEV(Return30d_pct), 2) AS StdDev
FROM (
    SELECT
        e.Date AS EventDate,
        e.FedRateChange,
        CASE
            WHEN e.FedRateChange > 0 THEN 'Rate up'
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
) AS sub
GROUP BY ChangeType;

-- 결과: 인상 20건 평균 +0.45% / 인하 6건 평균 +3.33%
-- (pandas t-test 결과 p=0.594와 일치 — 통계적으로 유의미한 차이는 아님)

-- ============================================
-- Q.3: 연도별 나스닥 평균 일별 수익률 및 변동성 집계
-- ============================================

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

-- 결과: 2022년만 유일하게 마이너스 평균 수익률(-0.1365%) 기록
-- 변동성도 2020년(코로나) 다음으로 두 번째로 높음(2.0212)
-- pandas 연도별 집계 결과와 일치

-- ============================================
-- Q.4: LAG() + 사용자 변수를 활용한 금리 변화 시점 감지
-- (nasdaq_event_ffr_ver_3 이벤트 테이블 없이, 원본 nasdaq 테이블만으로 재현)
-- ============================================

-- (4-1) 전일 대비 FedRate가 바뀐 날짜만 감지
SELECT
    Date,
    FedRate,
    PrevFedRate,
    ROUND(FedRate - PrevFedRate, 2) AS RateChange
FROM (
    SELECT
        Date,
        FedRate,
        LAG(FedRate) OVER (ORDER BY Date) AS PrevFedRate
    FROM nasdaq
) AS sub
WHERE FedRate != PrevFedRate
ORDER BY Date;

-- (4-2) 사용자 변수(@변수, :=)로 변경 순번(ChangeSequence) 지정
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


-- 결과: 이벤트 테이블 없이 원본 nasdaq 테이블만으로 26건의 금리 변화 시점을 정확히 재현
-- 사용자 변수(@change_count)로 각 변화에 순번을 매겨 시계열 순서 추적 가능

