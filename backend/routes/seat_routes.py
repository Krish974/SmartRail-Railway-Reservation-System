from datetime import datetime
from flask import Blueprint, request, session
from backend.models.seat_model import SeatModel
from backend.ml.seat_recommender import recommend_seats
from backend.utils.helpers import api_response
from backend.utils.db_connection import execute_query
from backend.config import Config

seat_bp = Blueprint('seat_bp', __name__)

@seat_bp.route('/trains/<int:train_id>/coaches', methods=['GET'])
def get_train_coaches(train_id):
    """
    Retrieves the complete valid coach rake composition for a train.
    Supports filtering by class and includes real-time seat availability for journey date & quota.
    """
    from backend.services.railway_service import RailwayService
    class_code = request.args.get('class')
    journey_date = request.args.get('date')
    quota = request.args.get('quota', 'GN')
    from_term = request.args.get('from')
    to_term = request.args.get('to')
    distance_km = request.args.get('distance_km')

    try:
        RailwayService.ensure_train_coaches(train_id)
        composition = RailwayService.get_train_coach_composition(
            train_id,
            class_type=class_code,
            date=journey_date,
            quota=quota,
            distance_km=distance_km,
            from_term=from_term,
            to_term=to_term
        )
        if not composition:
            return api_response(False, "Train not found.", None, 404)

        return api_response(True, "Train coach composition retrieved successfully.", composition)
    except Exception as e:
        return api_response(False, f"Failed to retrieve train coach composition: {str(e)}", None, 500)

@seat_bp.route('/trains/<int:train_id>/seats', methods=['GET'])
@seat_bp.route('/coaches/<int:coach_id>/seats', methods=['GET'])
def get_seats(train_id=None, coach_id=None):
    c_id = coach_id or request.args.get('coach_id')
    journey_date = request.args.get('date')
    session_id = request.args.get('session_id') or session.get('session_id')

    if not c_id:
        return api_response(False, "coach_id is required.", None, 400)

    try:
        coach, seats = SeatModel.get_coach_seats(int(c_id), journey_date, session_id)
        if not coach:
            return api_response(False, "Coach not found.", None, 404)

        return api_response(True, "Seat layout loaded successfully.", {
            "coach": coach,
            "seats": seats,
            "lock_duration_seconds": Config.SEAT_LOCK_DURATION_SECONDS
        })
    except Exception as e:
        return api_response(False, f"Failed to retrieve seats: {str(e)}", None, 500)

@seat_bp.route('/seats/lock', methods=['POST'])
def lock_seats():
    data = request.get_json() or {}
    seat_ids = data.get('seat_ids', [])
    journey_date = data.get('journey_date')
    session_id = data.get('session_id')
    user = session.get('user')
    user_id = user['id'] if user else data.get('user_id')

    if not seat_ids or not journey_date or not session_id:
        return api_response(False, "seat_ids, journey_date, and session_id are required.", None, 400)

    try:
        success, result = SeatModel.lock_seats(
            seat_ids=seat_ids,
            journey_date=journey_date,
            session_id=session_id,
            user_id=user_id,
            duration_seconds=Config.SEAT_LOCK_DURATION_SECONDS
        )

        if not success:
            return api_response(False, result, None, 409)

        return api_response(True, f"Successfully locked {len(seat_ids)} seat(s) for 5 minutes.", result)
    except Exception as e:
        return api_response(False, f"Lock failed: {str(e)}", None, 500)

@seat_bp.route('/seats/release', methods=['POST'])
def release_seats():
    data = request.get_json() or {}
    session_id = data.get('session_id')
    seat_ids = data.get('seat_ids')

    if not session_id:
        return api_response(False, "session_id is required.", None, 400)

    try:
        SeatModel.release_seats(session_id, seat_ids)
        return api_response(True, "Seat locks released.", None)
    except Exception as e:
        return api_response(False, f"Release failed: {str(e)}", None, 500)

