from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code to create data dictionary table
sql_code = """
DROP VIEW stg.channel_campaign_monthly_pnl;
DROP VIEW stg.ltv_cac;
DROP VIEW stg.monthly_cohorts;
DROP VIEW stg.monthly_channel_summary;
DROP VIEW stg.ads_daily;
"""
# DROP VIEW stg.monthly_cohorts;


# run it
with engine.begin() as conn:
    conn.execute(text(sql_code))
