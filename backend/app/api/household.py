from fastapi import APIRouter

from app.models.household import HouseholdCreate
from app.services.household_service import HouseholdService

router = APIRouter(
    prefix="/households",
    tags=["Households"]
)


@router.post("")
def create_household(payload: HouseholdCreate):
    return HouseholdService.create_household(payload)


@router.get("/default")
def get_default_household():
    """Return the first household with members + plans (used by dashboard on load)."""
    return HouseholdService.get_default_household()


@router.get("")
def list_households():
    return HouseholdService.list_households()


@router.get("/{household_id}")
def get_household(household_id: str):
    return HouseholdService.get_household(household_id)