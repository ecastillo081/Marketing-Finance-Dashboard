-- Optional reconciliation only.
-- Google campaign_id / campaign_name are randomly crossed with Search and
-- YouTube in the synthetic fixtures. Do not use this grain for allocation.

CREATE OR REPLACE TABLE stg.campaign_reconciliation AS
SELECT
    platform,
    channel,
    campaign_id,
    campaign_name,
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
GROUP BY 1, 2, 3, 4;
