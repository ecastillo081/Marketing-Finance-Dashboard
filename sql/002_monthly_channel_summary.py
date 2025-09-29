from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code
sql_code = """

-- create new view for new customer acquisitions
CREATE OR REPLACE VIEW stg.monthly_channel_summary AS
WITH new_customers AS (
    SELECT
        date_trunc('month', date) AS cohort,
        channel,
        SUM(new_customers) AS new_customers,
        SUM(spend) AS spend
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
