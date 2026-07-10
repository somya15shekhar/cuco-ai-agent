import os
import sys
import json

# Add 'backend' directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.models.claim import ParsedClaim
from app.api.insurance import get_insurer_plan, check_eligibility_endpoint, check_preauth_endpoint, CPTRequest
from app.agent.graph import run_cob_agent

print("==================================================")
print("RUNNING AGENTIC INSURANCE WORKFLOW REFACTOR TEST")
print("==================================================\n")

# 1. Test Mock Insurance Endpoints dynamically
print("--- Step 1: Testing Mock Insurance Endpoints (Direct Handlers) ---")
plan_a = get_insurer_plan("insurer1")
print(f"Plan A details (Insurer1):")
print(json.dumps(plan_a.model_dump(), indent=2))

plan_b = get_insurer_plan("insurer2")
print(f"Plan B details (Insurer2):")
print(json.dumps(plan_b.model_dump(), indent=2))
print("\n" + "-"*50 + "\n")

# 2. Aarav Sharma Surgery Claim
print("--- Step 2: Running LangGraph Agent for Aarav Sharma (Surgery Claim) ---")
aarav_claim = ParsedClaim(
    claim_id="CLM-AARAV-001",
    patient_name="Aarav Sharma",
    diagnosis="ACL tear and medial meniscus damage, left knee",
    cpt_codes=["29888", "29881"],
    icd10_codes=["M23.619", "M23.200"],
    total_amount=450000.0,
    billed_amounts={
        "29888": 350000.0,
        "29881": 100000.0
    },
    primary_insurer="Plan B",
    secondary_insurer="Plan A",
    hospital="City Orthopaedic Hospital (Network - both insurers)"
)

aarav_result = run_cob_agent(aarav_claim)
print("\n[SUCCESS] Aarav Sharma Claim Output:")
print(json.dumps(aarav_result, indent=2))
print("\n" + "-"*50 + "\n")

# 3. Priya Sharma Physiotherapy Claim
print("--- Step 3: Running LangGraph Agent for Priya Sharma (Physiotherapy Claim) ---")
priya_claim = ParsedClaim(
    claim_id="CLM-PRIYA-001",
    patient_name="Priya Sharma",
    diagnosis="Post-operative physiotherapy following right knee meniscus repair",
    cpt_codes=["97161", "97110"],
    icd10_codes=["Z96.651", "M23.200"],
    total_amount=30000.0,
    billed_amounts={
        "97161": 10000.0,
        "97110": 20000.0
    },
    primary_insurer="Plan A",
    secondary_insurer="Plan B",
    provider="ActiveRehab Physiotherapy Clinic (Network - Plan A, non-network - Plan B)"
)

priya_result = run_cob_agent(priya_claim)
print("\n[SUCCESS] Priya Sharma Claim Output:")
print(json.dumps(priya_result, indent=2))

# Save outputs to expected_console_output.txt
with open("expected_console_output.txt", "w", encoding="utf-8") as f:
    f.write("AARAV SHARMA CLAIM OUTPUT:\n")
    f.write(json.dumps(aarav_result, indent=2))
    f.write("\n\n" + "="*50 + "\n\n")
    f.write("PRIYA SHARMA CLAIM OUTPUT:\n")
    f.write(json.dumps(priya_result, indent=2))
