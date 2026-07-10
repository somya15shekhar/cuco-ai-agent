import os
import json
from typing import Dict, Any, Optional, List
from fastapi import HTTPException

from app.models.claim import InsurancePlan

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# mock_data is located in backend/mock_data relative to backend/app/data_loader.py
MOCK_DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "mock_data")

_cache: Dict[str, Any] = {}

def _load_json_file(filename: str) -> Dict[str, Any]:
    """Reads a JSON file from the mock_data directory and caches it."""
    if filename not in _cache:
        path = os.path.join(MOCK_DATA_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Mock data file not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            _cache[filename] = json.load(f)
    return _cache[filename]

def _resolve_insurer_file(insurer_key: str) -> str:
    """Maps a user-provided insurer name, plan ID, or filename to the correct insurer JSON file."""
    key = insurer_key.lower().strip()
    if key in ["insurer1", "ins1", "plana", "plan_a", "securehealth premier"]:
        return "insurer1.json"
    elif key in ["insurer2", "ins2", "planb", "plan_b", "flexicare plus"]:
        return "insurer2.json"
    raise ValueError(f"Unknown insurer or plan key: {insurer_key}")

def load_plan(insurer: str, member_id: Optional[str] = None) -> InsurancePlan:
    """Loads plan details from the insurer JSON file and dynamically updates member accumulators if member_id is provided."""
    file_name = _resolve_insurer_file(insurer)
    data = _load_json_file(file_name)
    
    # Extract CPT codes covered under the plan
    covered_cpt = []
    for service in data.get("covered_services", []):
        if "cpt_code" in service:
            covered_cpt.append(service["cpt_code"])
        if "cpt_codes" in service:
            covered_cpt.extend(service["cpt_codes"])
            
    # Extract preauth CPT codes
    preauth_cpt = data.get("preauthorization", {}).get("required_for_cpt", [])
    
    # Default plan accumulators
    deductible_met = 0.0
    oop_met = 0.0
    
    # If member_id is provided, load their specific accumulators from members.json
    if member_id:
        try:
            member = load_member(member_id)
            plan_id = "planA" if file_name == "insurer1.json" else "planB"
            for policy in member.get("policies", []):
                if policy.get("plan_id") == plan_id:
                    deductible_met = float(policy.get("deductible_met_ytd_inr", 0))
                    oop_met = float(policy.get("oop_paid_ytd_inr", 0))
                    break
        except Exception:
            pass # Fallback to 0.0 if member lookup fails
            
    return InsurancePlan(
        plan_name=data.get("plan_name", data.get("insurer", "Unknown")),
        deductible=float(data.get("annual_deductible", {}).get("value_inr", 0.0)),
        deductible_met=deductible_met,
        coinsurance_rate=float(data.get("coinsurance", {}).get("value_percent", 0.0)) / 100.0,
        oop_max=float(data.get("out_of_pocket_max", {}).get("value_inr", 0.0)),
        oop_met=oop_met,
        covered_cpt_codes=covered_cpt,
        preauth_required_cpt_codes=preauth_cpt
    )

def load_benefits(insurer: str) -> Dict[str, Any]:
    """Loads covered services / benefits details for a specific insurer."""
    file_name = _resolve_insurer_file(insurer)
    data = _load_json_file(file_name)
    return {
        "insurer": data.get("insurer"),
        "plan_name": data.get("plan_name"),
        "sum_insured": data.get("sum_insured"),
        "covered_services": data.get("covered_services", []),
        "exclusions": data.get("exclusions", [])
    }

def load_coverage_rules(insurer: str) -> Dict[str, Any]:
    """Loads COB calculation/coverage rules for a specific insurer from coverage_rules.json."""
    rules = _load_json_file("coverage_rules.json")
    file_name = _resolve_insurer_file(insurer)
    if file_name == "insurer1.json":
        return rules.get("planA_calculation_rules", {})
    else:
        return rules.get("planB_calculation_rules", {})

def load_preauth_rules(insurer: str) -> Dict[str, Any]:
    """Loads preauthorization guidelines for a specific insurer from preauth_rules.json."""
    rules = _load_json_file("preauth_rules.json")
    file_name = _resolve_insurer_file(insurer)
    if file_name == "insurer1.json":
        return rules.get("planA", {})
    else:
        return rules.get("planB", {})

def load_member(member_id_or_name: str) -> Dict[str, Any]:
    """Looks up a member by member_id or name in members.json."""
    data = _load_json_file("members.json")
    for m in data.get("members", []):
        if m.get("member_id", "").lower() == member_id_or_name.lower() or m.get("name", "").lower() == member_id_or_name.lower():
            return m
    raise HTTPException(status_code=404, detail=f"Member '{member_id_or_name}' not found.")
