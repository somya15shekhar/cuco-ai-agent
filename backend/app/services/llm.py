import os
import json
import logging
from typing import Dict, Any

from groq import Groq
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    logger.warning("GROQ_API_KEY environment variable is not set. LLM service calls may fail.")

client = Groq(api_key=api_key)


def extract_claim_information(document_text: str) -> Dict[str, Any]:
    """Extracts structured claim fields from raw document text using Groq's LLM.

    Args:
        document_text (str): The raw text extracted from OCR or PDF.

    Returns:
        Dict[str, Any]: A dictionary containing extracted keys (patient_name, diagnosis, etc.).
    """
    if not document_text.strip():
        logger.warning("extract_claim_information called with empty document_text.")
        return {
            "patient_name": "",
            "diagnosis": "",
            "cpt_codes": [],
            "icd10_codes": [],
            "amount_inr": "",
            "hospital": "",
            "doctor": "",
            "document_type": ""
        }

    prompt = f"""
You are an AI medical insurance document parser.

Extract the following fields from the document.

Return ONLY valid JSON.

{{
    "patient_name":"",
    "diagnosis":"",
    "cpt_codes":[],
    "icd10_codes":[],
    "amount_inr":"",
    "hospital":"",
    "doctor":"",
    "document_type":""
}}

Document:

{document_text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,  # Forces deterministic output matching the exact context
            response_format={"type": "json_object"},  # Constraints LLM to respond in JSON format
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        raw_content = response.choices[0].message.content
        if not raw_content:
            raise ValueError("Empty response received from Groq API.")

        # Parse the JSON string into a Python dictionary
        parsed_data = json.loads(raw_content)
        return parsed_data

    except json.JSONDecodeError as jde:
        logger.error(f"Failed to decode LLM response JSON: {jde}. Raw content: {raw_content}")
        return {
            "patient_name": "",
            "diagnosis": "",
            "cpt_codes": [],
            "icd10_codes": [],
            "amount_inr": "",
            "hospital": "",
            "doctor": "",
            "document_type": "",
            "error": "Failed to parse structured response from LLM"
        }
    except Exception as e:
        logger.error(f"Error during Groq API execution: {str(e)}")
        raise RuntimeError(f"LLM extraction service failed: {str(e)}") from e
