from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

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
