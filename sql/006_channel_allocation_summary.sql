-- 006: channel allocation summary (portfolio / customer-weighted)
-- Weighted modeled lifetime contribution / CAC
--   = (new_customers x modeled lifetime CM per customer) / spend
--   = modeled lifetime CM per customer / blended CAC
-- because modeled lifetime CM per customer is constant within a channel.
-- Unweighted mean of cohort ratios is retained only as a diagnostic.
-- Channel-level payback uses the same CM curve vs the channel blended CAC,
-- not the average of cohort payback months.

CREATE OR REPLACE TABLE stg.channel_allocation_summary AS
WITH observed AS (
    SELECT
        channel,
        SUM(spend) AS total_spend,
        SUM(new_customers) AS attributed_new_customers,
        SUM(platform_conversions) AS platform_conversions,
        SUM(platform_attributed_value) AS platform_attributed_value
    FROM stg.ads_daily
    GROUP BY channel
),
totals AS (
    SELECT SUM(total_spend) AS grand_spend
    FROM observed
),
lifetime AS (
    SELECT
        channel,
        MAX(modeled_lifetime_contribution_per_customer) AS modeled_lifetime_contribution_per_customer,
        MAX(horizon_months) AS horizon_months
    FROM stg.unit_economics
    GROUP BY channel
),
curve AS (
    SELECT
        channel,
        month_index,
        modeled_cm_per_acquired_customer,
        modeled_cum_cm_per_acquired_customer
    FROM stg.monthly_cohorts
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY channel, month_index
        ORDER BY cohort
    ) = 1
),
cohort_flags AS (
    SELECT
        channel,
        COUNT(*) AS acquisition_cohorts,
        SUM(CASE WHEN never_pays_back_within_horizon THEN 1 ELSE 0 END) AS cohorts_never_pay_back,
        AVG(modeled_lifetime_contribution_to_cac) AS modeled_lifetime_contribution_to_cac_unweighted_mean_of_cohorts
    FROM stg.unit_economics
    WHERE new_customers > 0
    GROUP BY channel
),
channel_cac AS (
    SELECT
        o.channel,
        o.total_spend,
        o.attributed_new_customers,
        o.platform_conversions,
        o.platform_attributed_value,
        CASE
            WHEN o.attributed_new_customers > 0 THEN o.total_spend / o.attributed_new_customers
            ELSE NULL
        END AS blended_cac,
        CASE
            WHEN o.total_spend > 0 THEN o.platform_attributed_value / o.total_spend
            ELSE NULL
        END AS platform_attributed_roas,
        l.modeled_lifetime_contribution_per_customer,
        l.horizon_months
    FROM observed AS o
    LEFT JOIN lifetime AS l
        USING (channel)
),
portfolio_payback AS (
    SELECT
        c.channel,
        MIN(cv.month_index) AS modeled_payback_month_index
    FROM channel_cac AS c
    INNER JOIN curve AS cv
        ON c.channel = cv.channel
    WHERE c.blended_cac IS NOT NULL
      AND cv.modeled_cum_cm_per_acquired_customer >= c.blended_cac
    GROUP BY c.channel
)
SELECT
    c.channel,
    c.total_spend,
    c.total_spend / t.grand_spend AS spend_mix_pct,
    c.attributed_new_customers,
    c.blended_cac,
    c.platform_attributed_roas,
    c.modeled_lifetime_contribution_per_customer,
    CASE
        WHEN c.blended_cac > 0 THEN c.modeled_lifetime_contribution_per_customer / c.blended_cac
        ELSE NULL
    END AS modeled_lifetime_contribution_to_cac_weighted,
    f.modeled_lifetime_contribution_to_cac_unweighted_mean_of_cohorts,
    p.modeled_payback_month_index,
    CASE
        WHEN c.attributed_new_customers > 0 AND p.modeled_payback_month_index IS NULL THEN TRUE
        ELSE FALSE
    END AS never_pays_back_within_horizon,
    f.acquisition_cohorts,
    f.cohorts_never_pay_back,
    CASE
        WHEN f.acquisition_cohorts > 0 THEN f.cohorts_never_pay_back::DOUBLE / f.acquisition_cohorts
        ELSE NULL
    END AS share_of_cohorts_never_pay_back,
    c.horizon_months,
    'weighted: (customers x modeled lifetime CM per customer) / spend; channel payback vs blended CAC' AS aggregation_method
FROM channel_cac AS c
CROSS JOIN totals AS t
LEFT JOIN cohort_flags AS f
    USING (channel)
LEFT JOIN portfolio_payback AS p
    USING (channel);
