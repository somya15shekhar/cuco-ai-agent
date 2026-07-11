import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.database import supabase
from app.services.ocr import extract_image_text
from app.services.pdf_parser import extract_pdf_text
from app.services.llm import extract_claim_information

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parse", tags=["Parse"])


@router.post("")
@router.post("/")
async def parse_claim_document(
    claim_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    FastAPI endpoint that accepts a claim document file and claim ID,
    detects its extension, extracts the text, passes it to Groq LLM for
    structured parsing, and saves the final result to the Supabase database.
    """
    temp_dir = os.path.abspath("backend/temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)

    extension = os.path.splitext(file.filename)[1].lower()
    temp_file_path = os.path.join(temp_dir, f"temp_{claim_id}{extension}")

    # 1. Save uploaded file to temporary path in workspace
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write temp file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to write uploaded file to disk."
        )

    try:
        # 2. Extract text based on file format
        if extension in [".png", ".jpg", ".jpeg"]:
            raw_text = extract_image_text(temp_file_path)
        elif extension == ".pdf":
            raw_text = extract_pdf_text(temp_file_path)
        elif extension == ".txt":
            with open(temp_file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{extension}'. Supported types: PNG, JPG, JPEG, PDF, TXT."
            )

        if not raw_text.strip():
            raise HTTPException(
                status_code=422,
                detail="Extracted document text is empty. Cannot parse fields."
            )

        # 3. Use LLM to extract claim fields
        structured_json = extract_claim_information(raw_text)

        # 4. Map structured fields to database schema format
        # Safely convert amount_inr to a float value
        total_amount = 0.0
        amount_raw = structured_json.get("amount_inr")
        if amount_raw:
            try:
                # Retain only digits and decimal points
                amount_clean = "".join(c for c in str(amount_raw) if c.isdigit() or c == ".")
                total_amount = float(amount_clean) if amount_clean else 0.0
            except ValueError:
                total_amount = 0.0

        # Combine doctor and hospital info for provider_name
        provider_name = structured_json.get("hospital") or ""
        doctor_name = structured_json.get("doctor") or ""
        if doctor_name:
            provider_name = f"{doctor_name} - {provider_name}" if provider_name else doctor_name

        # Prepare database schema payload
        payload = {
            "claim_id": claim_id,
            "patient_name": structured_json.get("patient_name") or "",
            "provider_name": provider_name,
            "diagnosis": structured_json.get("diagnosis") or "",
            "icd_codes": structured_json.get("icd10_codes") or [],
            "cpt_codes": structured_json.get("cpt_codes") or [],
            "line_items": [],
            "total_amount": total_amount,
            "confidence": 0.95,
            "raw_text": raw_text,
            "parsed_json": structured_json
        }

        # 5. Upsert parsed claim metadata into Supabase to handle re-adjudications gracefully
        db_response = supabase.table("parsed_claims").upsert(payload, on_conflict="claim_id").execute()
        if not db_response.data:
            raise HTTPException(
                status_code=500,
                detail="Successfully upserted parsed data, but no verification data was returned."
            )

        return {"status": "success"}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during claim parsing or database insertion: {str(e)}"
        )
    finally:
        # 6. Ensure the temporary file is deleted in all execution flows
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as delete_error:
                logger.error(f"Failed to delete temp file {temp_file_path}: {str(delete_error)}")
