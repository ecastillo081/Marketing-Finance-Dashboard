import pandas as pd, os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# load environment variables
load_dotenv()
username = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
database = os.getenv("database")

# file path
df = pd.read_excel("../data/raw/marketing.xlsx")



# # Specify the file path to your CSV
# file_path = r'C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\transactions\final_report\plaid_transactions_final.xlsx'
#
# # Read the CSV file into a DataFrame
# df_plaid_transactions_final = pd.read_excel(file_path)
#
# # Specify the file path to your CSV
# file_path = r"C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\balances\exports\plaid_balances.xlsx"
#
# # Read the Excel file into a DataFrame
# df_plaid_balances_final = pd.read_excel(file_path)
#
# # Specify the file path to your CSV
# file_path = r"C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\investments\holdings\exports\investment_balances.xlsx"
#
# # Read the Excel file into a DataFrame
# df_plaid_investment_balances = pd.read_excel(file_path)
#
# # Specify the file path to your CSV
# file_path = r"C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\investments\holdings\exports\investment_holdings.xlsx"
#
# # Read the Excel file into a DataFrame
# df_plaid_investment_holdings = pd.read_excel(file_path)
#
# # Specify the file path to your CSV
# file_path = r"C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\investments\holdings\exports\investment_securities.xlsx"
#
# # Read the Excel file into a DataFrame
# df_plaid_investment_securities = pd.read_excel(file_path)
#
# # Specify the file path to your CSV
# file_path = r"C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\investments\transactions\exports\investment_transactions.xlsx"
#
# # Read the Excel file into a DataFrame
# df_plaid_investment_transactions = pd.read_excel(file_path)
#
# # Specify the file path to your CSV
# file_path = r"C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\tokens\auth.xlsx"
#
# # Read the Excel file into a DataFrame
# df_plaid_auth = pd.read_excel(file_path)
#
# # Specify the file path to your CSV
# file_path = r"C:\Users\ecast\OneDrive\Desktop\PostgreSQL\Data\plaid\accounts\exports\account_details.xlsx"
#
# # Read the Excel file into a DataFrame
# df_account_details = pd.read_excel(file_path)
#
#
# # Create a connection string and engine
# connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
# engine = create_engine(connection_string)
#
# # Specify the schema where the tables will be pushed
# push_schema = 'plaid'  # Example schema name
#
# # List of DataFrames and corresponding table names
# dataframes = {
#     'transactions': df_plaid_transactions_final,
#     'balance': df_plaid_balances_final,
#     'investment_balances': df_plaid_investment_balances,
#     'investment_holdings': df_plaid_investment_holdings,
#     'investment_securities': df_plaid_investment_securities,
#     'investment_transactions': df_plaid_investment_transactions,
#     'auth': df_plaid_auth,
#     'account_details': df_account_details
# }
#
# # Push each DataFrame to the PostgreSQL database, replacing existing tables
# for table_name, df in dataframes.items():
#     try:
#         df.to_sql(table_name, engine, schema=push_schema, if_exists='replace', index=False)
#         print(f"Successfully pushed {table_name} to schema '{push_schema}'")
#     except Exception as e:
#         print(f"Error pushing {table_name} to PostgreSQL: {e}")
