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
    spend,
    new_customers,
    conversions,
    conversion_value
FROM raw.google_ads_daily
UNION ALL
SELECT
    date,
    channel,
    campaign_id,
    ad_id,
    spend,
    new_customers,
    purchases as conversions,
    purchase_value as conversion_value
FROM raw.meta_ads_daily
"""

# run it
with engine.begin() as conn:
    conn.execute(text(sql_code))
