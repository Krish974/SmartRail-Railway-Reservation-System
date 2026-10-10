import re
from flask import Blueprint, request, session
from backend.models.emergency_model import EmergencyModel
from backend.models.cleaning_model import CleaningModel, CLEANING_ISSUES
from backend.models.tte_model import TTEAssistanceModel, TTE_ASSISTANCE_TYPES, TTE_STATUSES
from backend.models.luggage_model import LuggageAssistanceModel, LUGGAGE_STATUSES
from backend.services.railway_service import RailwayService
from backend.utils.helpers import api_response

emergency_bp = Blueprint('emergency_bp', __name__)

@emergency_bp.route('/emergency/sos', methods=['POST'])
def trigger_sos():
    data = request.get_json() or {}
    emergency_type = data.get('emergency_type', 'General Railway SOS')
    train_number = data.get('train_number', '12952')
    coach = data.get('coach', 'B1')
    seat = data.get('seat', '14')
    description = data.get('description', 'Emergency assistance requested on-board.')
    user_name = data.get('user_name', 'Passenger')
    user_phone = data.get('user_phone', '9812345678')

    user = session.get('user')
    user_id = user['id'] if user else None
    if user:
        user_name = user.get('name', user_name)
        user_phone = user.get('phone', user_phone)

    try:
        incident = EmergencyModel.create_incident(
            emergency_type=emergency_type,
            train_number=train_number,
            coach=coach,
            seat=seat,
            description=description,
            user_name=user_name,
            user_phone=user_phone,
            user_id=user_id
        )

        return api_response(True, "SOS Alert Dispatched to RPF & On-board Railway Staff!", incident, 201)
    except Exception as e:
        return api_response(False, f"Failed to dispatch SOS: {str(e)}", None, 500)

@emergency_bp.route('/emergency/<incident_id>', methods=['GET'])
def get_incident(incident_id):
    try:
        incident = EmergencyModel.get_by_incident_id(incident_id)
        if not incident:
            return api_response(False, "Incident record not found.", None, 404)
        return api_response(True, "Incident details retrieved.", incident)
    except Exception as e:
        return api_response(False, f"Error fetching incident: {str(e)}", None, 500)

# ==============================================================================
# COACH CLEANING / HOUSEKEEPING SERVICE REQUEST ENDPOINTS
# ==============================================================================

@emergency_bp.route('/emergency/cleaning', methods=['POST'])
def create_cleaning_request():
    data = request.get_json() or {}
    train_number = str(data.get('train_number', '')).strip()
    coach_number = str(data.get('coach_number', '')).strip()
    seat_number = str(data.get('seat_number', '')).strip() if data.get('seat_number') else None
    issue_type = str(data.get('issue_type', '')).strip()
    passenger_name = str(data.get('passenger_name', '')).strip()
    contact_mobile = str(data.get('contact_mobile', '')).strip()
    description = str(data.get('description', '')).strip()

    # Session defaults if user is logged in
    user = session.get('user')
    user_id = user['id'] if user else None
    if user:
        if not passenger_name:
            passenger_name = user.get('name', 'Passenger')
        if not contact_mobile:
            contact_mobile = user.get('phone', '')

    if not passenger_name:
        passenger_name = 'Passenger'

    # Validation
    if not train_number:
        return api_response(False, "Train number is required.", None, 400)

    train = RailwayService.search_by_train_number(train_number)
    if not train:
        return api_response(False, f"Train number '{train_number}' is invalid or does not exist in the database.", None, 400)

    if not coach_number:
        return api_response(False, "Coach number is required (e.g. B1, S2, A1).", None, 400)

    if not contact_mobile:
        return api_response(False, "Contact mobile number is required.", None, 400)

    if not issue_type:
        return api_response(False, "Cleaning issue type is required.", None, 400)

    # Check issue_type against supported list
    normalized_issues = {i.lower(): i for i in CLEANING_ISSUES}
    matched_issue = normalized_issues.get(issue_type.lower())
    if not matched_issue:
        return api_response(False, f"Invalid issue type. Must be one of: {', '.join(CLEANING_ISSUES)}", None, 400)

    try:
        req = CleaningModel.create_request(
            train_number=train_number,
            coach_number=coach_number,
            seat_number=seat_number,
            issue_type=matched_issue,
            passenger_name=passenger_name,
            contact_mobile=contact_mobile,
            description=description,
            user_id=user_id
        )
        return api_response(True, "Cleaning request registered successfully. Housekeeping team has been assigned.", req, 201)
    except Exception as e:
        return api_response(False, f"Failed to submit cleaning request: {str(e)}", None, 500)

