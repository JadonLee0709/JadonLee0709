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








