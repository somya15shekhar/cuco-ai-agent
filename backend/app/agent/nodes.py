"""
LangGraph agent nodes — Supabase-backed via MemberService.

Member/insurer data comes from Supabase.
Insurance plan *rules* still come from JSON config via data_loader.
"""

from typing import Dict, Any, List

from app.models.claim import ParsedClaim, InsurancePlan, COBResult
from app.agent.state import AgentState
from app.services.eligibility import verify_eligibility
from app.services.preauth import check_preauthorization
from app.services.cob import calculate_cob, reconcile_ledger
from app.services.llm import client
from app.services.member_service import MemberService
from app.data_loader import load_plan


# ------------------------------------------------------------------
# Shared helper — resolves member + insurer keys from Supabase
# ------------------------------------------------------------------

def _resolve_member(state: AgentState) -> Dict[str, Any]:
    """Return cached member_data from state, or fetch from Supabase."""
    cached = state.get("member_data")
    if cached:
        return cached

    claim = state["parsed_claim"]

    # Prefer member_id; fall back to name lookup
    if claim.member_id:
        member = MemberService.get_member(claim.member_id)
    else:
        member = MemberService.get_member_by_name(claim.patient_name)

    if not member:
        return None

    member_id = member["id"]
    insurances = MemberService.get_member_insurance(member_id)

    # Match requested primary/secondary names to keys to respect IRDAI choice right
    def resolve_key(name: str) -> str:
        n = name.lower().strip() if name else ""
        if "plan a" in n or "insurer1" in n or "securehealth" in n:
            return "insurer1"
        if "plan b" in n or "insurer2" in n or "flexicare" in n:
            return "insurer2"
        return n

    req_prim = resolve_key(claim.primary_insurer)
    req_sec = resolve_key(claim.secondary_insurer)

    prim_key = None
    sec_key = None

    for ins in insurances:
        ik = ins["insurer_key"]
        if ik == req_prim:
            prim_key = ik
        elif ik == req_sec:
            sec_key = ik

    # Fallback to database enrollment order
    if not prim_key and insurances:
        prim_key = insurances[0]["insurer_key"]
    if not sec_key and len(insurances) > 1:
        for ins in insurances:
            if ins["insurer_key"] != prim_key:
                sec_key = ins["insurer_key"]
                break

    return {
        "member_id": member_id,
        "member_name": member.get("member_name", ""),
        "insurances": insurances,
        "primary_insurer_key": prim_key,
        "secondary_insurer_key": sec_key,
    }


# ------------------------------------------------------------------
# Node implementations
# ------------------------------------------------------------------


def intake_node(state: AgentState) -> Dict[str, Any]:
    """Fetch member data from Supabase and store in state for all nodes."""
    log = state.get("execution_log", []) + [
        "IntakeNode: Initializing claims workflow from Supabase."
    ]
    member_data = _resolve_member(state)

    if member_data:
        prim_name = MemberService.resolve_plan_name(member_data["primary_insurer_key"] or "")
        sec_name = MemberService.resolve_plan_name(member_data["secondary_insurer_key"] or "")
        log.append(
            f"IntakeNode: Loaded member {member_data['member_name']} "
            f"({member_data['member_id']}). "
            f"Primary: {prim_name}, Secondary: {sec_name}."
        )
    else:
        log.append("IntakeNode: Member lookup failed. Using defaults.")

    return {
        "member_data": member_data,
        "retry_count": 0,
        "validation_errors": [],
        "reflection_notes": None,
        "execution_log": log,
        "primary_plan": None,
        "secondary_plan": None,
    }


def eligibility_node(state: AgentState) -> Dict[str, Any]:
    """Verify CPT eligibility against the primary insurer's plan."""
    log = state.get("execution_log", []) + [
        "EligibilityNode: Checking CPT eligibility against primary plan."
    ]
    claim = state["parsed_claim"]
    member_data = state.get("member_data")

    prim_key = (member_data or {}).get("primary_insurer_key", "insurer1") or "insurer1"
    status = verify_eligibility(claim.cpt_codes, prim_key)

    log.append(
        f"EligibilityNode: Eligibility verification complete. "
        f"Eligible: {status['is_eligible']}."
    )
    return {"eligibility_status": status, "execution_log": log}


