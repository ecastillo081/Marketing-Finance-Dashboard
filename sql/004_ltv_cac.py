from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code
sql_code = """
CREATE OR REPLACE VIEW stg.ltv_cac AS
WITH contribution_margin as (
select
    cohort,
    channel,
    month_index,
    cm_per_customer
    FROM stg.monthly_cohorts
),
cac as (
select
    cohort,
    channel,
    cac
    FROM stg.monthly_channel_summary
),
cm_and_cac as (
select
    cm.cohort,
    cm.channel,
    cm.month_index,
    cm.cm_per_customer,
    cac.cac
FROM contribution_margin as cm
LEFT JOIN cac USING(cohort, channel)
),
cumulative_cm AS (
    SELECT
        cohort,
        channel,
        month_index,
        cm_per_customer,
        cac,
        SUM(cm_per_customer) OVER (PARTITION BY cohort, channel ORDER BY month_index
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_cm_per_customer
    FROM cm_and_cac
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
        SUM(cm_per_customer) AS ltv_per_customer,
        COUNT(*) as horizon_months
    FROM cumulative_cm
    GROUP BY cohort, channel
),
ltv_cac as (
select
    l.cohort,
    l.channel,
    l.ltv_per_customer,
    f.cac,
    case when cac > 0 then l.ltv_per_customer / f.cac 
    else null 
    end as ltv_to_cac,
    p.payback_month,
    horizon_months,
    -- priority score ranks the best channels to invest in: (LTV/CAC - 1)
    case 
        when cac is null or cac <= 0 then null 
        when payback_month is null or payback_month <= 0 then null
    else ((ltv_per_customer / cac) - 1) / payback_month
    end as priority_score
FROM ltv as l
JOIN (select distinct cohort, channel, cac FROM cac) as f USING(cohort, channel)
LEFT JOIN payback_period as p USING(cohort, channel)
ORDER BY l.cohort, l.channel
)

SELECT
    *,
    RANK() OVER (PARTITION BY cohort ORDER BY priority_score DESC NULLS LAST) AS channel_rank
FROM ltv_cac
ORDER BY cohort, channel

"""

# run sql
with engine.begin() as conn:
    conn.execute(text(sql_code))
