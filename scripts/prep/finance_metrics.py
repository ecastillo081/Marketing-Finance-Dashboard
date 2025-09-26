from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code
sql_code = """
CREATE OR REPLACE VIEW stg.finance_metrics AS
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
FROM stg.monthly_cohorts as c
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
