from typing import Dict, Any, List
from app.models.claim import ParsedClaim, InsurancePlan, COBResult
from app.data_loader import load_coverage_rules

def calculate_cob(claim: ParsedClaim, primary_plan: InsurancePlan, secondary_plan: InsurancePlan) -> COBResult:
    """Calculates Coordination of Benefits dynamically based on coverage rules from JSON.
    
    Args:
        claim: The ParsedClaim.
        primary_plan: The primary InsurancePlan.
        secondary_plan: The secondary InsurancePlan.
        
    Returns:
        A structured COBResult.
    """
    # 1. Load coverage rules dynamically
    prim_rules = load_coverage_rules(primary_plan.plan_name)
    sec_rules = load_coverage_rules(secondary_plan.plan_name)
    
    # Extract deductibles, coinsurance, and OOP limits from rules JSON
    ded_amt_p = float(prim_rules.get("step1_deductible", {}).get("amount_inr", 0.0))
    coins_rate_p = float(prim_rules.get("step2_coinsurance", {}).get("insurer_pays_percent", 0.0)) / 100.0
    oop_max_p = float(prim_rules.get("step3_oop_max_check", {}).get("oop_max_inr", 
                       prim_rules.get("step4_oop_max_check", {}).get("oop_max_inr", 0.0)))
                       
    ded_amt_s = float(sec_rules.get("step1_deductible", {}).get("amount_inr", 0.0))
    coins_rate_s = float(sec_rules.get("step2_coinsurance", {}).get("insurer_pays_percent", 0.0)) / 100.0
    oop_max_s = float(sec_rules.get("step3_oop_max_check", {}).get("oop_max_inr", 
                       sec_rules.get("step4_oop_max_check", {}).get("oop_max_inr", 0.0)))
                       
    # Parse PT sub-limits
    pt_limit_p = prim_rules.get("pt_sub_limit", {})
    pt_cpts_p = pt_limit_p.get("applies_to_cpt", [])
    pt_cap_p = float(pt_limit_p.get("sub_limit_inr", 999999.0))
    
    pt_limit_s = sec_rules.get("pt_sub_limit", {})
    pt_cpts_s = pt_limit_s.get("applies_to_cpt", [])
    pt_cap_s = float(pt_limit_s.get("sub_limit_inr", 999999.0))
    
    # Network status checks
    provider_str = (getattr(claim, "hospital", "") or getattr(claim, "provider", "") or "").lower()
    
    def is_network(plan_id: str) -> bool:
        p_key = plan_id.lower()
        if f"non-network - {p_key}" in provider_str or f"non-network - plan {p_key[-1].lower()}" in provider_str:
            return False
        return True

    is_network_p = is_network("planA" if primary_plan.plan_name == "SecureHealth Premier" else "planB")
    is_network_s = is_network("planA" if secondary_plan.plan_name == "SecureHealth Premier" else "planB")

    # Copay definitions
    copay_rate_p = 0.0
    if not is_network_p:
        copay_rate_p = float(prim_rules.get("step3_copay_non_network", {}).get("copay_percent", 
                             prim_rules.get("step4_copay_non_network", {}).get("copay_percent", 10.0))) / 100.0

    copay_rate_s = 0.0
    if not is_network_s:
        copay_rate_s = float(sec_rules.get("step3_copay_non_network", {}).get("copay_percent", 
                             sec_rules.get("step4_copay_non_network", {}).get("copay_percent", 10.0))) / 100.0

    # 2. Distribute total_amount across CPT codes
    cpt_amounts = {}
    if claim.billed_amounts:
        cpt_amounts = dict(claim.billed_amounts)
    elif claim.cpt_codes:
        avg_amt = claim.total_amount / len(claim.cpt_codes)
        cpt_amounts = {code: avg_amt for code in claim.cpt_codes}
    else:
        cpt_amounts = {"UNKNOWN": claim.total_amount}

    total_amount = claim.total_amount
    covered_amount = 0.0
    uncovered_amount = 0.0
    
    primary_deductible_applied = 0.0
    primary_coinsurance_patient = 0.0
    primary_oop_applied = 0.0
    primary_payment = 0.0
    patient_responsibility_after_primary = 0.0
    
    secondary_deductible_applied = 0.0
    secondary_coinsurance_patient = 0.0
    secondary_payment = 0.0
    final_patient_responsibility = 0.0
    
    # Track remaining accumulators
    rem_ded_p = max(0.0, ded_amt_p - primary_plan.deductible_met)
    rem_oop_p = max(0.0, oop_max_p - primary_plan.oop_met)
    
    # Secondary deductible application (deductible met lookup)
    rem_ded_s = max(0.0, ded_amt_s - secondary_plan.deductible_met)
    rem_oop_s = max(0.0, oop_max_s - secondary_plan.oop_met)

    for cpt_code, billed in cpt_amounts.items():
        is_cov_p = cpt_code in primary_plan.covered_cpt_codes
        is_cov_s = cpt_code in secondary_plan.covered_cpt_codes
        
        if is_cov_p or is_cov_s:
            covered_amount += billed
        else:
            uncovered_amount += billed

        # --- Primary Calculation ---
        if is_cov_p:
            # Apply PT sub-limit if CPT is physical therapy
            is_pt_p = cpt_code in pt_cpts_p
            admissible_p = min(billed, pt_cap_p) if is_pt_p else billed
            uncovered_cpt_p = billed - admissible_p
            
            # Apply remaining primary deductible
            ded_applied_p = min(admissible_p, rem_ded_p)
            rem_ded_p -= ded_applied_p
            primary_deductible_applied += ded_applied_p
            
            # Apply coinsurance and copay
            after_ded_p = admissible_p - ded_applied_p
            coins_patient_p = after_ded_p * (1.0 - coins_rate_p)
            copay_patient_p = after_ded_p * coins_rate_p * copay_rate_p
            
            pat_resp_p = ded_applied_p + coins_patient_p + copay_patient_p
            
            # Apply OOP max limit
            oop_applied_p = min(pat_resp_p, rem_oop_p)
            primary_oop_applied += oop_applied_p
            rem_oop_p -= oop_applied_p
            
            # Insurer pays the rest of admissible
            cpt_primary_payment = admissible_p - oop_applied_p
            primary_coinsurance_patient += coins_patient_p
            
            cpt_pat_resp_after_p = oop_applied_p + uncovered_cpt_p
        else:
            cpt_primary_payment = 0.0
            cpt_pat_resp_after_p = billed
            
        primary_payment += cpt_primary_payment
        patient_responsibility_after_primary += cpt_pat_resp_after_p
        
        # --- Secondary Calculation ---
        if is_cov_s:
            # Secondary Plan calculates what it pays based on residual balance from primary
            residual = cpt_pat_resp_after_p
            
            # Apply PT sub-limit under secondary plan
            is_pt_s = cpt_code in pt_cpts_s
            admissible_s = min(billed, pt_cap_s) if is_pt_s else billed
            
            # In COB coordination, secondary covers only up to secondary admissible limits
            # Cap the residual balance by the secondary plan's CPT sub-limit if applicable
            residual_admissible = min(residual, admissible_s)
            uncovered_cpt_s = residual - residual_admissible
            
            # Apply secondary deductible to the residual balance
            ded_applied_s = min(residual_admissible, rem_ded_s)
            rem_ded_s -= ded_applied_s
            secondary_deductible_applied += ded_applied_s
            
            # Apply secondary coinsurance and copay to the remaining residual
            after_ded_s = residual_admissible - ded_applied_s
            cpt_secondary_payment = after_ded_s * coins_rate_s * (1.0 - copay_rate_s)
            
            # Ensure the secondary insurer does not pay more than residual
            cpt_secondary_payment = min(cpt_secondary_payment, residual_admissible)
            
            # Secondary patient share
            sec_coins_patient = after_ded_s * (1.0 - coins_rate_s)
            sec_copay_patient = after_ded_s * coins_rate_s * copay_rate_s
            secondary_coinsurance_patient += (sec_coins_patient + sec_copay_patient)
            
            cpt_final_pat_resp = residual - cpt_secondary_payment
        else:
            cpt_secondary_payment = 0.0
            cpt_final_pat_resp = cpt_pat_resp_after_p
            
        secondary_payment += cpt_secondary_payment
        final_patient_responsibility += cpt_final_pat_resp

    return COBResult(
        claim_id=claim.claim_id,
        total_amount=round(total_amount, 2),
        covered_amount=round(covered_amount, 2),
        uncovered_amount=round(uncovered_amount, 2),
        primary_deductible_applied=round(primary_deductible_applied, 2),
        primary_coinsurance_patient=round(primary_coinsurance_patient, 2),
        primary_oop_applied=round(primary_oop_applied, 2),
        primary_payment=round(primary_payment, 2),
        patient_responsibility_after_primary=round(patient_responsibility_after_primary, 2),
        secondary_deductible_applied=round(secondary_deductible_applied, 2),
        secondary_coinsurance_patient=round(secondary_coinsurance_patient, 2),
        secondary_payment=round(secondary_payment, 2),
        final_patient_responsibility=round(final_patient_responsibility, 2),
        is_valid=True
    )
