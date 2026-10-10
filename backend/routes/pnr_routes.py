from flask import Blueprint, request, session
from datetime import datetime
from backend.models.booking_model import BookingModel
from backend.ml.pnr_predictor import predict_pnr_confirmation
from backend.utils.helpers import api_response

pnr_bp = Blueprint('pnr_bp', __name__)

@pnr_bp.route('/pnr/<pnr>', methods=['GET'])
def get_pnr_status(pnr):
    clean_pnr = str(pnr).strip()
    if not clean_pnr.isdigit() or len(clean_pnr) != 10:
        return api_response(False, "Invalid PNR format. PNR must be a 10-digit number.", None, 400)

    try:
        booking = BookingModel.get_by_pnr(clean_pnr)
        if not booking:
            return api_response(False, f"PNR {clean_pnr} not found in railway reservation system.", None, 404)

        # Attach AI Confirmation Prediction if status is WL or RAC
        prediction = None
        status_str = (booking.get('pnr_status') or booking.get('status') or '').upper()
        if 'WL' in status_str or 'WAITLIST' in status_str or 'RAC' in status_str:
            # Estimate waiting list number from status
            wl_num = 14
            for part in status_str.split():
                if part.isdigit():
                    wl_num = int(part)
                    break

            days_remaining = 5
            try:
                journey_dt = datetime.strptime(str(booking['journey_date'])[:10], '%Y-%m-%d')
                days_remaining = max(1, (journey_dt - datetime.now()).days)
            except Exception:
                pass

            prediction = predict_pnr_confirmation(
                wl_number=wl_num,
                days_left=days_remaining,
                train_type="Rajdhani Express" if "Rajdhani" in booking['train_name'] else "Superfast Express",
                class_type=booking['coach_class'],
                quota=booking['quota_code']
            )

        booking['ai_prediction'] = prediction
        return api_response(True, "PNR status retrieved successfully.", booking)
    except Exception as e:
        return api_response(False, f"Error fetching PNR: {str(e)}", None, 500)

@pnr_bp.route('/pnr/predict', methods=['POST'])
def predict_custom_pnr():
    data = request.get_json() or {}
    wl_number = data.get('waiting_list_number', 10)
    days_left = data.get('days_left', 7)
    train_type = data.get('train_type', 'Superfast Express')
    class_type = data.get('class_type', '3A')
    quota = data.get('quota', 'GN')

    try:
        pred = predict_pnr_confirmation(
            wl_number=wl_number,
            days_left=days_left,
            train_type=train_type,
            class_type=class_type,
            quota=quota
        )
        return api_response(True, "PNR confirmation prediction calculated.", pred)
    except Exception as e:
        return api_response(False, f"Prediction failed: {str(e)}", None, 500)

@pnr_bp.route('/pnr/<pnr>/refund-quote', methods=['GET', 'POST'])
def get_pnr_refund_quote(pnr):
    clean_pnr = str(pnr).strip()
    data = (request.get_json(silent=True) or {}) if request.method == 'POST' else {}
    passenger_ids = data.get('passenger_ids')
    try:
        success, quote = BookingModel.calculate_refund(clean_pnr, passenger_ids=passenger_ids)
        if not success:
            return api_response(False, quote, None, 400)
        return api_response(True, "Refund calculation retrieved successfully.", quote)
    except Exception as e:
        return api_response(False, f"Refund calculation failed: {str(e)}", None, 500)

@pnr_bp.route('/pnr/<pnr>/cancel', methods=['POST'])
def cancel_pnr(pnr):
    clean_pnr = str(pnr).strip()
    data = request.get_json(silent=True) or {}
    passenger_ids = data.get('passenger_ids')
    user = session.get('user') if 'session' in globals() else None
    user_id = user['id'] if user else None

    try:
        success, res = BookingModel.cancel_booking(clean_pnr, passenger_ids=passenger_ids, user_id=user_id)
        if not success:
            return api_response(False, res, None, 400)
        return api_response(True, "Ticket cancelled successfully.", res)
    except Exception as e:
        return api_response(False, f"Cancellation failed: {str(e)}", None, 500)

