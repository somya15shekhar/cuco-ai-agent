"""
MemberService — the single source of truth for member data.

Reads from Supabase tables: household_members, member_insurance.
Insurance plan *rules* still come from JSON config via data_loader.
"""

from typing import Dict, Any, List, Optional, Tuple
from app.database import supabase
from app.data_loader import load_plan as _load_plan_json


class MemberService:

    # ------------------------------------------------------------------
    # Core lookups
    # ------------------------------------------------------------------

    @staticmethod
    def get_member(member_id: str) -> Dict[str, Any]:
        """Fetch a household member by ID."""
        result = (
            supabase.table("household_members")
            .select("*")
            .eq("id", member_id)
            .single()
            .execute()
        )
        return result.data

    @staticmethod
    def get_member_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Lookup a member by name (fallback for legacy/OCR compatibility)."""
        result = (
            supabase.table("household_members")
            .select("*")
            .ilike("member_name", name)
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    def get_member_insurance(member_id: str) -> List[Dict[str, Any]]:
        """All insurance enrollments for a member, ordered by creation."""
        result = (
            supabase.table("member_insurance")
            .select("*")
            .eq("member_id", member_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    @staticmethod
    def get_member_with_insurance(member_id: str) -> Dict[str, Any]:
        """Member row + insurance list combined."""
        member = MemberService.get_member(member_id)
        member["insurances"] = MemberService.get_member_insurance(member_id)
        return member

    # ------------------------------------------------------------------
    # Insurer resolution
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_plan_name(insurer_key: str) -> str:
        """Map insurer_key (e.g. 'insurer1') → human name from JSON config."""
        try:
            plan = _load_plan_json(insurer_key)
            return plan.plan_name
        except Exception:
            return insurer_key

    @staticmethod
    def get_primary_secondary_keys(member_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Return (primary_insurer_key, secondary_insurer_key).

        Convention: first enrollment = primary for claims, second = secondary.
        """
        ins = MemberService.get_member_insurance(member_id)
        prim = ins[0]["insurer_key"] if len(ins) > 0 else None
        sec = ins[1]["insurer_key"] if len(ins) > 1 else None
        return prim, sec

    # ------------------------------------------------------------------
    # Accumulators
    # ------------------------------------------------------------------

    @staticmethod
    def get_accumulators(member_id: str, insurer_key: str) -> Tuple[float, float]:
        """Return (deductible_met_ytd, oop_paid_ytd) for a member + insurer."""
        for ins in MemberService.get_member_insurance(member_id):
            if ins.get("insurer_key") == insurer_key:
                return (
                    float(ins.get("deductible_met_ytd", 0) or 0),
                    float(ins.get("oop_paid_ytd", 0) or 0),
                )
        return 0.0, 0.0

    @staticmethod
    def update_accumulators(
        member_id: str,
        insurer_key: str,
        deductible_met: float,
        oop_met: float,
    ) -> None:
        """Persist updated YTD accumulators back to Supabase."""
        try:
            (
                supabase.table("member_insurance")
                .update({
                    "deductible_met_ytd": round(deductible_met, 2),
                    "oop_paid_ytd": round(oop_met, 2),
                })
                .eq("member_id", member_id)
                .eq("insurer_key", insurer_key)
                .execute()
            )
        except Exception:
            pass  # Graceful if columns don't exist yet

    # ------------------------------------------------------------------
    # Network status
    # ------------------------------------------------------------------

    @staticmethod
    def get_network_status(member_id: str) -> Dict[str, str]:
        """Build {plan_name: 'IN'/'OUT'} dict for a member."""
        status: Dict[str, str] = {}
        for ins in MemberService.get_member_insurance(member_id):
            plan_name = MemberService.resolve_plan_name(ins["insurer_key"])
            status[plan_name] = ins.get("network_status", "IN")
        return status
