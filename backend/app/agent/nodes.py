from typing import Dict, Any, List

from app.models.claim import ParsedClaim, InsurancePlan, COBResult
from app.agent.state import AgentState
from app.services.eligibility import verify_eligibility
from app.services.preauth import check_preauthorization
from app.services.cob import calculate_cob, reconcile_ledger
from app.services.llm import client
from app.data_loader import load_member, load_plan

def intake_node(state: AgentState) -> Dict[str, Any]:
    """Prepares the state for claim processing, initializing patient and insurer keys."""
    log = state.get("execution_log", []) + ["IntakeNode: Initializing claims workflow from members.json."]
    claim = state["parsed_claim"]
    
    try:
        member = load_member(claim.patient_name)
        member_id = member.get("member_id")
        current_claim_info = member.get("current_claim", {})
        
        prim_key = current_claim_info.get("primary_insurer_for_this_claim", "planA")
        sec_key = current_claim_info.get("secondary_insurer_for_this_claim", "planB")
        
        # Resolve insurer names (e.g. Insurer1 vs Insurer2)
        prim_insurer = "insurer1"
        sec_insurer = "insurer2"
        for policy in member.get("policies", []):
            if policy.get("plan_id") == prim_key:
                prim_insurer = policy.get("insurer")
            if policy.get("plan_id") == sec_key:
                sec_insurer = policy.get("insurer")
                
        log.append(f"IntakeNode: Loaded member {claim.patient_name} ({member_id}). "
                   f"Primary Insurer: {prim_insurer}, Secondary Insurer: {sec_insurer}.")
    except Exception as e:
        log.append(f"IntakeNode: Member lookup failed. Using defaults. Error: {str(e)}")
        
    return {
        "retry_count": 0,
        "validation_errors": [],
        "reflection_notes": None,
        "execution_log": log,
        "primary_plan": None,
        "secondary_plan": None
    }

def eligibility_node(state: AgentState) -> Dict[str, Any]:
    """Verifies eligibility of the claim CPT codes against the dynamic primary plan."""
    log = state.get("execution_log", []) + ["EligibilityNode: Checking CPT eligibility against primary plan."]
    claim = state["parsed_claim"]
    
    try:
        member = load_member(claim.patient_name)
        current_claim_info = member.get("current_claim", {})
        prim_key = current_claim_info.get("primary_insurer_for_this_claim", "planA")
        
        prim_insurer = "insurer1"
        for policy in member.get("policies", []):
            if policy.get("plan_id") == prim_key:
                prim_insurer = policy.get("insurer")
                break
    except Exception:
        prim_insurer = "insurer1"
        
    status = verify_eligibility(claim.cpt_codes, prim_insurer)
    
    log.append(f"EligibilityNode: Eligibility verification complete. Eligible: {status['is_eligible']}.")
    return {
        "eligibility_status": status,
        "execution_log": log
    }

def preauth_node(state: AgentState) -> Dict[str, Any]:
    """Checks preauthorization requirements dynamically."""
    log = state.get("execution_log", []) + ["PreAuthNode: Checking CPT preauthorization requirements."]
    claim = state["parsed_claim"]
    
    try:
        member = load_member(claim.patient_name)
        current_claim_info = member.get("current_claim", {})
        prim_key = current_claim_info.get("primary_insurer_for_this_claim", "planA")
        
        prim_insurer = "insurer1"
        for policy in member.get("policies", []):
            if policy.get("plan_id") == prim_key:
                prim_insurer = policy.get("insurer")
                break
    except Exception:
        prim_insurer = "insurer1"
        
    status = check_preauthorization(claim.cpt_codes, prim_insurer)
    
    log.append(f"PreAuthNode: Preauth check complete. Requires Preauth: {status['requires_preauth']}.")
    return {
        "preauth_status": status,
        "execution_log": log
    }

def fetch_primary_plan_node(state: AgentState) -> Dict[str, Any]:
    """Fetches details for the primary insurance plan dynamically."""
    log = state.get("execution_log", []) + ["FetchPrimaryPlanNode: Fetching primary plan details."]
    claim = state["parsed_claim"]
    
    try:
        member = load_member(claim.patient_name)
        current_claim_info = member.get("current_claim", {})
        prim_key = current_claim_info.get("primary_insurer_for_this_claim", "planA")
        
        prim_insurer = "insurer1"
        for policy in member.get("policies", []):
            if policy.get("plan_id") == prim_key:
                prim_insurer = policy.get("insurer")
                break
                
        plan = load_plan(prim_insurer, member_id=member.get("member_id"))
    except Exception as e:
        plan = load_plan("insurer1")
        log.append(f"FetchPrimaryPlanNode: Fallback to default insurer1. Error: {str(e)}")
        
    log.append(f"FetchPrimaryPlanNode: Primary plan loaded: {plan.plan_name}")
    return {
        "primary_plan": plan,
        "execution_log": log
    }

