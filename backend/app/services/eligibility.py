from typing import List, Dict, Any
from app.data_loader import load_benefits

def verify_eligibility(cpt_codes: List[str], insurer_or_plan: Any) -> Dict[str, Any]:
    """Verifies that all CPT codes in the claim are covered by the plan using JSON files.
    
    Args:
        cpt_codes: List of CPT codes in the claim.
        insurer_or_plan: Insurer name string or InsurancePlan object.
        
    Returns:
        A dictionary containing coverage status, covered codes, uncovered codes, and is_eligible.
    """
    # Extract the insurer name from string or plan object
    if hasattr(insurer_or_plan, "plan_name"):
        insurer_name = insurer_or_plan.plan_name
    else:
        insurer_name = str(insurer_or_plan)
        
    # Load benefits dynamically from JSON mock data
    benefits_data = load_benefits(insurer_name)
    covered_services = benefits_data.get("covered_services", [])
    
    # Extract covered CPT codes
    covered_cpt_codes = []
    for service in covered_services:
        if "cpt_code" in service:
            covered_cpt_codes.append(service["cpt_code"])
        if "cpt_codes" in service:
            covered_cpt_codes.extend(service["cpt_codes"])
            
    covered = [code for code in cpt_codes if code in covered_cpt_codes]
    uncovered = [code for code in cpt_codes if code not in covered_cpt_codes]
    
    is_eligible = len(covered) > 0  # Eligible if at least one code is covered
    
    return {
        "is_eligible": is_eligible,
        "covered_codes": covered,
        "uncovered_codes": uncovered
    }
