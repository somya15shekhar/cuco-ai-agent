from pydantic import BaseModel

class ClaimCreate(BaseModel):
    patient_name: str
    claim_type: str
    primary_insurer: str
    secondary_insurer: str
    total_amount: float