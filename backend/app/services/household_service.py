"""
HouseholdService — Supabase-backed household, member, and plan queries.

Returns the enriched shape the frontend expects:
  { household: {...}, members: [...], plans: [...] }
"""

from typing import Dict, Any, List
from app.database import supabase
from app.services.member_service import MemberService
from app.data_loader import load_plan as _load_plan_json


class HouseholdService:

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    @staticmethod
    def create_household(data) -> Dict[str, Any]:
        """Insert household + members + insurance enrolments."""
        household = (
            supabase.table("households")
            .insert({"household_name": data.household_name})
            .execute()
        )
        household_id = household.data[0]["id"]

        for member in data.members:
            member_row = (
                supabase.table("household_members")
                .insert({
                    "household_id": household_id,
                    "member_name": member.member_name,
                    "relationship": member.relationship,
                })
                .execute()
            )
            member_id = member_row.data[0]["id"]

            enrollments = []
            for insurance in member.insurances:
                enrollments.append({
                    "member_id": member_id,
                    "insurer_key": insurance.insurer_key,
                    "role": insurance.role,
                })

            if enrollments:
                supabase.table("member_insurance").insert(enrollments).execute()

        return household.data[0]

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    @staticmethod
    def list_households() -> List[Dict[str, Any]]:
        return (
            supabase.table("households")
            .select("*")
            .execute()
            .data
        )

    # ------------------------------------------------------------------
    # Get — enriched with members + plans (matches frontend shape)
    # ------------------------------------------------------------------

    @staticmethod
    def get_household(household_id: str) -> Dict[str, Any]:
        return HouseholdService._build_enriched_response(
            household_id=household_id
        )

    @staticmethod
    def get_default_household() -> Dict[str, Any]:
        """Return the first available household with full enrichment."""
        rows = (
            supabase.table("households")
            .select("*")
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return {"household": None, "members": [], "plans": []}
        return HouseholdService._build_enriched_response(
            household_row=rows[0]
        )

    # ------------------------------------------------------------------
    # Private helper — builds the enriched response
    # ------------------------------------------------------------------

    @staticmethod
    def _build_enriched_response(
        household_id: str = None, household_row: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        # Resolve household row
        if household_row is None:
            household_row = (
                supabase.table("households")
                .select("*")
                .eq("id", household_id)
                .single()
                .execute()
                .data
            )

        hid = household_row["id"]

        # Fetch members
        raw_members = (
            supabase.table("household_members")
            .select("*")
            .eq("household_id", hid)
            .execute()
            .data or []
        )

        members: List[Dict[str, Any]] = []
        seen_insurer_keys: set = set()
        insurer_accumulators = {}  # maps insurer_key -> (max_ded_met, max_oop_met)

        for m in raw_members:
            mid = m["id"]
            insurances = (
                supabase.table("member_insurance")
                .select("*")
                .eq("member_id", mid)
                .order("created_at")
                .execute()
                .data or []
            )

            primary_name = ""
            secondary_name = ""
            network_status: Dict[str, str] = {}

            if len(insurances) > 0:
                pk = insurances[0]["insurer_key"]
                primary_name = MemberService.resolve_plan_name(pk)
                network_status[primary_name] = insurances[0].get("network_status", "IN")
                seen_insurer_keys.add(pk)
                
                # Accumulate YTD values
                ded_met = float(insurances[0].get("deductible_met_ytd") or 0.0)
                oop_met = float(insurances[0].get("oop_paid_ytd") or 0.0)
                if pk not in insurer_accumulators:
                    insurer_accumulators[pk] = {"ded": 0.0, "oop": 0.0}
                insurer_accumulators[pk]["ded"] = max(insurer_accumulators[pk]["ded"], ded_met)
                insurer_accumulators[pk]["oop"] = max(insurer_accumulators[pk]["oop"], oop_met)

            if len(insurances) > 1:
                sk = insurances[1]["insurer_key"]
                secondary_name = MemberService.resolve_plan_name(sk)
                network_status[secondary_name] = insurances[1].get("network_status", "IN")
                seen_insurer_keys.add(sk)

                # Accumulate YTD values
                ded_met = float(insurances[1].get("deductible_met_ytd") or 0.0)
                oop_met = float(insurances[1].get("oop_paid_ytd") or 0.0)
                if sk not in insurer_accumulators:
                    insurer_accumulators[sk] = {"ded": 0.0, "oop": 0.0}
                insurer_accumulators[sk]["ded"] = max(insurer_accumulators[sk]["ded"], ded_met)
                insurer_accumulators[sk]["oop"] = max(insurer_accumulators[sk]["oop"], oop_met)

            members.append({
                "id": mid,
                "name": m["member_name"],
                "primary": primary_name,
                "secondary": secondary_name,
                "network_status": network_status,
            })

        # Build plan summary cards from JSON config
        plans: List[Dict[str, Any]] = []
        for insurer_key in sorted(seen_insurer_keys):
            try:
                acc = insurer_accumulators.get(insurer_key, {"ded": 0.0, "oop": 0.0})
                plan = _load_plan_json(insurer_key, deductible_met=acc["ded"], oop_met=acc["oop"])
                coins_pct = int(plan.coinsurance_rate * 100)
                plans.append({
                    "name": plan.plan_name,
                    "deductible": f"₹{plan.deductible:,.0f}",
                    "coinsurance": f"{coins_pct}/{100 - coins_pct}",
                    "oop_remaining": f"₹{max(0.0, plan.oop_max - plan.oop_met):,.0f}",
                })
            except Exception:
                pass

        # Derive household relationship label
        rels = [m.get("relationship", "") for m in raw_members]
        has_spouse = any("spouse" in r.lower() for r in rels)
        rel_label = "Married Household" if has_spouse else "Family Household"

        return {
            "household": {
                "id": hid,
                "name": household_row["household_name"],
                "relationship": rel_label,
            },
            "members": members,
            "plans": plans,
        }