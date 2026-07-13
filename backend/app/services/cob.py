from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.models.claim import ParsedClaim, InsurancePlan, COBResult
from app.data_loader import load_coverage_rules


# ---------------------------------------------------------------------------
# CPT-level result models
# ---------------------------------------------------------------------------

class PrimaryCPTResult(BaseModel):
    """Per-CPT adjudication result from the primary insurer."""
    cpt_code: str
    billed: float
    sub_limit: Optional[float]        # None if no sub-limit applies
    allowed: float                     # billed capped by sub-limit
    uncovered_by_sub_limit: float      # billed - allowed
    deductible_applied: float
    coinsurance_patient: float
    copay_patient: float
    insurer_payment: float
    patient_liability: float           # what patient owes for covered portion

class PrimaryResult(BaseModel):
    """Aggregate primary adjudication result."""
    total_billed: float
    allowed_amount: float
    uncovered_by_sub_limit: float
    deductible_applied: float
    coinsurance_patient: float
    copay_patient: float
    insurer_payment: float
    patient_liability: float
    cpt_details: List[PrimaryCPTResult]

class SecondaryCPTResult(BaseModel):
    """Per-CPT adjudication result from the secondary insurer."""
    cpt_code: str
    residual_from_primary: float       # patient_liability from primary
    sub_limit: Optional[float]         # None if no sub-limit applies
    allowed_residual: float            # residual capped by secondary sub-limit
    uncovered_by_sub_limit: float      # residual - allowed_residual
    deductible_applied: float
    coinsurance_patient: float
    copay_patient: float
    insurer_payment: float
    patient_liability: float           # what patient still owes after secondary

class SecondaryResult(BaseModel):
    """Aggregate secondary adjudication result."""
    total_residual: float
    allowed_residual: float
    uncovered_by_sub_limit: float
    deductible_applied: float
    coinsurance_patient: float
    copay_patient: float
    insurer_payment: float
    patient_liability: float
    cpt_details: List[SecondaryCPTResult]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_network_status(claim: ParsedClaim, plan_name: str) -> str:
    """Retrieve structured network status for a given plan from the claim."""
    if claim.network_status:
        for k, v in claim.network_status.items():
            if k.lower().strip() == plan_name.lower().strip():
                return v.upper().strip()
    return "IN"


def _load_plan_parameters(rules: Dict[str, Any], network_status: str) -> Dict[str, Any]:
    """Extract deductible, coinsurance, copay, OOP max, and PT sub-limit from coverage rules."""
    ded_amt = float(rules.get("step1_deductible", {}).get("amount_inr", 0.0))
    ded_type = rules.get("step1_deductible", {}).get("type", "aggregate_annual")
    coins_rate = float(rules.get("step2_coinsurance", {}).get("insurer_pays_percent", 0.0)) / 100.0
    oop_max = float(rules.get("step3_oop_max_check", {}).get("oop_max_inr",
                       rules.get("step4_oop_max_check", {}).get("oop_max_inr", 0.0)))

    pt_limit = rules.get("pt_sub_limit", {})
    pt_cpts = pt_limit.get("applies_to_cpt", [])
    pt_cap = float(pt_limit.get("sub_limit_inr", 999999.0))

    copay_rate = 0.0
    if network_status == "OUT":
        copay_rate = float(rules.get("step3_copay_non_network", {}).get("copay_percent",
                            rules.get("step4_copay_non_network", {}).get("copay_percent", 0.0))) / 100.0

    return {
        "ded_amt": ded_amt,
        "ded_type": ded_type,
        "coins_rate": coins_rate,
        "oop_max": oop_max,
        "pt_cpts": pt_cpts,
        "pt_cap": pt_cap,
        "copay_rate": copay_rate,
    }


# ---------------------------------------------------------------------------
# Primary adjudication
# ---------------------------------------------------------------------------

