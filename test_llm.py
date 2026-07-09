import os
import sys

# Add the 'backend' directory to the search path so that 'app.services.llm' is resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.services.llm import extract_claim_information

sample_text = """
Patient Name : Aarav Sharma

Diagnosis:
Complete tear of anterior cruciate ligament.

CPT 29888

Estimated Charges ₹350000

Hospital:
Orthopaedic Sports Center
"""

print("Running LLM information extraction...")
result = extract_claim_information(sample_text)

print("\n--- EXTRACTED JSON STRUCTURE ---")
import json
print(json.dumps(result, indent=4))