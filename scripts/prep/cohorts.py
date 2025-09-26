from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code
sql_code = """
-- create new view joining google and meta ad daily data
CREATE OR REPLACE VIEW stg.ads_daily AS
SELECT
    date,
    channel,
    campaign_id,
    ad_id,
    spend_usd,
    new_customers,
    conversions,
    conversion_value_usd
FROM raw.google_ads_daily
UNION ALL
SELECT
    date,
    channel,
    campaign_id,
    ad_id,
    spend_usd,
    new_customers,
    purchases as conversions,
    purchase_value_usd as conversion_value_usd
FROM raw.meta_ads_daily
"""

# run it
with engine.begin() as conn:
    conn.execute(text(sql_code))

# SQL code
sql_code = """

-- create new view for new customer acquisitions
CREATE OR REPLACE VIEW stg.monthly_cohorts AS
WITH new_customers AS (
    SELECT
        date_trunc('month', date) AS cohort,
        channel,
        SUM(new_customers) AS new_customers,
        SUM(spend_usd) AS spend
    FROM stg.ads_daily
    GROUP BY cohort, channel
    ORDER BY cohort, channel
)
SELECT
    cohort,
    channel,
    new_customers,
    spend,
    CASE
        WHEN new_customers > 0 THEN spend / new_customers
        ELSE NULL
    END AS cac
FROM new_customers
"""

# run sql
with engine.begin() as conn:
    conn.execute(text(sql_code))
