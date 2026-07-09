import os
from typing import Dict, Any

from app.services.ocr import extract_image_text
from app.services.pdf_parser import extract_pdf_text
from app.services.llm import extract_claim_information


def parse_document(file_path: str) -> Dict[str, Any]:
    """Automatically detects document format, extracts text, and parses structured claim data using an LLM.

    Args:
        file_path (str): Path to the claim document file.

    Returns:
        Dict[str, Any]: The parsed structured claim database entries.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Claim file not found at: {file_path}")

    extension = os.path.splitext(file_path)[1].lower()

    if extension in [".png", ".jpg", ".jpeg"]:
        raw_text = extract_image_text(file_path)

    elif extension == ".pdf":
        raw_text = extract_pdf_text(file_path)

    elif extension == ".txt":
        with open(file_path, "r", encoding="utf-8") as file:
            raw_text = file.read()

    else:
        raise ValueError(f"Unsupported file type: {extension}")

    structured_json = extract_claim_information(raw_text)

    return structured_json
