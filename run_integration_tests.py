import os
import sys
import time
import subprocess
import requests
import json

# Setup configurations
BASE_URL = "http://127.0.0.1:8000"
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))

print("==================================================")
# Start the FastAPI server in the background
print("Starting FastAPI Server on http://127.0.0.1:8000 ...")
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--app-dir", "backend"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

# Wait for server to boot up
time.sleep(3)

# Test tracker
test_results = {}

def record_test(name, success, info=""):
    test_results[name] = {"success": success, "info": info}
    status = "PASS" if success else "FAIL"
    print(f"[{status}] {name} - {info}")

try:
    # 1. Check root/docs endpoint
    try:
        res = requests.get(f"{BASE_URL}/docs", timeout=60)
        if res.status_code == 200:
            record_test("FastAPI Docs", True, "Successfully loaded swagger docs")
        else:
            record_test("FastAPI Docs", False, f"Returned status code {res.status_code}")
    except Exception as e:
        record_test("FastAPI Docs", False, str(e))

    # 2. Get Default Household
    try:
        res = requests.get(f"{BASE_URL}/households/default", timeout=60)
        if res.status_code == 200:
            data = res.json()
            record_test("Get Default Household", True, f"Name: {data.get('household', {}).get('name') if data.get('household') else 'None'}")
        else:
            record_test("Get Default Household", False, f"Returned status code {res.status_code}")
    except Exception as e:
        record_test("Get Default Household", False, str(e))

    # 3. Create a Household
    household_payload = {
        "household_name": "Test Family Integration",
        "members": [
            {
                "member_name": "Integration User",
                "relationship": "Spouse",
                "insurances": [
                    {"insurer_key": "insurer1", "role": "primary"},
                    {"insurer_key": "insurer2", "role": "dependent"}
                ]
            }
        ]
    }
    try:
        res = requests.post(f"{BASE_URL}/households", json=household_payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            record_test("Create Household", True, f"Created household ID: {data.get('id')}")
        else:
            record_test("Create Household", False, f"Returned status code {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Create Household", False, str(e))

    # 4. Create a Claim
    claim_payload = {
        "user_id": "00f12b9a-b2f0-4064-ad05-df3534fb0b42",
        "patient_name": "Integration User",
        "claim_type": "physiotherapy",
        "total_amount": 35000.0,
        "primary_insurer": "Plan A",
        "secondary_insurer": "Plan B"
    }
    claim_id = None
    try:
        res = requests.post(f"{BASE_URL}/claims", json=claim_payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            claim_id = data[0]["id"] if data else None
            record_test("Create Claim", True, f"Created claim ID: {claim_id}")
        else:
            record_test("Create Claim", False, f"Returned status code {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Create Claim", False, str(e))

    # 5. List Claims
    try:
        res = requests.get(f"{BASE_URL}/claims", timeout=60)
        if res.status_code == 200:
            data = res.json()
            record_test("List Claims", True, f"Found {len(data)} claims in DB")
        else:
            record_test("List Claims", False, f"Returned status code {res.status_code}")
    except Exception as e:
        record_test("List Claims", False, str(e))

    # 6. Upload a document
    test_pdf = os.path.join(BACKEND_DIR, "test_files", "aarav_mri_report.pdf")
    if claim_id and os.path.exists(test_pdf):
        try:
            with open(test_pdf, "rb") as f:
                files = {"file": (os.path.basename(test_pdf), f, "application/pdf")}
                data = {"claim_id": claim_id, "document_type": "mri_report"}
                res = requests.post(f"{BASE_URL}/upload", data=data, files=files, timeout=60)
                if res.status_code == 200:
                    record_test("Upload Document", True, f"Uploaded metadata to Supabase bucket")
                else:
                    record_test("Upload Document", False, f"Returned status code {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Upload Document", False, str(e))
    else:
        record_test("Upload Document", False, "Skipped (missing claim_id or test file)")

    # 7. Parse the document
    if claim_id and os.path.exists(test_pdf):
        try:
            with open(test_pdf, "rb") as f:
                files = {"file": (os.path.basename(test_pdf), f, "application/pdf")}
                data = {"claim_id": claim_id}
                res = requests.post(f"{BASE_URL}/parse", data=data, files=files, timeout=60)
                if res.status_code == 200:
                    record_test("Parse Document", True, f"Document parsed and structured JSON saved to DB")
                else:
                    record_test("Parse Document", False, f"Returned status code {res.status_code}: {res.text}")
        except Exception as e:
            record_test("Parse Document", False, str(e))
    else:
        record_test("Parse Document", False, "Skipped (missing claim_id or test file)")

    # 8. Process Claim (LangGraph COB Engine)
    cob_payload = {
        "claim_id": claim_id or "CLM-MOCK-INTEGRATION",
        "patient_name": "Integration User",
        "member_id": None,
        "diagnosis": "ACL tear with meniscus injury",
        "cpt_codes": ["97161", "97110"],
        "icd10_codes": ["M23.619", "M23.200"],
        "total_amount": 30000.0,
        "billed_amounts": {"97161": 10000.0, "97110": 20000.0},
        "primary_insurer": "Plan A",
        "secondary_insurer": "Plan B",
        "hospital": "City Hospital",
        "network_status": {"SecureHealth Premier": "IN", "FlexiCare Plus": "IN"}
    }
    try:
        res = requests.post(f"{BASE_URL}/process-claim", json=cob_payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            is_valid = data.get("validation_status", {}).get("is_valid", False)
            record_test("Process Claim (COB)", True, f"Reconciliation is_valid: {is_valid}")
        else:
            record_test("Process Claim (COB)", False, f"Returned status code {res.status_code}: {res.text}")
    except Exception as e:
        record_test("Process Claim (COB)", False, str(e))

    # 9. Get Insurer Plan Details
    try:
        res = requests.get(f"{BASE_URL}/insurance/insurer1", timeout=60)
        if res.status_code == 200:
            data = res.json()
            record_test("Get Plan Rules", True, f"Loaded Plan A name: {data.get('plan_name')}")
        else:
            record_test("Get Plan Rules", False, f"Returned status code {res.status_code}")
    except Exception as e:
        record_test("Get Plan Rules", False, str(e))

    # 10. Eligibility Checker
    eligibility_payload = {
        "cpt_codes": ["97161", "97110"],
        "plan_name": "insurer1"
    }
    try:
        res = requests.post(f"{BASE_URL}/insurance/eligibility", json=eligibility_payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            record_test("Check Eligibility", True, f"Is eligible: {data.get('is_eligible')}")
        else:
            record_test("Check Eligibility", False, f"Returned status code {res.status_code}")
    except Exception as e:
        record_test("Check Eligibility", False, str(e))

    # 11. Pre-Auth Checker
    preauth_payload = {
        "cpt_codes": ["29888", "29881"],
        "plan_name": "insurer1"
    }
    try:
        res = requests.post(f"{BASE_URL}/insurance/preauth", json=preauth_payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            record_test("Check Pre-Authorization", True, f"Requires preauth: {data.get('requires_preauth')}")
        else:
            record_test("Check Pre-Authorization", False, f"Returned status code {res.status_code}")
    except Exception as e:
        record_test("Check Pre-Authorization", False, str(e))

finally:
    # Shutdown server
    print("\nShutting down FastAPI server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    print("FastAPI server terminated.")

# Print final diagnostic report card
print("\n" + "="*50)
print("             INTEGRATION TEST REPORT CARD             ")
print("="*50)
failed_tests = 0
for name, res in test_results.items():
    status = "PASS" if res["success"] else "FAIL"
    print(f"{name:<25}: {status:<5} | {res['info']}")
    if not res["success"]:
        failed_tests += 1
print("="*50)
print(f"Total failures: {failed_tests}")
print("="*50)

if failed_tests > 0:
    sys.exit(1)
else:
    sys.exit(0)