def fetch_secondary_plan_node(state: AgentState) -> Dict[str, Any]:
    """Fetches details for the secondary insurance plan dynamically."""
    log = state.get("execution_log", []) + ["FetchSecondaryPlanNode: Fetching secondary plan details."]
    claim = state["parsed_claim"]
    
    try:
        member = load_member(claim.patient_name)
        current_claim_info = member.get("current_claim", {})
        sec_key = current_claim_info.get("secondary_insurer_for_this_claim", "planB")
        
        sec_insurer = "insurer2"
        for policy in member.get("policies", []):
            if policy.get("plan_id") == sec_key:
                sec_insurer = policy.get("insurer")
                break
                
        plan = load_plan(sec_insurer, member_id=member.get("member_id"))
    except Exception as e:
        plan = load_plan("insurer2")
        log.append(f"FetchSecondaryPlanNode: Fallback to default insurer2. Error: {str(e)}")
        
    log.append(f"FetchSecondaryPlanNode: Secondary plan loaded: {plan.plan_name}")
    return {
        "secondary_plan": plan,
        "execution_log": log
    }

def cob_node(state: AgentState) -> Dict[str, Any]:
    """Performs Coordination of Benefits calculations using dynamic data."""
    retry = state.get("retry_count", 0)
    log = state.get("execution_log", []) + [f"COBNode: Running COB calculation engine (Attempt {retry})."]
    
    claim = state["parsed_claim"]
    primary = state["primary_plan"]
    secondary = state["secondary_plan"]
    
    # Run dynamic calculations
    result = calculate_cob(claim, primary, secondary)
    
    # Artificial validation discrepancy on first attempt to demonstrate reflection loop
    if retry == 0:
        result.final_patient_responsibility += 100.0  # Simulate a math error of $100
        result.patient_liability_covered += 100.0
        result.total_patient_cost += 100.0
        if result.explanation:
            if "patient" in result.explanation:
                result.explanation["patient"]["final_responsibility"] += 100.0
                result.explanation["patient"]["patient_liability_covered"] += 100.0
                result.explanation["patient"]["total_patient_cost"] += 100.0
            if "ledger" in result.explanation:
                result.explanation["ledger"]["patient_responsibility"] += 100.0
        result.is_valid = False
        result.validation_message = "Patient responsibility does not reconcile with payment breakdown."
        log.append("COBNode: Simulated mathematical discrepancy injected for testing reflection.")
        
    return {
        "cob_result": result,
        "execution_log": log
    }

def validation_node(state: AgentState) -> Dict[str, Any]:
    """Validates the financial correctness of the COB calculations."""
    log = state.get("execution_log", []) + ["ValidationNode: Validating financial ledger reconciliation."]
    result = state["cob_result"]
    errors = []
    
    # Ledger validation check using reconcile_ledger
    is_valid = reconcile_ledger(
        total_billed=result.total_amount,
        primary_payment=result.primary_payment,
        secondary_payment=result.secondary_payment,
        patient_responsibility=result.final_patient_responsibility,
        uncovered_amount=result.uncovered_amount
    )
    
    if not is_valid:
        calculated_total = (
            result.primary_payment + 
            result.secondary_payment + 
            result.final_patient_responsibility + 
            result.uncovered_amount
        )
        errors.append(
            f"Ledger Mismatch: Primary Payment ({result.primary_payment}) + Secondary Payment "
            f"({result.secondary_payment}) + Patient Responsibility ({result.final_patient_responsibility}) "
            f"+ Uncovered Amount ({result.uncovered_amount}) = {calculated_total}, which does not match "
            f"Total Claim Amount ({result.total_amount}). Discrepancy is {round(calculated_total - result.total_amount, 2)}."
        )
        
    if result.primary_payment < 0 or result.secondary_payment < 0 or result.final_patient_responsibility < 0:
        errors.append("Validation Error: Negative values detected in payment amounts.")
        
    log.append(f"ValidationNode: Completed validation. Found {len(errors)} error(s).")
    return {
        "validation_errors": errors,
        "execution_log": log
    }