def adjudicate_primary(claim: ParsedClaim, plan: InsurancePlan, network_status: str) -> PrimaryResult:
    """Process the primary insurer's adjudication independently per CPT code."""
    params = _load_plan_parameters(load_coverage_rules(plan.plan_name), network_status)

    # Distribute total billed across CPTs
    if claim.billed_amounts:
        cpt_amounts = list(claim.billed_amounts.items())
    elif claim.cpt_codes:
        avg = claim.total_amount / len(claim.cpt_codes)
        cpt_amounts = [(c, avg) for c in claim.cpt_codes]
    else:
        cpt_amounts = [("UNKNOWN", claim.total_amount)]

    # Initialise running accumulators
    accumulated_pt = 0.0
    if params["ded_type"] == "per_claim":
        remaining_ded = params["ded_amt"]
    else:
        remaining_ded = max(0.0, params["ded_amt"] - plan.deductible_met)
    current_oop = plan.oop_met

    cpt_details: List[PrimaryCPTResult] = []
    totals = dict(billed=0.0, allowed=0.0, uncov_sub=0.0, ded=0.0, coins=0.0,
                  copay=0.0, paid=0.0, pat=0.0)

    for cpt_code, billed in cpt_amounts:
        is_covered = cpt_code in plan.covered_cpt_codes
        if not is_covered:
            cpt_details.append(PrimaryCPTResult(
                cpt_code=cpt_code, billed=billed, sub_limit=None,
                allowed=0.0, uncovered_by_sub_limit=billed,
                deductible_applied=0.0, coinsurance_patient=0.0,
                copay_patient=0.0, insurer_payment=0.0,
                patient_liability=billed))
            totals["billed"] += billed
            totals["pat"] += billed       # entire amount falls on patient as not-covered
            totals["uncov_sub"] += billed
            continue

        # --- Sub-limit ---
        is_pt = cpt_code in params["pt_cpts"]
        if is_pt:
            cap_remaining = max(0.0, params["pt_cap"] - accumulated_pt)
            allowed = min(billed, cap_remaining)
            accumulated_pt += allowed
            sub_limit_val = params["pt_cap"]
        else:
            allowed = billed
            sub_limit_val = None
        uncov_sub = billed - allowed

        # --- Deductible ---
        ded_applied = min(allowed, remaining_ded)
        remaining_ded -= ded_applied

        # --- Coinsurance & Copay ---
        after_ded = allowed - ded_applied
        coins_patient = after_ded * (1.0 - params["coins_rate"])
        copay_patient = after_ded * params["coins_rate"] * params["copay_rate"]
        insurer_pay = after_ded - coins_patient - copay_patient
        pat_share = ded_applied + coins_patient + copay_patient

        # --- OOP max cap ---
        oop_space = max(0.0, params["oop_max"] - current_oop)
        if pat_share > oop_space:
            excess = pat_share - oop_space
            insurer_pay += excess
            # Re-apportion patient components under the cap
            tmp = oop_space
            ded_applied_r = min(ded_applied, tmp); tmp -= ded_applied_r
            coins_patient_r = min(coins_patient, tmp); tmp -= coins_patient_r
            copay_patient_r = min(copay_patient, tmp)
            pat_share = oop_space
            current_oop = params["oop_max"]
        else:
            ded_applied_r = ded_applied
            coins_patient_r = coins_patient
            copay_patient_r = copay_patient
            current_oop += pat_share

        # Patient liability for this CPT = covered patient share + sub-limit excess
        patient_liability = pat_share + uncov_sub

        cpt_details.append(PrimaryCPTResult(
            cpt_code=cpt_code, billed=billed, sub_limit=sub_limit_val,
            allowed=allowed, uncovered_by_sub_limit=uncov_sub,
            deductible_applied=ded_applied_r, coinsurance_patient=coins_patient_r,
            copay_patient=copay_patient_r, insurer_payment=insurer_pay,
            patient_liability=patient_liability))

        totals["billed"] += billed
        totals["allowed"] += allowed
        totals["uncov_sub"] += uncov_sub
        totals["ded"] += ded_applied_r
        totals["coins"] += coins_patient_r
        totals["copay"] += copay_patient_r
        totals["paid"] += insurer_pay
        totals["pat"] += patient_liability

    return PrimaryResult(
        total_billed=claim.total_amount,
        allowed_amount=totals["allowed"],
        uncovered_by_sub_limit=totals["uncov_sub"],
        deductible_applied=totals["ded"],
        coinsurance_patient=totals["coins"],
        copay_patient=totals["copay"],
        insurer_payment=totals["paid"],
        patient_liability=totals["pat"],
        cpt_details=cpt_details)


# ---------------------------------------------------------------------------
# Secondary adjudication
# ---------------------------------------------------------------------------

