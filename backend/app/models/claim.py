from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class InsurancePlan(BaseModel):
    plan_name: str
    deductible: float = 0.0
    deductible_met: float = 0.0
    coinsurance_rate: float = 0.0  # Percentage paid by the insurer (e.g., 0.8 = 80%)
    oop_max: float = 0.0
    oop_met: float = 0.0
    covered_cpt_codes: List[str] = Field(default_factory=list)
    preauth_required_cpt_codes: List[str] = Field(default_factory=list)

class ParsedClaim(BaseModel):
    claim_id: str
    patient_name: str
    member_id: Optional[str] = None
    diagnosis: str
    cpt_codes: List[str] = Field(default_factory=list)
    icd10_codes: List[str] = Field(default_factory=list)
    total_amount: float
    billed_amounts: Dict[str, float] = Field(default_factory=dict)  # maps CPT -> billed amount
    primary_insurer: str
    secondary_insurer: str
    hospital: Optional[str] = None
    provider: Optional[str] = None
    network_status: Dict[str, str] = Field(default_factory=dict)  # maps plan/insurer name or id to "IN" or "OUT"

class COBResult(BaseModel):
    claim_id: str
    total_amount: float
    covered_amount: float
    uncovered_amount: float
    primary_deductible_applied: float
    primary_coinsurance_patient: float
    primary_oop_contribution: float
    primary_payment: float
    patient_responsibility_after_primary: float
    secondary_deductible_applied: float
    secondary_coinsurance_patient: float
    secondary_oop_contribution: float = 0.0
    secondary_payment: float

    final_patient_responsibility: float
    patient_liability_covered: float
    total_patient_cost: float
    is_valid: bool = True
    validation_message: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None