@emergency_bp.route('/emergency/cleaning/<request_id>', methods=['GET'])
def get_cleaning_request(request_id):
    try:
        req = CleaningModel.get_by_request_id(request_id)
        if not req:
            return api_response(False, f"No cleaning request found matching ID '{request_id}'.", None, 404)
        return api_response(True, "Cleaning request details retrieved.", req)
    except Exception as e:
        return api_response(False, f"Error fetching cleaning request: {str(e)}", None, 500)

@emergency_bp.route('/emergency/cleaning', methods=['GET'])
def get_all_cleaning_requests():
    user = session.get('user')
    if user and user.get('role') != 'ADMIN':
        return api_response(False, "Access denied. Admin privileges required.", None, 403)

    limit = int(request.args.get('limit', 50))
    try:
        requests = CleaningModel.get_all(limit=limit)
        return api_response(True, f"Retrieved {len(requests)} cleaning requests.", requests)
    except Exception as e:
        return api_response(False, f"Failed to fetch cleaning requests: {str(e)}", None, 500)

@emergency_bp.route('/emergency/cleaning/<request_id>/status', methods=['PATCH', 'PUT'])
def update_cleaning_status(request_id):
    user = session.get('user')
    if user and user.get('role') != 'ADMIN':
        return api_response(False, "Access denied. Admin privileges required.", None, 403)

    data = request.get_json() or {}
    new_status = data.get('status')
    if not new_status:
        return api_response(False, "Status is required.", None, 400)

    try:
        updated = CleaningModel.update_status(request_id, new_status)
        if not updated:
            return api_response(False, f"Cleaning request '{request_id}' not found.", None, 404)
        return api_response(True, f"Cleaning request status updated to {new_status}.", updated)
    except ValueError as ve:
        return api_response(False, str(ve), None, 400)
    except Exception as e:
        return api_response(False, f"Failed to update cleaning status: {str(e)}", None, 500)

# ==============================================================================
# TTE / TRAIN STAFF PASSENGER ASSISTANCE ENDPOINTS
# ==============================================================================

@emergency_bp.route('/emergency/tte', methods=['POST'])
def create_tte_request():
    data = request.get_json() or {}
    train_number = str(data.get('train_number', '')).strip()
    journey_date = str(data.get('journey_date', '')).strip()
    coach = str(data.get('coach', '')).strip() if data.get('coach') else None
    berth = str(data.get('berth', '')).strip() if data.get('berth') else None
    pnr = str(data.get('pnr', '')).strip() if data.get('pnr') else None
    assistance_type = str(data.get('assistance_type', '')).strip()
    description = str(data.get('description', '')).strip()

    # Session defaults if user is logged in
    user = session.get('user')
    user_id = user['id'] if user else None

    # Validation: Required fields
    if not train_number:
        return api_response(False, "Train number is required.", None, 400)

    if not journey_date:
        return api_response(False, "Journey date is required.", None, 400)

    if not assistance_type:
        return api_response(False, "Assistance type is required.", None, 400)

    norm_types = {t.lower(): t for t in TTE_ASSISTANCE_TYPES}
    norm_types.update({
        'berth/seat issue': 'Berth / Seat Issue',
        'berth / seat issue': 'Berth / Seat Issue',
        'rac assistance': 'RAC Assistance',
        'ticket verification': 'Ticket Verification',
        'wrong passenger occupying berth': 'Wrong Passenger on Berth',
        'wrong passenger on berth': 'Wrong Passenger on Berth',
        'passenger dispute': 'Passenger Dispute',
        'coach / berth assistance': 'Coach / Berth Assistance',
        'coach/berth assistance': 'Coach / Berth Assistance',
        'general on-board assistance': 'General On-board Assistance',
        'general onboard assistance': 'General On-board Assistance',
        'other': 'Other',
        'other passenger assistance': 'Other'
    })
    matched_type = norm_types.get(assistance_type.lower())
    if not matched_type:
        return api_response(False, f"Invalid assistance type. Must be one of: {', '.join(TTE_ASSISTANCE_TYPES)}", None, 400)

    if not description or len(description) < 5:
        return api_response(False, "Please describe your issue (at least 5 characters).", None, 400)

    # Optional PNR validation (10 digits if provided)
    if pnr:
        if not re.fullmatch(r'\d{10}', pnr):
            return api_response(False, "PNR must be a valid 10-digit number.", None, 400)

    # Validate train and populate name
    train = RailwayService.search_by_train_number(train_number)
    train_name = train.get('train_name') if train else f"Train {train_number}"

    try:
        req = TTEAssistanceModel.create_request(
            train_number=train_number,
            journey_date=journey_date,
            assistance_type=matched_type,
            description=description,
            coach=coach,
            berth=berth,
            pnr=pnr,
            train_name=train_name,
            user_id=user_id
        )
        return api_response(True, "Assistance request submitted successfully.", req, 201)
    except Exception as e:
        return api_response(False, f"Failed to submit TTE assistance request: {str(e)}", None, 500)

