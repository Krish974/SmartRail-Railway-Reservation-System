from datetime import datetime, timedelta
from backend.utils.db_connection import execute_query, get_db_type
from backend.config import Config

class SeatModel:
    @staticmethod
    def clean_expired_locks():
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql = "DELETE FROM seat_locks WHERE expires_at <= %s"
        execute_query(sql, (now_str,), commit=True)

    @staticmethod
    def get_coach_seats(coach_id, journey_date=None, session_id=None):
        SeatModel.clean_expired_locks()

        # Fetch coach info
        coach_sql = """
            SELECT c.*, t.train_number, t.train_name, t.departure_time, t.arrival_time 
            FROM coaches c 
            JOIN trains t ON c.train_id = t.id 
            WHERE c.id = %s
        """
        coach = execute_query(coach_sql, (coach_id,), fetchone=True)
        if not coach:
            return None, []

        # Fetch seats
        seats_sql = """
            SELECT id, coach_id, seat_number, seat_type, is_window, is_aisle, deck_or_position
            FROM seats
            WHERE coach_id = %s
            ORDER BY seat_number ASC
        """
        seats = execute_query(seats_sql, (coach_id,), fetchall=True)

        if not journey_date:
            journey_date = datetime.now().strftime('%Y-%m-%d')

        # Find booked seats for this coach & date
        booked_sql = """
            SELECT p.seat_id FROM passengers p
            JOIN bookings b ON p.booking_id = b.id
            WHERE b.coach_id = %s AND b.journey_date = %s AND b.status = 'CONFIRMED' AND p.seat_id IS NOT NULL
        """
        booked_rows = execute_query(booked_sql, (coach_id, journey_date), fetchall=True)
        booked_seat_ids = set(r['seat_id'] for r in booked_rows)

        # Find active locked seats
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lock_sql = """
            SELECT seat_id, session_id, expires_at FROM seat_locks
            WHERE journey_date = %s AND expires_at > %s
        """
        locked_rows = execute_query(lock_sql, (journey_date, now_str), fetchall=True)
        lock_map = {r['seat_id']: r for r in locked_rows}

        enriched_seats = []
        for s in seats:
            seat_id = s['id']
            status = 'available'
            locked_by_current = False
            lock_expires_in = 0

            if seat_id in booked_seat_ids:
                status = 'occupied'
            elif seat_id in lock_map:
                lock_info = lock_map[seat_id]
                if session_id and lock_info['session_id'] == session_id:
                    status = 'selected'
                    locked_by_current = True
                else:
                    status = 'temporarily_locked'
                # calculate remaining seconds
                try:
                    exp_dt = datetime.strptime(str(lock_info['expires_at'])[:19], '%Y-%m-%d %H:%M:%S')
                    lock_expires_in = max(0, int((exp_dt - datetime.now()).total_seconds()))
                except Exception:
                    lock_expires_in = 300

            enriched_seats.append({
                "id": seat_id,
                "coach_id": s['coach_id'],
                "seat_number": s['seat_number'],
                "seat_type": s['seat_type'],
                "is_window": bool(s['is_window']),
                "is_aisle": bool(s['is_aisle']),
                "status": status,
                "locked_by_current": locked_by_current,
                "lock_expires_in": lock_expires_in
            })

        return coach, enriched_seats

    @staticmethod
    def lock_seats(seat_ids, journey_date, session_id, user_id=None, duration_seconds=300):
        SeatModel.clean_expired_locks()
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        expires_at = (now + timedelta(seconds=duration_seconds)).strftime('%Y-%m-%d %H:%M:%S')

        # Check if any seat is already booked
        seat_placeholders = ','.join(['%s'] * len(seat_ids))
        booked_sql = f"""
            SELECT p.seat_id, s.seat_number FROM passengers p
            JOIN bookings b ON p.booking_id = b.id
            JOIN seats s ON p.seat_id = s.id
            WHERE p.seat_id IN ({seat_placeholders}) AND b.journey_date = %s AND b.status = 'CONFIRMED'
        """
        booked = execute_query(booked_sql, (*seat_ids, journey_date), fetchall=True)
        if booked:
            conflict_numbers = [str(r['seat_number']) for r in booked]
            return False, f"Seat(s) {', '.join(conflict_numbers)} are already booked."

        # Check if any seat is locked by someone else
        locked_sql = f"""
            SELECT l.seat_id, s.seat_number FROM seat_locks l
            JOIN seats s ON l.seat_id = s.id
            WHERE l.seat_id IN ({seat_placeholders}) AND l.journey_date = %s AND l.expires_at > %s AND l.session_id != %s
        """
        conflicts = execute_query(locked_sql, (*seat_ids, journey_date, now_str, session_id), fetchall=True)
        if conflicts:
            conflict_numbers = [str(r['seat_number']) for r in conflicts]
            return False, f"Seat(s) {', '.join(conflict_numbers)} are temporarily reserved by another passenger."

        # Clear any existing locks for this session on this date
        execute_query("DELETE FROM seat_locks WHERE session_id = %s AND journey_date = %s", (session_id, journey_date), commit=True)

        # Insert fresh locks
        for sid in seat_ids:
            execute_query("""
                INSERT INTO seat_locks (seat_id, journey_date, user_id, session_id, locked_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (sid, journey_date, user_id, session_id, now_str, expires_at), commit=True)

        return True, {
            "seat_ids": seat_ids,
            "expires_at": expires_at,
            "duration_seconds": duration_seconds
        }

    @staticmethod
    def release_seats(session_id, seat_ids=None):
        if seat_ids:
            placeholders = ','.join(['%s'] * len(seat_ids))
            sql = f"DELETE FROM seat_locks WHERE session_id = %s AND seat_id IN ({placeholders})"
            execute_query(sql, (session_id, *seat_ids), commit=True)
        else:
            sql = "DELETE FROM seat_locks WHERE session_id = %s"
            execute_query(sql, (session_id,), commit=True)
        return True
