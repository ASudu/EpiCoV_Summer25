import gisaid_download
from dotenv import load_dotenv
import os

# Credentials for GISAID
load_dotenv() # Load environment variables from .env file
user = os.getenv("GISAID_USERNAME")
password = os.getenv("GISAID_PASSWORD")