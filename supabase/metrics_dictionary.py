from sqlalchemy import create_engine, text
from supabase.credentials import username, password, host, port, database

# create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

# SQL code
sql_code = """
-- create schema if not exists
CREATE SCHEMA IF NOT EXISTS data_dictionary;

-- create table
DROP TABLE IF EXISTS data_dictionary.metrics;
CREATE TABLE data_dictionary.metrics (
  column_name TEXT PRIMARY KEY,
  description TEXT,
  data_type   TEXT,
  example     TEXT
);

-- insert rows
INSERT INTO data_dictionary.metrics (column_name, description, data_type, example) VALUES
('active_customers', 'Expected number of customers active in a given month of a cohort. Formula: acquired_customers × retention_rate', 'NUMERIC', '494.2'),
('ad_id', 'Unique identifier for the ad creative', 'TEXT', 'gad_001'),
('arpu', 'Average revenue per user in month t. Used for LTV calculations', 'NUMERIC(12,2)', '25.00'),
('attributed_revenue', 'Revenue attributed to a channel/campaign based on platform tracking', 'NUMERIC(12,2)', '3000.00'),
('cac', 'Customer Acquisition Cost. Formula: spend ÷ new_customers', 'NUMERIC(12,2)', '62.50'),
('campaign_id', 'Unique identifier for the campaign', 'TEXT', 'gcmp_2025_101'),
('channel', 'Marketing channel grouping (e.g., Google Ads - Search, Meta Ads)', 'TEXT', 'Google Ads - YouTube'),
('channel_rank', 'Ranking of channel/cohort by priority_score', 'INTEGER', '1'),
('cm_per_customer', 'Contribution margin per customer in month t. Formula: (ARPU × GM% – variable costs – payment fees) × retention_rate', 'NUMERIC(12,2)', '3.75'),
('cogs', 'Cost of Goods Sold for products/services tied to conversions', 'NUMERIC(12,2)', '700.00'),
('cohort', 'Acquisition cohort (month customers first purchased)', 'DATE', '2025-01-01'),
('contribution_margin', 'Total contribution margin dollars in month t. Formula: gross_profit – variable_costs – payment_fees', 'NUMERIC(12,2)', '1500.00'),
('conversion_value', 'Value of conversions in USD for the row (from platform)', 'NUMERIC(12,2)', '1750.50'),
('conversions', 'Number of conversions (e.g., purchases) attributed', 'INTEGER', '120'),
('gross_profit', 'Gross profit dollars. Formula: net_revenue × gross_margin_pct', 'NUMERIC(12,2)', '9658.08'),
('ltv_dollars', 'Lifetime gross margin dollars for a cohort. Formula: Σ cm_per_customer × acquired_customers', 'NUMERIC(12,2)', '125,000.00'),
('ltv_per_customer', 'Lifetime gross margin per customer. Formula: Σ cm_per_customer over horizon', 'NUMERIC(12,2)', '95.00'),
('ltv_to_cac', 'LTV to CAC ratio. Formula: ltv_per_customer ÷ cac', 'NUMERIC(6,2)', '2.5'),
('month_index', 'Months since cohort acquisition (0 = acquisition month)', 'INTEGER', '3'),
('net_revenue', 'Revenue after refunds. Formula: revenue × (1 – refund_rate)', 'NUMERIC(12,2)', '16,096.80'),
('net_value_created', 'Net profit generated per cohort. Formula: (new_customers × ltv_per_customer) – spend', 'NUMERIC(12,2)', '42,000.00'),
('new_customers', 'Number of first-time customers acquired', 'INTEGER', '1412'),
('payback_month', 'First month_index where cumulative CM_per_customer ≥ CAC', 'INTEGER', '5'),
('payment_fees', 'Processing fees on net revenue. Formula: net_revenue × payment_processing_fee_pct', 'NUMERIC(12,2)', '466.81'),
('priority_score', 'Optimization metric. Formula: (LTV/CAC – 1) ÷ payback_month', 'NUMERIC(8,4)', '0.0833'),
('refunds', 'Portion of revenue lost due to customer refunds/returns. Formula: revenue × refund_rate', 'NUMERIC(12,2)', '847.20'),
('retention_rate', 'Fraction of cohort still active in month t', 'NUMERIC(5,2)', '0.35'),
('revenue', 'Gross revenue in month t before refunds', 'NUMERIC(12,2)', '5930.40'),
('roas', 'Return on Ad Spend. Formula: attributed_revenue ÷ spend', 'NUMERIC(6,2)', '3.0'),
('spend', 'Total ad spend in USD', 'NUMERIC(12,2)', '245.67'),
('variable_costs', 'Variable costs tied to orders (e.g., shipping, handling). Formula: active_customers × variable_cost_per_order', 'NUMERIC(12,2)', '9884.00');
"""

# run it
with engine.begin() as conn:
    conn.execute(text(sql_code))

print("Data dictionary created")
