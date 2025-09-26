from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code to create data dictionary table
sql_code = """
-- create schema if not exists
CREATE SCHEMA IF NOT EXISTS data_dictionary;

-- create table
CREATE TABLE IF NOT EXISTS data_dictionary.google_ads (
    column_name TEXT PRIMARY KEY,
    description TEXT,
    data_type   TEXT,
    example     TEXT
);

-- insert rows
INSERT INTO data_dictionary.google_ads (column_name, description, data_type, example) VALUES
('date', 'Reporting date for the metric', 'DATE', '2025-01-15'),
('customer_id', 'Google Ads account/customer ID', 'TEXT', '123-456-7890'),
('campaign_id', 'Unique identifier for the campaign', 'TEXT', 'gcmp_2025_101'),
('campaign_name', 'Human-readable name of the campaign', 'TEXT', 'Search - Brand - US'),
('ad_group_id', 'Unique identifier for the ad group', 'TEXT', 'ggrp_001'),
('ad_group_name', 'Name of the ad group', 'TEXT', 'Brand Exact'),
('ad_id', 'Unique identifier for the ad creative', 'TEXT', 'gad_001'),
('ad_name', 'Name of the ad creative', 'TEXT', 'RSAs v1'),
('network', 'Advertising network where the ad was served', 'TEXT', 'SEARCH or YOUTUBE'),
('device', 'Device type where ad was served', 'TEXT', 'MOBILE or DESKTOP'),
('channel', 'Marketing channel grouping', 'TEXT', 'Google Ads - Search'),
('currency', 'Currency for spend and value metrics', 'TEXT', 'USD'),
('impressions', 'Number of times the ad was shown', 'INTEGER', '12345'),
('clicks', 'Number of clicks on the ad', 'INTEGER', '456'),
('spend_usd', 'Total spend for that row in USD', 'NUMERIC(12,2)', '245.67'),
('conversions', 'Number of conversions attributed to clicks', 'INTEGER', '23'),
('conversion_value_usd', 'Total value of conversions in USD', 'NUMERIC(12,2)', '1750.50');
"""

# run it
with engine.begin() as conn:
    conn.execute(text(sql_code))

print("Data dictionary created")
