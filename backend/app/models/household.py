from pydantic import BaseModel
from typing import List
from typing import Optional


class InsuranceEnrollment(BaseModel):
    insurer_key: str          # insurer1 / insurer2
    role: str                 # primary / dependent


class HouseholdMemberCreate(BaseModel):
    member_name: str
    relationship: str
    insurances: List[InsuranceEnrollment]


class HouseholdCreate(BaseModel):
    household_name: str
    members: List[HouseholdMemberCreate]


class HouseholdResponse(BaseModel):
    id: str
    household_name: str