def calculate_secondary_liability(
    primary_result: PrimaryResult,
    secondary_plan: InsurancePlan,
    network_status: str
) -> SecondaryResult:
    """Adjudicate secondary insurer against the residual patient liability from primary."""
    params = _load_plan_parameters(load_coverage_rules(secondary_plan.plan_name), network_status)

    accumulated_pt_sec = 0.0
    if params["ded_type"] == "per_claim":
        remaining_ded = params["ded_amt"]
    else:
        remaining_ded = max(0.0, params["ded_amt"] - secondary_plan.deductible_met)
    current_oop = secondary_plan.oop_met

    cpt_details: List[SecondaryCPTResult] = []
    totals = dict(residual=0.0, allowed=0.0, uncov_sub=0.0, ded=0.0, coins=0.0,
                  copay=0.0, paid=0.0, pat=0.0)

    for prim_cpt in primary_result.cpt_details:
        cpt_code = prim_cpt.cpt_code
        residual = prim_cpt.patient_liability

        is_covered = cpt_code in secondary_plan.covered_cpt_codes
        if not is_covered:
            cpt_details.append(SecondaryCPTResult(
                cpt_code=cpt_code, residual_from_primary=residual,
                sub_limit=None, allowed_residual=0.0,
                uncovered_by_sub_limit=residual,
                deductible_applied=0.0, coinsurance_patient=0.0,
                copay_patient=0.0, insurer_payment=0.0,
                patient_liability=residual))
            totals["residual"] += residual
            totals["pat"] += residual
            totals["uncov_sub"] += residual
            continue

        # --- Sub-limit on residual ---
        is_pt = cpt_code in params["pt_cpts"]
        if is_pt:
            cap_remaining = max(0.0, params["pt_cap"] - accumulated_pt_sec)
            allowed_res = min(residual, cap_remaining)
            accumulated_pt_sec += allowed_res
            sub_limit_val = params["pt_cap"]
        else:
            allowed_res = residual
            sub_limit_val = None
        uncov_sub = residual - allowed_res

        # --- Deductible ---
        ded_applied = min(allowed_res, remaining_ded)
        remaining_ded -= ded_applied

        # --- Coinsurance & Copay ---
        after_ded = allowed_res - ded_applied
        coins_patient = after_ded * (1.0 - params["coins_rate"])
        copay_patient = after_ded * params["coins_rate"] * params["copay_rate"]
        insurer_pay = after_ded - coins_patient - copay_patient
        pat_share = ded_applied + coins_patient + copay_patient

        # --- OOP max cap ---
        oop_space = max(0.0, params["oop_max"] - current_oop)
        if pat_share > oop_space:
            excess = pat_share - oop_space
            insurer_pay += excess
            tmp = oop_space
            ded_applied_r = min(ded_applied, tmp); tmp -= ded_applied_r
            coins_patient_r = min(coins_patient, tmp); tmp -= coins_patient_r
            copay_patient_r = min(copay_patient, tmp)
            pat_share = oop_space
            current_oop = params["oop_max"]
        else:
            ded_applied_r = ded_applied
            coins_patient_r = coins_patient
            copay_patient_r = copay_patient
            current_oop += pat_share

        # Patient liability = covered patient share + sub-limit exclusion
        patient_liability = pat_share + uncov_sub

        cpt_details.append(SecondaryCPTResult(
            cpt_code=cpt_code, residual_from_primary=residual,
            sub_limit=sub_limit_val, allowed_residual=allowed_res,
            uncovered_by_sub_limit=uncov_sub,
            deductible_applied=ded_applied_r, coinsurance_patient=coins_patient_r,
            copay_patient=copay_patient_r, insurer_payment=insurer_pay,
            patient_liability=patient_liability))

        totals["residual"] += residual
        totals["allowed"] += allowed_res
        totals["uncov_sub"] += uncov_sub
        totals["ded"] += ded_applied_r
        totals["coins"] += coins_patient_r
        totals["copay"] += copay_patient_r
        totals["paid"] += insurer_pay
        totals["pat"] += patient_liability

    return SecondaryResult(
        total_residual=totals["residual"],
        allowed_residual=totals["allowed"],
        uncovered_by_sub_limit=totals["uncov_sub"],
        deductible_applied=totals["ded"],
        coinsurance_patient=totals["coins"],
        copay_patient=totals["copay"],
        insurer_payment=totals["paid"],
        patient_liability=totals["pat"],
        cpt_details=cpt_details)


