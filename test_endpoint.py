import os
import sys
import json
import asyncio
import io
from fastapi import UploadFile

# Add the 'backend' directory to the search path so that 'app' is resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.routers.parse import parse_claim_document
from app.database import supabase

print("==============================")
print("TESTING /PARSE API ROUTE DIRECTLY")
print("==============================\n")

# Use a valid claim ID from the database for the foreign key reference
claim_id = "d1deff21-750b-4346-b395-3529ea3da089"
test_file_path = "backend/test_files/aarav_mri_report.pdf"

if not os.path.exists(test_file_path):
    print(f"Error: Test file not found at {test_file_path}")
    sys.exit(1)

async def test_route():
    print(f"Reading file: {test_file_path}")
    with open(test_file_path, "rb") as f:
        file_content = f.read()

    # Wrap the file in a FastAPI UploadFile object
    upload_file = UploadFile(
        file=io.BytesIO(file_content),
        filename=os.path.basename(test_file_path),
        size=len(file_content),
        headers={"content-type": "application/pdf"}
    )

    print(f"Calling parse_claim_document route handler for Claim ID: {claim_id}...")
    response = await parse_claim_document(claim_id=claim_id, file=upload_file)

    print("\nRoute response:", response)

    print("\nVerifying database entry in Supabase 'parsed_claims' table...")
    db_res = supabase.table("parsed_claims").select("*").eq("claim_id", claim_id).execute()
    if db_res.data:
        print("Verification: SUCCESS. Record found in Supabase:")
        print(json.dumps(db_res.data, indent=4))
    else:
        print("Verification: FAILED. No record found in 'parsed_claims' table for claim_id:", claim_id)

# Run the async test
asyncio.run(test_route())

