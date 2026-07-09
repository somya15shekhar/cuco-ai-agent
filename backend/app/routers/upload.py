from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.database import supabase
from postgrest.exceptions import APIError

router = APIRouter(prefix="/upload", tags=["Upload"])

@router.post("/")
async def upload_document(
    claim_id: str = Form(...),
    document_type: str = Form("mri_report"),
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()

        # 1. Upload to Supabase Storage (bucket name: "documents")
        storage_response = supabase.storage.from_("documents").upload(
            path=file.filename,
            file=contents,
            file_options={
                "content-type": file.content_type,
                "upsert": "true"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    db_data = None
    try:
        # 2. Insert metadata into the 'documents' table in database
        db_response = supabase.table("documents").insert({
            "claim_id": claim_id,
            "document_type": document_type,
            "file_name": file.filename,
            "storage_path": file.filename,
            "mime_type": file.content_type
        }).execute()
        db_data = db_response.data
    except APIError as e:
        # If database insert fails (e.g. missing table or constraints), we still return storage success with warning
        return {
            "message": "File uploaded to storage, but metadata database insertion failed.",
            "filename": file.filename,
            "error": str(e)
        }
    except Exception as e:
        return {
            "message": "File uploaded to storage, but metadata database insertion failed.",
            "filename": file.filename,
            "error": str(e)
        }

    return {
        "message": "File uploaded successfully and metadata stored",
        "filename": file.filename,
        "db_data": db_data
    }
