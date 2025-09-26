from dotenv import load_dotenv
import os

# load environment variables
load_dotenv()
username = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
database = os.getenv("database")
