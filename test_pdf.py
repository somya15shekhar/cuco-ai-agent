import os
import sys

# Add the 'backend' directory to the search path so that 'app.services.pdf_parser' is resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.services.pdf_parser import extract_pdf_text

# Use the merged PDF file in backend/test_files
pdf_path = os.path.join("backend", "test_files", "aarav_mri_report.pdf")

if not os.path.exists(pdf_path):
    print(f"Error: Could not find PDF at {pdf_path}")
else:
    print(f"Reading PDF: {pdf_path}...")
    text = extract_pdf_text(pdf_path)
    print("\n--- EXTRACTED TEXT ---\n")
    print(text)