# ---------------------------------------------------------------------------
# Accumulator update (post-adjudication)
# ---------------------------------------------------------------------------

def update_accumulators(plan: InsurancePlan, deductible_applied: float, oop_increment: float) -> None:
    """Update plan YTD accumulators in-memory after payment calculations are finalised."""
    plan.deductible_met += deductible_applied
    plan.oop_met = min(plan.oop_max, plan.oop_met + oop_increment)


# ---------------------------------------------------------------------------
# Ledger reconciliation
# ---------------------------------------------------------------------------

def reconcile_ledger(
    total_billed: float,
    primary_payment: float,
    secondary_payment: float,
    patient_responsibility: float,
    uncovered_amount: float
) -> bool:
    """Verify: primary_paid + secondary_paid + patient_responsibility + uncovered == total_billed."""
    calculated = primary_payment + secondary_payment + patient_responsibility + uncovered_amount
    return abs(calculated - total_billed) <= 0.01


# ---------------------------------------------------------------------------
# Explanation builder
# ---------------------------------------------------------------------------

def _build_explanation(
    primary_res: PrimaryResult,
    secondary_res: SecondaryResult,
    final_patient_responsibility: float,
    total_uncovered: float,
) -> Dict[str, Any]:
    """Build a detailed, internally-consistent explanation object."""

    # Primary per-CPT breakdown
    prim_cpt_details = []
    for c in primary_res.cpt_details:
        detail: Dict[str, Any] = {"cpt_code": c.cpt_code, "billed": round(c.billed, 2)}
        if c.sub_limit is not None:
            detail["sub_limit"] = round(c.sub_limit, 2)
        detail.update({
            "allowed": round(c.allowed, 2),
            "uncovered_by_sub_limit": round(c.uncovered_by_sub_limit, 2),
            "deductible": round(c.deductible_applied, 2),
            "coinsurance": round(c.coinsurance_patient, 2),
            "copay": round(c.copay_patient, 2),
            "insurer_payment": round(c.insurer_payment, 2),
            "patient_liability": round(c.patient_liability, 2),
        })
        prim_cpt_details.append(detail)

    # Secondary per-CPT breakdown
    sec_cpt_details = []
    for c in secondary_res.cpt_details:
        detail: Dict[str, Any] = {"cpt_code": c.cpt_code, "residual_from_primary": round(c.residual_from_primary, 2)}
        if c.sub_limit is not None:
            detail["sub_limit"] = round(c.sub_limit, 2)
        detail.update({
            "allowed_residual": round(c.allowed_residual, 2),
            "uncovered_by_sub_limit": round(c.uncovered_by_sub_limit, 2),
            "deductible": round(c.deductible_applied, 2),
            "coinsurance": round(c.coinsurance_patient, 2),
            "copay": round(c.copay_patient, 2),
            "insurer_payment": round(c.insurer_payment, 2),
            "patient_liability": round(c.patient_liability, 2),
        })
        sec_cpt_details.append(detail)

    return {
        "primary": {
            "total_billed": round(primary_res.total_billed, 2),
            "allowed": round(primary_res.allowed_amount, 2),
            "uncovered_by_sub_limit": round(primary_res.uncovered_by_sub_limit, 2),
            "deductible": round(primary_res.deductible_applied, 2),
            "coinsurance": round(primary_res.coinsurance_patient, 2),
            "copay": round(primary_res.copay_patient, 2),
            "paid": round(primary_res.insurer_payment, 2),
            "patient_liability": round(primary_res.patient_liability, 2),
            "cpt_breakdown": prim_cpt_details,
        },
        "secondary": {
            "residual_from_primary": round(secondary_res.total_residual, 2),
            "allowed_residual": round(secondary_res.allowed_residual, 2),
            "uncovered_by_sub_limit": round(secondary_res.uncovered_by_sub_limit, 2),
            "deductible": round(secondary_res.deductible_applied, 2),
            "coinsurance": round(secondary_res.coinsurance_patient, 2),
            "copay": round(secondary_res.copay_patient, 2),
            "paid": round(secondary_res.insurer_payment, 2),
            "patient_liability": round(secondary_res.patient_liability, 2),
            "cpt_breakdown": sec_cpt_details,
        },
        "patient": {
            "final_responsibility": round(final_patient_responsibility, 2),
            "patient_liability_covered": round(final_patient_responsibility, 2),
            "uncovered_amount": round(total_uncovered, 2),
            "total_patient_cost": round(final_patient_responsibility + total_uncovered, 2),
        },
        "ledger": {
            "total_billed": round(primary_res.total_billed, 2),
            "primary_paid": round(primary_res.insurer_payment, 2),
            "secondary_paid": round(secondary_res.insurer_payment, 2),
            "patient_responsibility": round(final_patient_responsibility, 2),
            "uncovered": round(total_uncovered, 2),
        },
    }


