from supabase import create_client

from dotenv import load_dotenv
load_dotenv()
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)


try:
    response = supabase.auth.sign_up({
        "email": "somyashekhar61@gmail.com",
        "password": "Password@123"
    })
    print(response)

except Exception as e:
    print(e)