def preauth_node(state: AgentState) -> Dict[str, Any]:
    """Check preauthorization requirements against the primary plan."""
    log = state.get("execution_log", []) + [
        "PreAuthNode: Checking CPT preauthorization requirements."
    ]
    claim = state["parsed_claim"]
    member_data = state.get("member_data")

    prim_key = (member_data or {}).get("primary_insurer_key", "insurer1") or "insurer1"
    status = check_preauthorization(claim.cpt_codes, prim_key)

    log.append(
        f"PreAuthNode: Preauth check complete. "
        f"Requires Preauth: {status['requires_preauth']}."
    )
    return {"preauth_status": status, "execution_log": log}


def fetch_primary_plan_node(state: AgentState) -> Dict[str, Any]:
    """Load primary InsurancePlan from JSON with Supabase accumulators."""
    log = state.get("execution_log", []) + [
        "FetchPrimaryPlanNode: Fetching primary plan details."
    ]
    member_data = state.get("member_data")

    prim_key = (member_data or {}).get("primary_insurer_key") or "insurer1"
    member_id = (member_data or {}).get("member_id")

    ded_met, oop_met = 0.0, 0.0
    if member_id:
        ded_met, oop_met = MemberService.get_accumulators(member_id, prim_key)

    try:
        plan = load_plan(prim_key, deductible_met=ded_met, oop_met=oop_met)
    except Exception as e:
        plan = load_plan("insurer1")
        log.append(f"FetchPrimaryPlanNode: Fallback to insurer1. Error: {e}")

    log.append(f"FetchPrimaryPlanNode: Primary plan loaded: {plan.plan_name}")
    return {"primary_plan": plan, "execution_log": log}


def fetch_secondary_plan_node(state: AgentState) -> Dict[str, Any]:
    """Load secondary InsurancePlan from JSON with Supabase accumulators."""
    log = state.get("execution_log", []) + [
        "FetchSecondaryPlanNode: Fetching secondary plan details."
    ]
    member_data = state.get("member_data")

    sec_key = (member_data or {}).get("secondary_insurer_key") or "insurer2"
    member_id = (member_data or {}).get("member_id")

    ded_met, oop_met = 0.0, 0.0
    if member_id:
        ded_met, oop_met = MemberService.get_accumulators(member_id, sec_key)

    try:
        plan = load_plan(sec_key, deductible_met=ded_met, oop_met=oop_met)
    except Exception as e:
        plan = load_plan("insurer2")
        log.append(f"FetchSecondaryPlanNode: Fallback to insurer2. Error: {e}")

    log.append(f"FetchSecondaryPlanNode: Secondary plan loaded: {plan.plan_name}")
    return {"secondary_plan": plan, "execution_log": log}


def cob_node(state: AgentState) -> Dict[str, Any]:
    """Perform Coordination of Benefits calculations (no demo error injection)."""
    retry = state.get("retry_count", 0)
    log = state.get("execution_log", []) + [
        f"COBNode: Running COB calculation engine (Attempt {retry})."
    ]

    claim = state["parsed_claim"]
    primary = state["primary_plan"]
    secondary = state["secondary_plan"]

    result = calculate_cob(claim, primary, secondary)

    return {"cob_result": result, "execution_log": log}


