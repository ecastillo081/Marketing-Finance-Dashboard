-- 002: monthly channel summary (observed fixtures only)
-- Grain: acquisition calendar month x channel
-- blended_cac = spend / attributed new-customer proxy
-- platform_attributed_roas = platform-attributed conversion value / spend
-- ROAS is not profit, incremental return, or contribution return.

CREATE OR REPLACE TABLE stg.monthly_channel_summary AS
SELECT
    date_trunc('month', date)::DATE AS cohort,
    channel,
    SUM(spend) AS spend,
    SUM(new_customers) AS new_customers,
    SUM(platform_conversions) AS platform_conversions,
    SUM(platform_attributed_value) AS platform_attributed_value,
    CASE
        WHEN SUM(new_customers) > 0 THEN SUM(spend) / SUM(new_customers)
        ELSE NULL
    END AS blended_cac,
    CASE
        WHEN SUM(spend) > 0 THEN SUM(platform_attributed_value) / SUM(spend)
        ELSE NULL
    END AS platform_attributed_roas
FROM stg.ads_daily
GROUP BY 1, 2;
