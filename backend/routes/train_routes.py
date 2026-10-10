from flask import Blueprint, request, jsonify
from backend.models.train_model import TrainModel
from backend.services.railway_service import RailwayService
from backend.utils.helpers import api_response

train_bp = Blueprint('train_bp', __name__)

@train_bp.route('/stations', methods=['GET'])
def get_stations():
    """Returns all stations supported by the system."""
    try:
        stations = RailwayService.get_all_stations()
        return api_response(True, "Stations retrieved successfully.", stations)
    except Exception as e:
        return api_response(False, f"Failed to retrieve stations: {str(e)}", None, 500)

@train_bp.route('/stations/search', methods=['GET'])
def search_stations():
    """
    Dynamic autocomplete endpoint for station/city search.
    Query param: ?q=<search term>&limit=<optional count, default 10>
    """
    query = request.args.get('q', '').strip()
    try:
        limit = int(request.args.get('limit', 10))
    except (ValueError, TypeError):
        limit = 10

    try:
        results = RailwayService.search_stations(query, limit=limit)
        return api_response(True, f"Found {len(results)} matching station(s).", results)
    except Exception as e:
        return api_response(False, f"Station search failed: {str(e)}", None, 500)

@train_bp.route('/trains', methods=['GET'])
def get_all_trains():
    """Returns all active trains in the system."""
    try:
        trains = TrainModel.get_all_trains()
        return api_response(True, "Trains retrieved successfully.", trains)
    except Exception as e:
        return api_response(False, f"Failed to retrieve trains: {str(e)}", None, 500)

@train_bp.route('/trains/search', methods=['GET'])
def search_trains():
    """
    Unified train search endpoint supporting:
    - Route search (source, destination)
    - Train number (train_number or query)
    - Train name (train_name or query)
    - Date search modes: 'all' (all operating dates) vs 'specific' (specific calendar journey date)
    - Running day filter: e.g. Sunday, Monday, Wednesday...
    - Show non-running toggle: include trains not running on selected date for separate section
    - Optional filters: class (e.g. 3A), quota (e.g. GN, TQ, LD)
    """
    source = request.args.get('source', '').strip()
    destination = request.args.get('destination', '').strip()
    train_number = request.args.get('train_number', '').strip()
    train_name = request.args.get('train_name', '').strip()
    query = request.args.get('query', '').strip() or request.args.get('q', '').strip()
    date = request.args.get('date', '').strip()
    date_mode = request.args.get('date_mode', '').strip().lower()
    running_day = request.args.get('running_day', '').strip()
    show_non_running = request.args.get('show_non_running', '').strip().lower() in ('1', 'true', 'yes')
    class_type = request.args.get('class', '').strip()
    quota = request.args.get('quota', 'GN').strip()

    try:
        results = RailwayService.unified_search(
            query=query,
            train_number=train_number,
            train_name=train_name,
            source=source,
            destination=destination,
            date=date,
            class_type=class_type,
            quota=quota,
            date_mode=date_mode,
            running_day=running_day,
            show_non_running=show_non_running
        )
        effective_mode = date_mode if date_mode in ('all', 'specific') else ('specific' if date else 'all')
        return jsonify({
            "success": True,
            "message": f"Found {len(results)} train(s) matching your criteria.",
            "trains": results,
            "data": results,
            "date_mode": effective_mode,
            "selected_date": date if effective_mode == 'specific' else None
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error searching trains: {str(e)}",
            "trains": [],
            "data": [],
            "date_mode": date_mode or 'all',
            "selected_date": date or None
        }), 500

@train_bp.route('/trains/number/<train_number>', methods=['GET'])
def get_train_by_number(train_number):
    """Exact search by train number."""
    try:
        train = RailwayService.search_by_train_number(train_number)
        if not train:
            return api_response(False, f"Train number '{train_number}' not found.", None, 404)
        return api_response(True, "Train found.", train)
    except Exception as e:
        return api_response(False, f"Error fetching train: {str(e)}", None, 500)

@train_bp.route('/trains/name/<train_name>', methods=['GET'])
def get_trains_by_name(train_name):
    """Search trains by partial/full train name."""
    try:
        trains = RailwayService.search_by_train_name(train_name)
        return api_response(True, f"Found {len(trains)} matching train(s).", trains)
    except Exception as e:
        return api_response(False, f"Error searching trains: {str(e)}", None, 500)

@train_bp.route('/trains/<int:train_id>', methods=['GET'])
def get_train_details(train_id):
    """Get train details including stops and coaches by database ID."""
    try:
        train = TrainModel.get_by_id(train_id)
        if not train:
            return api_response(False, f"Train with ID {train_id} not found.", None, 404)
        return api_response(True, "Train details retrieved.", train)
    except Exception as e:
        return api_response(False, f"Error fetching train: {str(e)}", None, 500)