def reflection_node(state: AgentState) -> Dict[str, Any]:
    """Uses Groq LLM to diagnose validation failures."""
    log = state.get("execution_log", []) + ["ReflectionNode: Analyzing validation failure with Groq LLM."]
    errors = state.get("validation_errors", [])
    claim = state["parsed_claim"]
    cob = state["cob_result"]
    
    errors_str = "\n".join(f"- {e}" for e in errors)
    prompt = f"""
You are an expert insurance claim auditor. The Coordination of Benefits (COB) calculations failed validation.

Claim Details:
- Claim ID: {claim.claim_id}
- Total Billed: ${claim.total_amount}

Calculated Breakdown:
- Primary Payment: ${cob.primary_payment}
- Secondary Payment: ${cob.secondary_payment}
- Uncovered Billed: ${cob.uncovered_amount}
- Patient Responsibility: ${cob.final_patient_responsibility}

Validation Errors:
{errors_str}

Analyze the calculation results, identify why the ledger does not reconcile, and explain the issue clearly. 
DO NOT recalculate the figures yourself (calculations must remain deterministic). Simply explain the mismatch and declare that the COB engine must be re-run on retry without the error.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a helpful insurance coordination audit assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        notes = response.choices[0].message.content
    except Exception as e:
        notes = f"Reflection error: Groq API call failed: {str(e)}"
        
    log.append(f"ReflectionNode: Groq diagnosis generated.")
    
    current_retry = state.get("retry_count", 0)
    return {
        "reflection_notes": notes,
        "retry_count": current_retry + 1,
        "validation_errors": [],  # Clear current validation errors for the next run
        "execution_log": log
    }

def output_node(state: AgentState) -> Dict[str, Any]:
    """Generates the structured JSON outputs from the state."""
    log = state.get("execution_log", []) + ["OutputNode: Claim processing completed successfully."]
    cob = state.get("cob_result")
    claim = state["parsed_claim"]
    primary = state.get("primary_plan")
    secondary = state.get("secondary_plan")
    
    if cob is None:
        eligibility = state.get("eligibility_status") or {}
        reason = "Claim is ineligible (uncovered or empty CPT codes)."
        if eligibility and not eligibility.get("is_eligible", False):
            reason = f"Claim is ineligible. CPT codes checked: {claim.cpt_codes or 'None'}."
            
        final_output = {
            "claim_summary": {
                "claim_id": claim.claim_id,
                "patient_name": claim.patient_name,
                "diagnosis": claim.diagnosis,
                "total_billed": claim.total_amount,
                "primary_insurer": claim.primary_insurer,
                "secondary_insurer": claim.secondary_insurer,
            },
            "payment_breakdown": {
                "primary_insurer_payment": 0.0,
                "secondary_insurer_payment": 0.0,
                "uncovered_amount": claim.total_amount,
            },
            "patient_responsibility": {
                "final_patient_responsibility": claim.total_amount,
                "patient_liability_covered": 0.0,
                "uncovered_amount": claim.total_amount,
                "total_patient_cost": claim.total_amount,
                "primary_deductible_applied": 0.0,
                "primary_coinsurance_patient": 0.0,
                "primary_oop_contribution": 0.0,
                "secondary_deductible_applied": 0.0,
                "secondary_coinsurance_patient": 0.0,
                "secondary_oop_contribution": 0.0,
            },
            "validation_status": {
                "is_valid": False,
                "retry_count": state.get("retry_count", 0),
                "reflection_notes": reason,
            },
            "explanation": {
                "general_notes": reason
            },
            "workflow_log": log
        }
        return {
            "final_output": final_output,
            "execution_log": log
        }

    # Perform accumulator updates on the final successful result
    from app.services.cob import update_accumulators
    if primary:
        update_accumulators(primary, cob.primary_deductible_applied, cob.primary_oop_contribution)
    if secondary:
        update_accumulators(secondary, cob.secondary_deductible_applied, cob.secondary_oop_contribution)
    
    final_output = {
        "claim_summary": {
            "claim_id": claim.claim_id,
            "patient_name": claim.patient_name,
            "diagnosis": claim.diagnosis,
            "total_billed": claim.total_amount,
            "primary_insurer": claim.primary_insurer,
            "secondary_insurer": claim.secondary_insurer,
        },
        "payment_breakdown": {
            "primary_insurer_payment": cob.primary_payment,
            "secondary_insurer_payment": cob.secondary_payment,
            "uncovered_amount": cob.uncovered_amount,
        },
        "patient_responsibility": {
            "final_patient_responsibility": cob.final_patient_responsibility,
            "patient_liability_covered": cob.patient_liability_covered,
            "uncovered_amount": cob.uncovered_amount,
            "total_patient_cost": cob.total_patient_cost,
            "primary_deductible_applied": cob.primary_deductible_applied,
            "primary_coinsurance_patient": cob.primary_coinsurance_patient,
            "primary_oop_contribution": cob.primary_oop_contribution,
            "secondary_deductible_applied": cob.secondary_deductible_applied,
            "secondary_coinsurance_patient": cob.secondary_coinsurance_patient,
            "secondary_oop_contribution": cob.secondary_oop_contribution,
        },
        "validation_status": {
            "is_valid": len(state.get("validation_errors", [])) == 0,
            "retry_count": state.get("retry_count", 0),
            "reflection_notes": state.get("reflection_notes"),
        },
        "explanation": cob.explanation,
        "workflow_log": log
    }
    
    return {
        "final_output": final_output,
        "execution_log": log
    }

