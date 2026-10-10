from datetime import datetime
import random
from backend.utils.db_connection import execute_query

CLEANING_ISSUES = [
    "Coach floor dirty",
    "Washroom / Toilet unhygienic",
    "Dustbin full / overflowing",
    "Seat / Berth stained or dirty",
    "Bad odor / smell in coach",
    "Spilled liquid / food waste",
    "Other cleaning request"
]

CLEANING_STATUSES = [
    "PENDING",
    "ASSIGNED",
    "CLEANING IN PROGRESS",
    "RESOLVED",
    "CANCELLED"
]

def generate_cleaning_id():
    """
    Generates a unique Cleaning Request ID: CLR-YYYYMMDD-XXX
    """
    date_str = datetime.now().strftime("%Y%m%d")
    for _ in range(10):
        rand_suffix = f"{random.randint(100, 999)}"
        cid = f"CLR-{date_str}-{rand_suffix}"
        existing = execute_query("SELECT id FROM cleaning_requests WHERE request_id = %s", (cid,), fetchone=True)
        if not existing:
            return cid
    # Fallback with milliseconds if needed
    ms_suffix = datetime.now().strftime("%f")[:3]
    return f"CLR-{date_str}-{ms_suffix}"

class CleaningModel:
    @staticmethod
    def create_request(train_number, coach_number, seat_number, issue_type, passenger_name, contact_mobile, description=None, user_id=None):
        request_id = generate_cleaning_id()
        sql = """
            INSERT INTO cleaning_requests (
                request_id, user_id, passenger_name, contact_mobile,
                train_number, coach_number, seat_number, issue_type,
                description, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
        """
        execute_query(sql, (
            request_id, user_id, passenger_name, contact_mobile,
            str(train_number).strip(), str(coach_number).strip().upper(),
            str(seat_number).strip() if seat_number else None,
            issue_type, description or "",
        ), commit=True)

        return CleaningModel.get_by_request_id(request_id)

    @staticmethod
    def get_by_request_id(request_id):
        sql = "SELECT * FROM cleaning_requests WHERE request_id = %s"
        return execute_query(sql, (request_id,), fetchone=True)

    @staticmethod
    def get_all(limit=50):
        sql = "SELECT * FROM cleaning_requests ORDER BY id DESC LIMIT %s"
        return execute_query(sql, (limit,), fetchall=True)

    @staticmethod
    def update_status(request_id, status):
        status_clean = str(status).strip().upper()
        if status_clean not in [s.upper() for s in CLEANING_STATUSES]:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(CLEANING_STATUSES)}")

        # SQLite/MySQL compatible update
        sql = "UPDATE cleaning_requests SET status = %s WHERE request_id = %s"
        execute_query(sql, (status_clean, request_id), commit=True)
        return CleaningModel.get_by_request_id(request_id)
