-- 005: channel x month P&L
-- Channel grain only. Google campaign IDs are randomly crossed with Search /
-- YouTube in the synthetic fixtures and are not used for allocation.

CREATE OR REPLACE TABLE stg.channel_monthly_pnl AS
SELECT
    s.cohort AS month,
    s.channel,
    s.spend,
    s.new_customers,
    s.platform_conversions,
    s.platform_attributed_value,
    s.blended_cac,
    s.platform_attributed_roas,
    u.modeled_lifetime_contribution_per_customer,
    u.modeled_lifetime_contribution_to_cac,
    u.modeled_payback_month_index,
    u.never_pays_back_within_horizon,
    u.modeled_lifetime_contribution_dollars,
    u.modeled_lifetime_contribution_net_of_acquisition_spend
FROM stg.monthly_channel_summary AS s
LEFT JOIN stg.unit_economics AS u
    ON s.cohort = u.cohort
    AND s.channel = u.channel;
