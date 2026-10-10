from flask import Blueprint, request, session
from backend.models.booking_model import BookingModel
from backend.models.quota_model import QuotaModel
from backend.utils.helpers import api_response, login_required

booking_bp = Blueprint('booking_bp', __name__)

@booking_bp.route('/bookings', methods=['POST'])
def create_booking():
    data = request.get_json() or {}
    user = session.get('user')
    user_id = user['id'] if user else data.get('user_id', 2) # Demo user fallback
    train_id = data.get('train_id')
    coach_id = data.get('coach_id')
    journey_date = data.get('journey_date')
    quota_code = data.get('quota_code', 'GN')
    passengers = data.get('passengers', [])
    session_id = data.get('session_id')

    if not train_id or not coach_id or not journey_date or not passengers:
        return api_response(False, "Missing required booking details.", None, 400)

    # Validate quota eligibility
    is_eligible, quota_msg = QuotaModel.validate_eligibility(quota_code, passengers)
    if not is_eligible:
        return api_response(False, quota_msg, None, 422)

    try:
        booking = BookingModel.create_booking(
            user_id=user_id,
            train_id=int(train_id),
            coach_id=int(coach_id),
            journey_date=journey_date,
            quota_code=quota_code,
            passengers=passengers,
            session_id=session_id,
            base_fare=data.get('base_fare'),
            from_station=data.get('from_station'),
            to_station=data.get('to_station')
        )

        return api_response(True, f"Ticket booked successfully! PNR: {booking['pnr']}", booking, 201)
    except Exception as e:
        return api_response(False, f"Booking creation failed: {str(e)}", None, 500)

@booking_bp.route('/bookings', methods=['GET'])
def get_user_bookings():
    user = session.get('user')
    user_id = user['id'] if user else request.args.get('user_id', 2)
    try:
        bookings = BookingModel.get_by_user_id(int(user_id))
        return api_response(True, f"Retrieved {len(bookings)} bookings.", bookings)
    except Exception as e:
        return api_response(False, f"Failed to retrieve bookings: {str(e)}", None, 500)

@booking_bp.route('/bookings/<int:booking_id>', methods=['GET'])
def get_booking_detail(booking_id):
    try:
        booking = BookingModel.get_by_id(booking_id)
        if not booking:
            return api_response(False, "Booking not found.", None, 404)
        return api_response(True, "Booking details retrieved.", booking)
    except Exception as e:
        return api_response(False, f"Failed to retrieve booking: {str(e)}", None, 500)

@booking_bp.route('/bookings/<int:booking_id>/refund-quote', methods=['GET', 'POST'])
def get_booking_refund_quote(booking_id):
    data = (request.get_json(silent=True) or {}) if request.method == 'POST' else {}
    passenger_ids = data.get('passenger_ids') or request.args.getlist('passenger_ids', type=int)
    try:
        success, quote = BookingModel.calculate_refund(booking_id, passenger_ids=passenger_ids if passenger_ids else None)
        if not success:
            return api_response(False, quote, None, 400)
        return api_response(True, "Refund calculation retrieved successfully.", quote)
    except Exception as e:
        return api_response(False, f"Refund calculation failed: {str(e)}", None, 500)

@booking_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    data = request.get_json(silent=True) or {}
    passenger_ids = data.get('passenger_ids')
    user = session.get('user')
    user_id = user['id'] if user else None

    try:
        success, res = BookingModel.cancel_booking(booking_id, passenger_ids=passenger_ids, user_id=user_id)
        if not success:
            return api_response(False, res, None, 400)
        return api_response(True, "Ticket cancelled successfully.", res)
    except Exception as e:
        return api_response(False, f"Cancellation failed: {str(e)}", None, 500)

