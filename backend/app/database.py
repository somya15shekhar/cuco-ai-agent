from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase = create_client(  #job is to create a connection object that your Python application uses to communicate with your Supabase project.
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
)