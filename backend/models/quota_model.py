from backend.utils.db_connection import execute_query

class QuotaModel:
    @staticmethod
    def get_all():
        sql = "SELECT id, code, name, discount_or_premium_pct, description FROM quotas ORDER BY id ASC"
        return execute_query(sql, fetchall=True)

    @staticmethod
    def get_by_code(code):
        sql = "SELECT id, code, name, discount_or_premium_pct, description FROM quotas WHERE code = %s"
        return execute_query(sql, (code.upper(),), fetchone=True)

    @staticmethod
    def validate_eligibility(quota_code, passengers):
        """
        Validates passenger details against specific quota constraints.
        passengers: list of dicts with keys: name, age, gender, id_type, id_number
        """
        code = (quota_code or 'GN').upper()

        if code == 'GN':
            return True, "Eligible for General Quota."

        if not passengers or len(passengers) == 0:
            return False, "At least one passenger must be provided."

        if code == 'LD':  # Ladies Quota
            for p in passengers:
                gender = str(p.get('gender', '')).strip().lower()
                age = int(p.get('age', 0))
                if gender != 'female' and age >= 12:
                    return False, f"Passenger {p.get('name', 'Unknown')} is not eligible. Ladies quota is reserved for females and children under 12."
            return True, "Eligible for Ladies Quota."

        if code == 'SS':  # Senior Citizen Quota
            for p in passengers:
                gender = str(p.get('gender', '')).strip().lower()
                age = int(p.get('age', 0))
                if gender == 'male' and age < 60:
                    return False, f"Male passenger {p.get('name', 'Unknown')} must be at least 60 years old for Senior Citizen quota (current: {age})."
                elif gender == 'female' and age < 58:
                    return False, f"Female passenger {p.get('name', 'Unknown')} must be at least 58 years old for Senior Citizen quota (current: {age})."
                elif gender not in ('male', 'female') and age < 60:
                    return False, f"Passenger {p.get('name', 'Unknown')} must be at least 60 years old."
            return True, "Eligible for Senior Citizen Concession Quota."

        if code in ('TQ', 'PT'):  # Tatkal & Premium Tatkal
            if len(passengers) > 4:
                return False, "Tatkal and Premium Tatkal bookings are limited to a maximum of 4 passengers per booking."
            for p in passengers:
                if not p.get('id_number') or not p.get('id_type'):
                    return False, f"Government photo ID is mandatory for all Tatkal passengers ({p.get('name')})."
            return True, "Eligible for Tatkal Quota."

        if code == 'HP':  # Divyang
            for p in passengers:
                id_type = str(p.get('id_type', '')).lower()
                if 'disability' not in id_type and 'divyang' not in id_type and 'udid' not in id_type:
                    return False, f"A valid Divyangjan / UDID Unique Disability Card is required for passenger {p.get('name')}."
            return True, "Eligible for Divyang Quota."

        return True, "Quota verified."
