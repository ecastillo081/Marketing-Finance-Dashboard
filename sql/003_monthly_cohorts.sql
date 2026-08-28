-- 003: cohort economics
-- For every acquisition cohort x channel, project ALL 38 assumption months.
-- This is a forward modeled unit-economics framework, not realized historical LTV.
--
-- Retention, ARPU, gross margin, refund rate, processing fee, and variable
-- cost per order are modeled assumptions. Spend and new_customers are observed
-- synthetic fixtures.
--
-- Waterfall (gross margin treated as product margin, before fees and
-- fulfillment-like variable costs):
--   modeled gross revenue
--   - refunds
--   = modeled net revenue
--   net revenue x gross_margin_pct = gross profit
--   gross profit - payment fees - variable costs = contribution margin
--
-- Channel finance drivers are used when present; otherwise DEFAULT is applied.

CREATE OR REPLACE TABLE stg.monthly_cohorts AS
WITH finance_by_channel AS (
    SELECT
        c.cohort,
        c.channel,
        c.new_customers,
        c.spend,
        c.blended_cac,
        COALESCE(f.gross_margin_pct, d.gross_margin_pct) AS assumed_gross_margin_pct,
        COALESCE(f.variable_cost_per_order, d.variable_cost_per_order) AS assumed_variable_cost_per_order,
        COALESCE(f.payment_processing_fee_pct, d.payment_processing_fee_pct) AS assumed_payment_processing_fee_pct,
        COALESCE(f.refund_rate_pct, d.refund_rate_pct) AS assumed_refund_rate_pct
    FROM stg.monthly_channel_summary AS c
    LEFT JOIN assumptions.finance AS f
        ON c.channel = f.channel
    LEFT JOIN assumptions.finance AS d
        ON d.channel = 'DEFAULT'
),
horizon AS (
    SELECT
        r.month_index,
        r.retention_rate_t AS assumed_retention_rate,
        a.arpu_t AS assumed_arpu
    FROM assumptions.retention AS r
    INNER JOIN assumptions.arpu AS a
        USING (month_index)
),
extended AS (
    SELECT
        f.cohort,
        f.channel,
        f.new_customers,
        f.spend,
        f.blended_cac,
        f.assumed_gross_margin_pct,
        f.assumed_variable_cost_per_order,
        f.assumed_payment_processing_fee_pct,
        f.assumed_refund_rate_pct,
        h.month_index,
        h.assumed_retention_rate,
        h.assumed_arpu
    FROM finance_by_channel AS f
    CROSS JOIN horizon AS h
),
metrics AS (
    SELECT
        cohort,
        channel,
        month_index,
        new_customers,
        spend,
        blended_cac,
        assumed_retention_rate,
        assumed_arpu,
        assumed_gross_margin_pct,
        assumed_variable_cost_per_order,
        assumed_payment_processing_fee_pct,
        assumed_refund_rate_pct,
        new_customers * assumed_retention_rate AS modeled_active_customers,
        new_customers * assumed_retention_rate * assumed_arpu AS modeled_gross_revenue,
        new_customers * assumed_retention_rate * assumed_arpu * assumed_refund_rate_pct AS modeled_refunds,
        new_customers * assumed_retention_rate * assumed_arpu * (1 - assumed_refund_rate_pct) AS modeled_net_revenue,
        new_customers * assumed_retention_rate * assumed_arpu * (1 - assumed_refund_rate_pct)
            * (1 - assumed_gross_margin_pct) AS modeled_cogs,
        new_customers * assumed_retention_rate * assumed_arpu * (1 - assumed_refund_rate_pct)
            * assumed_gross_margin_pct AS modeled_gross_profit,
        new_customers * assumed_retention_rate * assumed_arpu * (1 - assumed_refund_rate_pct)
            * assumed_payment_processing_fee_pct AS modeled_payment_fees,
        new_customers * assumed_retention_rate * assumed_variable_cost_per_order AS modeled_variable_costs,
        (
            new_customers * assumed_retention_rate * assumed_arpu * (1 - assumed_refund_rate_pct)
                * assumed_gross_margin_pct
            - new_customers * assumed_retention_rate * assumed_arpu * (1 - assumed_refund_rate_pct)
                * assumed_payment_processing_fee_pct
            - new_customers * assumed_retention_rate * assumed_variable_cost_per_order
        ) AS modeled_contribution_margin,
        CASE
            WHEN new_customers > 0 THEN
                (
                    (assumed_retention_rate * assumed_arpu) * (1 - assumed_refund_rate_pct) * assumed_gross_margin_pct
                    - (assumed_retention_rate * assumed_arpu) * (1 - assumed_refund_rate_pct) * assumed_payment_processing_fee_pct
                    - assumed_retention_rate * assumed_variable_cost_per_order
                )
            ELSE NULL
        END AS modeled_cm_per_acquired_customer
    FROM extended
)
SELECT
    *,
    SUM(modeled_cm_per_acquired_customer) OVER (
        PARTITION BY cohort, channel
        ORDER BY month_index
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS modeled_cum_cm_per_acquired_customer
FROM metrics;
