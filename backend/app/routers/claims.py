from fastapi import APIRouter, Query
from typing import Optional
from app.schemas.claim import ClaimCreate
from app.database import supabase

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.post("")
@router.post("/")
def create_claim(claim: ClaimCreate):
    """Create a new claim record in Supabase, linked to a household member."""
    payload = {
        "user_id": claim.user_id,
        "patient_name": claim.patient_name,
        "claim_type": claim.claim_type,
        "primary_insurer": claim.primary_insurer,
        "secondary_insurer": claim.secondary_insurer,
        "total_amount": claim.total_amount,
    }
    if claim.member_id:
        payload["member_id"] = claim.member_id
    if claim.household_id:
        payload["household_id"] = claim.household_id

    response = supabase.table("claims").insert(payload).execute()
    return response.data


@router.get("")
@router.get("/")
def list_claims(household_id: Optional[str] = Query(None)):
    """List claims, optionally filtered by household_id."""
    query = supabase.table("claims").select("*").order("created_at", desc=True)
    if household_id:
        query = query.eq("household_id", household_id)
    return query.execute().data