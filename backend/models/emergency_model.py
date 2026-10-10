from backend.utils.db_connection import execute_query
from backend.utils.helpers import generate_incident_id

class EmergencyModel:
    @staticmethod
    def create_incident(emergency_type, train_number, coach, seat, description, user_name="Anonymous Passenger", user_phone="139-RPF", user_id=None):
        incident_id = generate_incident_id()
        response_note = f"Alert received by RailMadad/RPF Control Room. Immediate dispatch protocol initiated for Train {train_number} Coach {coach} Seat {seat}."

        sql = """
            INSERT INTO emergency_logs (
                incident_id, user_id, user_name, user_phone, emergency_type,
                train_number, coach, seat, description, status, response_note
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'DISPATCHED', %s)
        """
        execute_query(sql, (
            incident_id, user_id, user_name, user_phone, emergency_type,
            train_number, coach, seat, description, response_note
        ), commit=True)

        return EmergencyModel.get_by_incident_id(incident_id)

    @staticmethod
    def get_by_incident_id(incident_id):
        sql = "SELECT * FROM emergency_logs WHERE incident_id = %s"
        return execute_query(sql, (incident_id,), fetchone=True)

    @staticmethod
    def get_all(limit=50):
        sql = "SELECT * FROM emergency_logs ORDER BY id DESC LIMIT %s"
        return execute_query(sql, (limit,), fetchall=True)

    @staticmethod
    def update_status(incident_id, status, response_note=None):
        if response_note:
            sql = "UPDATE emergency_logs SET status = %s, response_note = %s WHERE incident_id = %s"
            execute_query(sql, (status, response_note, incident_id), commit=True)
        else:
            sql = "UPDATE emergency_logs SET status = %s WHERE incident_id = %s"
            execute_query(sql, (status, incident_id), commit=True)
        return EmergencyModel.get_by_incident_id(incident_id)
