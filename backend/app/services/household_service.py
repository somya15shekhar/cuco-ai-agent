from app.database import supabase


class HouseholdService:

    @staticmethod
    def create_household(data):

        household = (
            supabase.table("households")
            .insert({
                "household_name": data.household_name
            })
            .execute()
        )

        household_id = household.data[0]["id"]

        for member in data.members:

            member_row = (
                supabase.table("household_members")
                .insert({
                    "household_id": household_id,
                    "member_name": member.member_name,
                    "relationship": member.relationship
                })
                .execute()
            )

            member_id = member_row.data[0]["id"]

            enrollments = []

            for insurance in member.insurances:

                enrollments.append({

                    "member_id": member_id,

                    "insurer_key": insurance.insurer_key,

                    "role": insurance.role

                })

            supabase.table("member_insurance")\
                .insert(enrollments)\
                .execute()

        return household.data[0]

    @staticmethod
    def list_households():

        return supabase.table("households")\
            .select("*")\
            .execute()\
            .data

    @staticmethod
    def get_household(household_id):

        household = supabase.table("households")\
            .select("*")\
            .eq("id", household_id)\
            .single()\
            .execute()

        return household.data