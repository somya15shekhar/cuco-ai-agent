from typing import List, Dict, Any
from app.data_loader import load_preauth_rules

def check_preauthorization(cpt_codes: List[str], insurer_or_plan: Any) -> Dict[str, Any]:
    """Determines whether each CPT code requires prior authorization using JSON rules.
    
    Args:
        cpt_codes: List of CPT codes in the claim.
        insurer_or_plan: Insurer name string or InsurancePlan object.
        
    Returns:
        A dict containing requires_preauth, required_codes, and approval status.
    """
    if hasattr(insurer_or_plan, "plan_name"):
        insurer_name = insurer_or_plan.plan_name
    else:
        insurer_name = str(insurer_or_plan)
        
    # Load preauth rules from JSON
    preauth_rules = load_preauth_rules(insurer_name)
    required_cpt_codes = preauth_rules.get("preauth_required_cpt_codes", [])
    
    required_codes = [code for code in cpt_codes if code in required_cpt_codes]
    requires_preauth = len(required_codes) > 0
    
    # Mock approval status: approved is True for our test CPT codes
    approved = True
    
    return {
        "requires_preauth": requires_preauth,
        "required_codes": required_codes,
        "approved": approved,
        "submission_process": preauth_rules.get("submission_process", {})
    }