@emergency_bp.route('/emergency/tte/<request_id>', methods=['GET'])
def get_tte_request(request_id):
    try:
        req = TTEAssistanceModel.get_by_request_id(request_id)
        if not req:
            return api_response(False, f"No assistance request found matching ID '{request_id}'.", None, 404)
        return api_response(True, "TTE assistance request details retrieved.", req)
    except Exception as e:
        return api_response(False, f"Error fetching TTE assistance request: {str(e)}", None, 500)

@emergency_bp.route('/emergency/tte', methods=['GET'])
def get_all_tte_requests():
    limit = int(request.args.get('limit', 50))
    try:
        requests = TTEAssistanceModel.get_all(limit=limit)
        return api_response(True, f"Retrieved {len(requests)} TTE assistance requests.", requests)
    except Exception as e:
        return api_response(False, f"Failed to fetch TTE assistance requests: {str(e)}", None, 500)

@emergency_bp.route('/emergency/tte/<request_id>/status', methods=['PATCH', 'PUT'])
def update_tte_status(request_id):
    user = session.get('user')
    if user and user.get('role') != 'ADMIN':
        return api_response(False, "Access denied. Admin privileges required.", None, 403)

    data = request.get_json() or {}
    new_status = data.get('status')
    if not new_status:
        return api_response(False, "Status is required.", None, 400)

    try:
        updated = TTEAssistanceModel.update_status(request_id, new_status)
        if not updated:
            return api_response(False, f"TTE assistance request '{request_id}' not found.", None, 404)
        return api_response(True, f"Assistance request status updated to {new_status}.", updated)
    except ValueError as ve:
        return api_response(False, str(ve), None, 400)
    except Exception as e:
        return api_response(False, f"Failed to update TTE assistance status: {str(e)}", None, 500)

# ==============================================================================
# LEFT LUGGAGE / FORGOTTEN LUGGAGE ASSISTANCE ENDPOINTS
# ==============================================================================

