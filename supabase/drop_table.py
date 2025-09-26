from sqlalchemy import create_engine, MetaData, Table
from supabase.credentials import username, password, host, port, database

# Create a connection string and engine
connection_string = f'postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require'
engine = create_engine(connection_string)

metadata = MetaData()

# drop table parameters
schema_name = 'schema_name'
table_name = 'table_name'

# Reflect the table from the specified schema
table_to_drop = Table(table_name, metadata, schema=schema_name, autoload_with=engine)

# Connect to the database
with engine.connect() as connection:
    table_to_drop.drop(engine)  # Drop the table
    print(f"Table '{schema_name}.{table_name}' has been dropped.")
