import os
from supabase import create_client, Client
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_supabase_client: Optional[Client] = None

def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            # We don't want to crash the app if they haven't set it yet, but we should log it
            print("WARNING: SUPABASE_URL or SUPABASE_KEY is missing. Supabase client won't work.")
            return None
        _supabase_client = create_client(url, key)
    return _supabase_client