def validation_node(state: AgentState) -> Dict[str, Any]:
    """Validate financial correctness of the COB calculations."""
    log = state.get("execution_log", []) + [
        "ValidationNode: Validating financial ledger reconciliation."
    ]
    result = state["cob_result"]
    errors = []

    is_valid = reconcile_ledger(
        total_billed=result.total_amount,
        primary_payment=result.primary_payment,
        secondary_payment=result.secondary_payment,
        patient_responsibility=result.final_patient_responsibility,
        uncovered_amount=result.uncovered_amount,
    )

    if not is_valid:
        calculated_total = (
            result.primary_payment
            + result.secondary_payment
            + result.final_patient_responsibility
            + result.uncovered_amount
        )
        errors.append(
            f"Ledger Mismatch: Primary ({result.primary_payment}) + "
            f"Secondary ({result.secondary_payment}) + "
            f"Patient ({result.final_patient_responsibility}) + "
            f"Uncovered ({result.uncovered_amount}) = {calculated_total}, "
            f"vs Total ({result.total_amount}). "
            f"Discrepancy: {round(calculated_total - result.total_amount, 2)}."
        )

    if (
        result.primary_payment < 0
        or result.secondary_payment < 0
        or result.final_patient_responsibility < 0
    ):
        errors.append("Validation Error: Negative values detected in payments.")

    log.append(f"ValidationNode: Completed validation. {len(errors)} error(s).")
    return {"validation_errors": errors, "execution_log": log}


def reflection_node(state: AgentState) -> Dict[str, Any]:
    """Use Groq LLM to diagnose validation failures."""
    log = state.get("execution_log", []) + [
        "ReflectionNode: Analyzing validation failure with Groq LLM."
    ]
    errors = state.get("validation_errors", [])
    claim = state["parsed_claim"]
    cob = state["cob_result"]

    errors_str = "\n".join(f"- {e}" for e in errors)
    prompt = f"""
You are an expert insurance claim auditor. The COB calculations failed validation.

Claim Details:
- Claim ID: {claim.claim_id}
- Total Billed: ${claim.total_amount}

Calculated Breakdown:
- Primary Payment: ${cob.primary_payment}
- Secondary Payment: ${cob.secondary_payment}
- Uncovered: ${cob.uncovered_amount}
- Patient Responsibility: ${cob.final_patient_responsibility}

Validation Errors:
{errors_str}

Analyze the results, identify the mismatch, and explain clearly.
DO NOT recalculate figures. Explain the issue and declare the engine must be re-run.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a helpful insurance audit assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        notes = response.choices[0].message.content
    except Exception as e:
        notes = f"Reflection error: Groq API call failed: {e}"

    log.append("ReflectionNode: Groq diagnosis generated.")
    return {
        "reflection_notes": notes,
        "retry_count": state.get("retry_count", 0) + 1,
        "validation_errors": [],
        "execution_log": log,
    }


def output_node(state: AgentState) -> Dict[str, Any]:
    """Generate structured JSON output and persist accumulators to Supabase."""
    log = state.get("execution_log", []) + [
        "OutputNode: Claim processing completed successfully."
    ]
    cob = state.get("cob_result")
    claim = state["parsed_claim"]
    primary = state.get("primary_plan")
    secondary = state.get("secondary_plan")
    member_data = state.get("member_data")

    if cob is None:
        # Ineligible — return zero-pay output
        eligibility = state.get("eligibility_status") or {}
        reason = "Claim is ineligible (uncovered or empty CPT codes)."
        if eligibility and not eligibility.get("is_eligible", False):
            reason = f"Claim is ineligible. CPT codes: {claim.cpt_codes or 'None'}."

        return {
            "final_output": {
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
                "explanation": {"general_notes": reason},
                "workflow_log": log,
            },
            "execution_log": log,
        }

    # Persist accumulators to Supabase
    from app.services.cob import update_accumulators

    if primary:
        update_accumulators(primary, cob.primary_deductible_applied, cob.primary_oop_contribution)
    if secondary:
        update_accumulators(secondary, cob.secondary_deductible_applied, cob.secondary_oop_contribution)

    # Write back to Supabase if we have a member
    if member_data and member_data.get("member_id"):
        mid = member_data["member_id"]
        prim_key = member_data.get("primary_insurer_key")
        sec_key = member_data.get("secondary_insurer_key")
        if primary and prim_key:
            MemberService.update_accumulators(mid, prim_key, primary.deductible_met, primary.oop_met)
        if secondary and sec_key:
            MemberService.update_accumulators(mid, sec_key, secondary.deductible_met, secondary.oop_met)

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
        "workflow_log": log,
    }

    return {"final_output": final_output, "execution_log": log}
