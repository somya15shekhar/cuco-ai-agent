from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.models.claim import InsurancePlan
from app.services.eligibility import verify_eligibility
from app.services.preauth import check_preauthorization
from app.data_loader import load_plan

router = APIRouter(prefix="/insurance", tags=["Insurance"])

class CPTRequest(BaseModel):
    cpt_codes: List[str]
    insurer: Optional[str] = None
    plan_name: Optional[str] = None
    member_id: Optional[str] = None

@router.get("/{insurer}", response_model=InsurancePlan)
def get_insurer_plan(insurer: str, member_id: Optional[str] = None):
    """Loads plan details dynamically from JSON based on insurer/plan key."""
    try:
        return load_plan(insurer, member_id=member_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/eligibility")
def check_eligibility_endpoint(request: CPTRequest):
    """Checks eligibility for a list of CPT codes against the specified insurer plan."""
    try:
        insurer_key = request.insurer or request.plan_name or "insurer1"
        plan = load_plan(insurer_key, member_id=request.member_id)
        return verify_eligibility(request.cpt_codes, plan)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/preauth")
def check_preauth_endpoint(request: CPTRequest):
    """Checks preauthorization requirements for a list of CPT codes against the specified insurer plan."""
    try:
        insurer_key = request.insurer or request.plan_name or "insurer1"
        plan = load_plan(insurer_key, member_id=request.member_id)
        return check_preauthorization(request.cpt_codes, plan)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
