from typing import TypedDict, Optional, List, Dict, Any
from app.models.claim import ParsedClaim, InsurancePlan, COBResult

class AgentState(TypedDict):
    """The state tracker for the LangGraph insurance coordination agent."""
    parsed_claim: ParsedClaim
    primary_plan: Optional[InsurancePlan]
    secondary_plan: Optional[InsurancePlan]
    eligibility_status: Optional[Dict[str, Any]]
    preauth_status: Optional[Dict[str, Any]]
    cob_result: Optional[COBResult]
    validation_errors: Optional[List[str]]
    reflection_notes: Optional[str]
    retry_count: int
    final_output: Optional[Dict[str, Any]]
    execution_log: List[str]