# ---------------------------------------------------------------------------
# Main COB orchestrator
# ---------------------------------------------------------------------------

def calculate_cob(claim: ParsedClaim, primary_plan: InsurancePlan, secondary_plan: InsurancePlan) -> COBResult:
    """Adjudicate a claim through primary and secondary insurance, verify the ledger, return COBResult."""

    # 1. Resolve structured network status
    net_p = get_network_status(claim, primary_plan.plan_name)
    net_s = get_network_status(claim, secondary_plan.plan_name)

    # 2. Adjudicate primary
    primary_res = adjudicate_primary(claim, primary_plan, net_p)

    # 3. Adjudicate secondary
    secondary_res = calculate_secondary_liability(primary_res, secondary_plan, net_s)

    # 4. Derive final totals
    #    final_patient_responsibility = what patient still owes after BOTH insurers for covered services
    #    This is the sum of deductible, coinsurance, and copay applied by the secondary plan.
    final_patient_responsibility = (secondary_res.deductible_applied + 
                                    secondary_res.coinsurance_patient + 
                                    secondary_res.copay_patient)

    #    uncovered_amount = True uncovered amount after BOTH layers
    #    This is the remaining uncovered amount after the secondary insurer adjudicates the residual.
    total_uncovered = secondary_res.uncovered_by_sub_limit

    # 5. OOP contribution (YTD accumulator increments — computed but NOT applied to plans here)
    oop_inc_p = primary_res.deductible_applied + primary_res.coinsurance_patient + primary_res.copay_patient
    oop_inc_s = secondary_res.deductible_applied + secondary_res.coinsurance_patient + secondary_res.copay_patient

    # 6. Verify ledger
    is_valid = reconcile_ledger(
        total_billed=claim.total_amount,
        primary_payment=primary_res.insurer_payment,
        secondary_payment=secondary_res.insurer_payment,
        patient_responsibility=final_patient_responsibility,
        uncovered_amount=total_uncovered)

    validation_message = None
    if not is_valid:
        calc = (primary_res.insurer_payment + secondary_res.insurer_payment
                + final_patient_responsibility + total_uncovered)
        validation_message = (
            f"Ledger reconciliation failed. Total billed: {claim.total_amount}, "
            f"Calculated total: {calc}")

    # 7. Build explanation
    explanation = _build_explanation(primary_res, secondary_res,
                                     final_patient_responsibility, total_uncovered)

    return COBResult(
        claim_id=claim.claim_id,
        total_amount=round(claim.total_amount, 2),
        covered_amount=round(primary_res.allowed_amount + secondary_res.allowed_residual, 2),
        uncovered_amount=round(total_uncovered, 2),
        primary_deductible_applied=round(primary_res.deductible_applied, 2),
        primary_coinsurance_patient=round(primary_res.coinsurance_patient, 2),
        primary_oop_contribution=round(oop_inc_p, 2),
        primary_payment=round(primary_res.insurer_payment, 2),
        patient_responsibility_after_primary=round(primary_res.patient_liability, 2),
        secondary_deductible_applied=round(secondary_res.deductible_applied, 2),
        secondary_coinsurance_patient=round(secondary_res.coinsurance_patient, 2),
        secondary_oop_contribution=round(oop_inc_s, 2),
        secondary_payment=round(secondary_res.insurer_payment, 2),
        final_patient_responsibility=round(final_patient_responsibility, 2),
        patient_liability_covered=round(final_patient_responsibility, 2),
        total_patient_cost=round(final_patient_responsibility + total_uncovered, 2),
        is_valid=is_valid,
        validation_message=validation_message,
        explanation=explanation)
