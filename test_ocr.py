import os
import sys

# Add the 'backend' directory to the search path so that 'app.services.ocr' is found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.services.ocr import extract_image_text

# Use the merged PNG file in backend/test_files
image_path = os.path.join("backend", "test_files", "surgeon_estimate.png")

if not os.path.exists(image_path):
    print(f"Error: Could not find image at {image_path}")
else:
    print(f"Running OCR on {image_path}...\n")
    text = extract_image_text(image_path)
    print("--- EXTRACTED TEXT ---")
    print(text)