@emergency_bp.route('/emergency/luggage', methods=['POST'])
def create_luggage_request():
    data = request.get_json() or {}
    train_number = str(data.get('train_number', '')).strip()
    journey_date = str(data.get('journey_date', '')).strip()
    coach_number = str(data.get('coach_number') or data.get('coach', '')).strip()
    seat_number = str(data.get('seat_number') or data.get('seat', '')).strip()
    deboarding_station = str(data.get('deboarding_station', '')).strip()
    luggage_description = str(data.get('luggage_description') or data.get('description', '')).strip()
    passenger_mobile = str(data.get('passenger_mobile') or data.get('mobile', '')).strip()

    pnr = str(data.get('pnr', '')).strip() if data.get('pnr') else None
    train_name = str(data.get('train_name', '')).strip() if data.get('train_name') else None
    boarding_station = str(data.get('boarding_station', '')).strip() if data.get('boarding_station') else None
    luggage_contents = str(data.get('luggage_contents', '')).strip() if data.get('luggage_contents') else None
    additional_details = str(data.get('additional_details') or data.get('details', '')).strip() if (data.get('additional_details') or data.get('details')) else None

    user = session.get('user')
    user_id = user['id'] if user else None
    if user and not passenger_mobile:
        passenger_mobile = user.get('phone', '')

    # Validation: Required fields
    if not train_number:
        return api_response(False, "Train number is required.", None, 400)

    if not journey_date:
        return api_response(False, "Journey date is required.", None, 400)

    if not coach_number:
        return api_response(False, "Coach number is required (e.g. B2, S4).", None, 400)

    if not seat_number:
        return api_response(False, "Seat / berth number is required.", None, 400)

    if not deboarding_station:
        return api_response(False, "Deboarding station is required.", None, 400)

    if not luggage_description or len(luggage_description) < 3:
        return api_response(False, "Please provide a description of the luggage.", None, 400)

    if not passenger_mobile:
        return api_response(False, "Passenger mobile number is required.", None, 400)

    # Validate mobile (at least 10 digits)
    digits_mobile = re.sub(r'\D', '', passenger_mobile)
    if len(digits_mobile) < 10:
        return api_response(False, "Please enter a valid 10-digit mobile number.", None, 400)

    # Optional PNR validation (10 digits if provided)
    if pnr:
        if not re.fullmatch(r'\d{10}', pnr):
            return api_response(False, "PNR must be a valid 10-digit number.", None, 400)

    # Validate train and populate name if missing
    if not train_name:
        train = RailwayService.search_by_train_number(train_number)
        train_name = train.get('train_name') if train else f"Train {train_number}"

    try:
        req = LuggageAssistanceModel.create_request(
            train_number=train_number,
            journey_date=journey_date,
            coach_number=coach_number,
            seat_number=seat_number,
            deboarding_station=deboarding_station,
            luggage_description=luggage_description,
            passenger_mobile=passenger_mobile,
            pnr=pnr,
            train_name=train_name,
            boarding_station=boarding_station,
            luggage_contents=luggage_contents,
            additional_details=additional_details,
            user_id=user_id
        )
        return api_response(True, "Left luggage assistance request submitted successfully.", req, 201)
    except Exception as e:
        return api_response(False, f"Failed to submit left luggage request: {str(e)}", None, 500)

@emergency_bp.route('/emergency/luggage/<request_id>', methods=['GET'])
def get_luggage_request(request_id):
    try:
        req = LuggageAssistanceModel.get_by_request_id(request_id)
        if not req:
            return api_response(False, f"No left luggage request found matching ID '{request_id}'.", None, 404)
        return api_response(True, "Left luggage request details retrieved.", req)
    except Exception as e:
        return api_response(False, f"Error fetching left luggage request: {str(e)}", None, 500)

@emergency_bp.route('/emergency/luggage', methods=['GET'])
def get_all_luggage_requests():
    limit = int(request.args.get('limit', 50))
    try:
        requests = LuggageAssistanceModel.get_all(limit=limit)
        return api_response(True, f"Retrieved {len(requests)} left luggage requests.", requests)
    except Exception as e:
        return api_response(False, f"Failed to fetch left luggage requests: {str(e)}", None, 500)

@emergency_bp.route('/emergency/luggage/<request_id>/status', methods=['PATCH', 'PUT'])
def update_luggage_status(request_id):
    user = session.get('user')
    if user and user.get('role') != 'ADMIN':
        return api_response(False, "Access denied. Admin privileges required.", None, 403)

    data = request.get_json() or {}
    new_status = data.get('status')
    if not new_status:
        return api_response(False, "Status is required.", None, 400)

    admin_notes = data.get('admin_notes')

    try:
        updated = LuggageAssistanceModel.update_status(request_id, new_status, admin_notes=admin_notes)
        if not updated:
            return api_response(False, f"Left luggage request '{request_id}' not found.", None, 404)
        return api_response(True, f"Left luggage request status updated to {new_status}.", updated)
    except ValueError as ve:
        return api_response(False, str(ve), None, 400)
    except Exception as e:
        return api_response(False, f"Failed to update left luggage status: {str(e)}", None, 500)


