-- 004: unit economics by acquisition cohort x channel
-- modeled_lifetime_contribution_per_customer = sum of modeled CM per acquired
--   customer over the full 38-month assumption horizon (forward projection).
-- modeled_payback_month_index = first month_index where cumulative modeled CM
--   per acquired customer >= blended CAC. month_index 0 = acquisition month.
-- Never-payback cohorts remain NULL and are flagged.
-- Priority score is intentionally omitted.

CREATE OR REPLACE TABLE stg.unit_economics AS
WITH lifetime AS (
    SELECT
        cohort,
        channel,
        MAX(new_customers) AS new_customers,
        MAX(spend) AS spend,
        MAX(blended_cac) AS blended_cac,
        SUM(modeled_cm_per_acquired_customer) AS modeled_lifetime_contribution_per_customer,
        COUNT(*) AS horizon_months
    FROM stg.monthly_cohorts
    GROUP BY cohort, channel
),
payback AS (
    SELECT
        cohort,
        channel,
        MIN(month_index) AS modeled_payback_month_index
    FROM stg.monthly_cohorts
    WHERE modeled_cum_cm_per_acquired_customer >= blended_cac
    GROUP BY cohort, channel
)
SELECT
    l.cohort,
    l.channel,
    l.new_customers,
    l.spend,
    l.blended_cac,
    l.modeled_lifetime_contribution_per_customer,
    CASE
        WHEN l.blended_cac > 0 THEN l.modeled_lifetime_contribution_per_customer / l.blended_cac
        ELSE NULL
    END AS modeled_lifetime_contribution_to_cac,
    p.modeled_payback_month_index,
    CASE
        WHEN l.new_customers > 0 AND p.modeled_payback_month_index IS NULL THEN TRUE
        ELSE FALSE
    END AS never_pays_back_within_horizon,
    l.horizon_months,
    CASE
        WHEN l.new_customers > 0 THEN l.new_customers * l.modeled_lifetime_contribution_per_customer
        ELSE NULL
    END AS modeled_lifetime_contribution_dollars,
    CASE
        WHEN l.new_customers > 0 THEN l.new_customers * l.modeled_lifetime_contribution_per_customer - l.spend
        ELSE NULL
    END AS modeled_lifetime_contribution_net_of_acquisition_spend
FROM lifetime AS l
LEFT JOIN payback AS p
    USING (cohort, channel);
