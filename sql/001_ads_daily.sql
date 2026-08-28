-- 001: consolidated daily ads
-- Observed synthetic fixtures only. No modeled revenue or LTV here.
--
-- Google: platform conversions = conversions; attributed value = conversion_value
-- Meta:   platform conversions = purchases;   attributed value = purchase_value
-- Meta also has a separate source `conversions` field (source_conversions).
-- The generator derived new_customers from that field, so Meta new_customers
-- can exceed purchases. That is a fixture limitation, not a mapping bug.

CREATE OR REPLACE TABLE stg.ads_daily AS
SELECT
    date::DATE AS date,
    'Google Ads' AS platform,
    channel,
    campaign_id,
    campaign_name,
    ad_id,
    spend,
    new_customers,
    conversions AS source_conversions,
    conversions AS normalized_purchase_conversions,
    conversions AS platform_conversions,
    conversion_value AS platform_attributed_value
FROM raw.google_ads_daily

UNION ALL

SELECT
    date::DATE AS date,
    'Meta Ads' AS platform,
    channel,
    campaign_id,
    campaign_name,
    ad_id,
    spend,
    new_customers,
    conversions AS source_conversions,
    purchases AS normalized_purchase_conversions,
    purchases AS platform_conversions,
    purchase_value AS platform_attributed_value
FROM raw.meta_ads_daily;
