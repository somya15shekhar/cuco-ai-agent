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


@router.get("")
def list_households():

    return HouseholdService.list_households()


@router.get("/{household_id}")
def get_household(household_id: str):

    return HouseholdService.get_household(household_id)