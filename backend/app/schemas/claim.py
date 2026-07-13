from pydantic import BaseModel
from typing import Optional

class ClaimCreate(BaseModel):
    user_id: str
    patient_name: str
    claim_type: str
    primary_insurer: str
    secondary_insurer: str
    total_amount: float
    member_id: Optional[str] = None
    household_id: Optional[str] = None