@seat_bp.route('/seats/recommend', methods=['POST'])
def get_recommendations():
    """
    AI Seat Recommendation API
    Evaluates ALL eligible available seats across ALL coaches of the selected class
    (or single coach), filtering out occupied and locked seats, and returns a complete ranked list.
    """
    from backend.services.railway_service import RailwayService
    data = request.get_json() or {}
    train_id = data.get('train_id')
    coach_id = data.get('coach_id')
    coach_class = data.get('coach_class')
    journey_date = data.get('journey_date')
    session_id = data.get('session_id') or session.get('session_id')
    passenger_type = data.get('passenger_type', 'general')
    preference = data.get('preference', 'WINDOW')
    count = data.get('count')

    if count is not None:
        try:
            count = int(count)
        except Exception:
            count = None

    if not coach_id and not (train_id and coach_class):
        return api_response(False, "coach_id or (train_id and coach_class) is required.", None, 400)

    try:
        # Resolve train_id and coach_class if coach_id is provided
        active_coach = None
        if coach_id:
            active_coach = execute_query("SELECT * FROM coaches WHERE id = %s", (coach_id,), fetchone=True)
            if not active_coach:
                return api_response(False, "Coach not found.", None, 404)
            if not train_id:
                train_id = active_coach['train_id']
            if not coach_class:
                coach_class = active_coach['coach_class']

        # Ensure full coach rake exists for train
        if train_id:
            RailwayService.ensure_train_coaches(train_id)

        # Retrieve all coaches for this class
        coaches = execute_query(
            "SELECT * FROM coaches WHERE train_id = %s AND UPPER(coach_class) = UPPER(%s)",
            (train_id, coach_class),
            fetchall=True
        )

        # Fallback to single active coach if no others found
        if not coaches and active_coach:
            coaches = [active_coach]

        if not coaches:
            return api_response(False, f"No coaches found for class {coach_class}.", None, 404)

        # Sort coaches naturally
        import re
        def coach_sort_key(c):
            c_num = c.get('coach_number', '') if isinstance(c, dict) else str(c)
            m = re.search(r'(\d+)', c_num)
            p = re.sub(r'\d+', '', c_num)
            return (p, int(m.group(1)) if m else 0)
        coaches.sort(key=coach_sort_key)

        coach_ids = [c['id'] for c in coaches]
        coach_map = {c['id']: c for c in coaches}

        # Fetch all seats in these coaches
        placeholders = ', '.join(['%s'] * len(coach_ids))
        seats_sql = f"""
            SELECT s.id, s.coach_id, s.seat_number, s.seat_type, s.is_window, s.is_aisle, s.deck_or_position
            FROM seats s
            WHERE s.coach_id IN ({placeholders})
            ORDER BY s.coach_id ASC, s.seat_number ASC
        """
        all_seats = execute_query(seats_sql, tuple(coach_ids), fetchall=True)

        if not journey_date:
            journey_date = datetime.now().strftime('%Y-%m-%d')

        # Find booked seats for these coaches and date
        booked_sql = f"""
            SELECT p.seat_id FROM passengers p
            JOIN bookings b ON p.booking_id = b.id
            WHERE b.coach_id IN ({placeholders}) AND b.journey_date = %s AND b.status = 'CONFIRMED' AND p.seat_id IS NOT NULL
        """
        booked_rows = execute_query(booked_sql, (*coach_ids, journey_date), fetchall=True)
        booked_seat_ids = set(r['seat_id'] for r in booked_rows)

        # Find active locked seats
        SeatModel.clean_expired_locks()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lock_sql = """
            SELECT seat_id, session_id FROM seat_locks
            WHERE journey_date = %s AND expires_at > %s
        """
        locked_rows = execute_query(lock_sql, (journey_date, now_str), fetchall=True)
        # Exclude seats locked by other sessions
        locked_seat_ids = set(r['seat_id'] for r in locked_rows if not (session_id and r['session_id'] == session_id))

        # Filter available seats
        available_seats = []
        for s in all_seats:
            sid = s['id']
            if sid in booked_seat_ids or sid in locked_seat_ids:
                continue
            c_info = coach_map.get(s['coach_id'], {})
            s_dict = dict(s)
            s_dict['coach_number'] = c_info.get('coach_number', '')
            s_dict['coach_class'] = c_info.get('coach_class', coach_class)
            s_dict['base_fare'] = c_info.get('base_fare', 0)
            available_seats.append(s_dict)

        recommendations = recommend_seats(
            available_seats=available_seats,
            passenger_type=passenger_type,
            preference=preference,
            coach_class=coach_class,
            count=count
        )

        top_match = recommendations[0] if recommendations else None

        return api_response(True, f"Generated {len(recommendations)} AI seat recommendation(s) across {len(coaches)} coach(es).", {
            "train_id": train_id,
            "coach_class": coach_class,
            "active_coach_id": coach_id,
            "passenger_type": passenger_type,
            "preference": preference,
            "total_coaches": len(coaches),
            "total_evaluated": len(available_seats),
            "top_match": top_match,
            "recommendations": recommendations
        })
    except Exception as e:
        return api_response(False, f"AI recommendation failed: {str(e)}", None, 500)
