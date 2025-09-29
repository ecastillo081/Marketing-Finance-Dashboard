from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code
sql_code = """
CREATE OR REPLACE VIEW stg.monthly_cohorts AS
WITH finance_assumptions as (
SELECT
    cohort,
    c.channel,
    new_customers,
    spend,
    cac,
    gross_margin_pct,
    variable_cost_per_order,
    payment_processing_fee_pct,
    refund_rate_pct
FROM stg.monthly_channel_summary as c
LEFT JOIN assumptions.finance as f
ON c.channel = f.channel),

finance_assumptions_extended as (
SELECT
    cohort,
    channel,
    new_customers,
    spend,
    cac,
    gross_margin_pct,
    variable_cost_per_order,
    payment_processing_fee_pct,
    refund_rate_pct,
    month_index,
    retention_rate_t as retention_rate,
    arpu_t as arpu
FROM finance_assumptions
CROSS JOIN assumptions.retention
JOIN assumptions.arpu USING(month_index)
),
finance_metrics as (
SELECT
    cohort,
    channel,
    month_index,
    new_customers,
    retention_rate,
    arpu,
    new_customers * retention_rate AS active_customers,
    new_customers * retention_rate * arpu AS revenue,
    new_customers * retention_rate * arpu * refund_rate_pct AS refunds,
    new_customers * retention_rate * arpu * (1 - refund_rate_pct) AS net_revenue,
    (new_customers * retention_rate * arpu * (1 - refund_rate_pct))
    - (new_customers * retention_rate * arpu * (1 - refund_rate_pct) * gross_margin_pct) as cogs,    
    new_customers * retention_rate * arpu * (1 - refund_rate_pct) * gross_margin_pct AS gross_profit,
    new_customers * retention_rate * arpu * (1 - refund_rate_pct) * payment_processing_fee_pct AS payment_fees,
    new_customers * retention_rate * variable_cost_per_order AS variable_costs,
    cac,
    (new_customers * retention_rate * arpu * (1 - refund_rate_pct) * gross_margin_pct)
    - (new_customers * retention_rate * arpu * (1 - refund_rate_pct) * payment_processing_fee_pct)
    - (new_customers * retention_rate * variable_cost_per_order) AS contribution_margin,
    CASE WHEN new_customers > 0 THEN
    (
      ((retention_rate * arpu) * (1 - refund_rate_pct) * gross_margin_pct)
      - ((retention_rate * arpu) * (1 - refund_rate_pct) * payment_processing_fee_pct)
      - (retention_rate * variable_cost_per_order)
    )
    ELSE NULL 
    END AS cm_per_customer
FROM finance_assumptions_extended
)

SELECT
    *
FROM finance_metrics
ORDER BY cohort, channel, month_index
"""

# run sql
with engine.begin() as conn:
    conn.execute(text(sql_code))


#### return on ad spend view
# SQL code
sql_code = """
CREATE OR REPLACE VIEW stg.return_on_ad_spend AS
WITH campaign_spend AS (
    SELECT
        date_trunc('month', date) AS month,
        channel,
        campaign_id,
    SUM(spend) as spend,
    SUM(new_customers) as new_customers,
    SUM(conversions) as conversions,
    SUM(conversion_value) as attributed_revenue
    FROM stg.ads_daily
    GROUP BY month, channel, campaign_id
),
cohort AS (
    SELECT
        cohort as month,
        channel,
        AVG(ltv_per_customer) as ltv_per_customer,
        AVG(cac) as cac
    FROM stg.ltv_cac
    GROUP BY cohort, channel
)
SELECT
    cs.month,
    cs.channel,
    campaign_id,
    attributed_revenue,
    case when spend > 0 then attributed_revenue / spend END as roas, -- return on ad spend
    new_customers,
    case when new_customers > 0 then spend / new_customers END as cac,
    ltv_per_customer,
    case when new_customers > 0 then new_customers * ltv_per_customer END as ltv_dollars,
    new_customers * ltv_per_customer - spend as net_value_created
FROM campaign_spend as cs
LEFT JOIN cohort as c USING(month, channel)
ORDER BY cs.month, cs.channel, campaign_id
"""

# run sql
with engine.begin() as conn:
    conn.execute(text(sql_code))
