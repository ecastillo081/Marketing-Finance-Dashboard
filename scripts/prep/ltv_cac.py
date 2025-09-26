from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code
sql_code = """
CREATE OR REPLACE VIEW stg.ltv_cac AS
WITH cumulative_cm AS (
    SELECT
        cohort,
        channel,
        month_index,
        cm_per_customer,
        cac,
        SUM(cm_per_customer) OVER (PARTITION BY cohort, channel ORDER BY month_index
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_cm_per_customer
    FROM stg.finance_metrics
),
payback_period AS (
    SELECT DISTINCT ON (cohort, channel)
        cohort,
        channel,
        month_index AS payback_month
    FROM cumulative_cm
    WHERE cum_cm_per_customer >= cac
    ORDER BY cohort, channel, month_index
),
ltv AS (
    SELECT
        cohort,
        channel,
        SUM(cm_per_customer) AS ltv_per_customer
    FROM cumulative_cm
    GROUP BY cohort, channel
)
select
    l.cohort,
    l.channel,
    l.ltv_per_customer,
    f.cac,
    case when cac > 0 then l.ltv_per_customer / f.cac 
    else null 
    end as ltv_to_cac,
    p.payback_month
FROM ltv as l
JOIN (select distinct cohort, channel, cac FROM stg.finance_metrics) as f USING(cohort, channel)
LEFT JOIN payback_period as p USING(cohort, channel)
ORDER BY l.cohort, l.channel
"""

# run sql
with engine.begin() as conn:
    conn.execute(text(sql_code))
