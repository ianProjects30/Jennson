from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()  # load variables from .env

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase URL or Key is not set!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
