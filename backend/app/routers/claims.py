from fastapi import APIRouter
from app.schemas.claim import ClaimCreate
from app.database import supabase

router = APIRouter(prefix="/claims", tags=["Claims"])

@router.post("/")
def create_claim(claim: ClaimCreate):

    response = (
        supabase.table("claims")
        .insert({
            "patient_name": claim.patient_name,
            "claim_type": claim.claim_type,
            "primary_insurer": claim.primary_insurer,
            "secondary_insurer": claim.secondary_insurer,
            "total_amount": claim.total_amount
        })
        .execute()
    )

    return response.data