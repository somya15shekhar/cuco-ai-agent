import os
import sys
import json

# Add the 'backend' directory to the search path so that 'app.services.parser' is resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.services.parser import parse_document

print("==============================")
print("RUNNING UNIFIED PARSER TESTS")
print("==============================\n")

# 1. IMAGE TEST
image_file = "backend/test_files/surgeon_estimate.png"
if os.path.exists(image_file):
    print("--- 1. IMAGE TEST (OCR -> LLM) ---")
    image_result = parse_document(image_file)
    print(json.dumps(image_result, indent=4))
else:
    print(f"Skipping Image Test: File not found at {image_file}")

print("\n------------------------------\n")

# 2. PDF TEST
pdf_file = "backend/test_files/aarav_mri_report.pdf"
if os.path.exists(pdf_file):
    print("--- 2. PDF TEST (PDF Parser -> LLM) ---")
    pdf_result = parse_document(pdf_file)
    print(json.dumps(pdf_result, indent=4))
else:
    print(f"Skipping PDF Test: File not found at {pdf_file}")

print("\n------------------------------\n")

# 3. TXT TEST
txt_file = "backend/test_files/user_query.txt"
if os.path.exists(txt_file):
    print("--- 3. TXT TEST (Read -> LLM) ---")
    txt_result = parse_document(txt_file)
    print(json.dumps(txt_result, indent=4))
else:
    print(f"Skipping TXT Test: File not found at {txt_file}")
