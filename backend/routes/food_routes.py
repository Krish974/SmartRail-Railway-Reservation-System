import datetime
from flask import Blueprint, request, session
from backend.models.food_model import FoodModel
from backend.models.booking_model import BookingModel
from backend.services.railway_service import RailwayService
from backend.utils.db_connection import execute_query
from backend.utils.helpers import api_response, login_required

food_bp = Blueprint('food_bp', __name__)

@food_bp.route('/journey-info', methods=['GET'])
def get_journey_info():
    """
    Retrieves passenger journey info and route halts for food ordering.
    Supports either PNR lookup or Train Number + Journey Date lookup.
    Enforces valid route halts only (no non-halt waypoints or random stations).
    """
    pnr = request.args.get('pnr', '').strip()
    train_number = request.args.get('train_number', '').strip()
    journey_date = request.args.get('date', '').strip() or datetime.date.today().strftime('%Y-%m-%d')

    if not pnr and not train_number:
        return api_response(False, "Please provide either a 10-digit PNR or Train Number.", None, 400)

    booking = None
    passenger_info = None

    if pnr:
        booking = BookingModel.get_by_pnr(pnr)
        if not booking:
            return api_response(False, f"Reservation with PNR '{pnr}' not found. Please verify the 10-digit number.", None, 404)
        
        train_number = booking['train_number']
        journey_date = booking['journey_date']
        
        # Prepare passenger prefill
        passengers = booking.get('passengers', [])
        primary_passenger = passengers[0] if passengers else {}
        passenger_info = {
            "pnr": pnr,
            "passenger_name": primary_passenger.get('name') or booking.get('user_name', 'Passenger'),
            "contact_phone": booking.get('user_phone', ''),
            "coach": booking.get('coach_number', 'B1'),
            "seat": primary_passenger.get('seat_number_assigned') or 'Berth Confirmed',
            "all_passengers": passengers
        }

    # Ensure train route is cached in database
    train, stops = RailwayService.ensure_train_route_cached(train_number)
    if not train:
        return api_response(False, f"Train #{train_number} not found in railway database.", None, 404)

    # If stops are still empty (e.g. initial sync), fetch direct stops
    if not stops:
        stops = RailwayService._get_train_stops(train['id'])

    # Fetch station restaurant counts to highlight delivery availability
    # Build list of valid halts
    valid_halts = []
    for s in stops:
        st_id = s.get('station_id')
        st_code = s.get('station_code') or ''
        st_name = s.get('station_name') or ''
        
        # Count available restaurants at this station
        rest_count = execute_query(
            "SELECT COUNT(*) as cnt FROM food_restaurants WHERE station_id = %s AND active = 1",
            (st_id,), fetchone=True
        )['cnt']

        valid_halts.append({
            "stop_sequence": s.get('stop_sequence'),
            "station_id": st_id,
            "station_code": st_code,
            "station_name": st_name,
            "arrival_time": s.get('arrival_time'),
            "departure_time": s.get('departure_time'),
            "halt_minutes": s.get('halt_minutes', 0),
            "distance_km": s.get('distance_km', 0.0),
            "has_food_delivery": bool(rest_count > 0),
            "restaurant_count": rest_count
        })

    # Retrieve live train telemetry if available
    tracking = RailwayService.get_train_tracking_summary(train_number)
    live_status = None
    if tracking:
        live_status = {
            "available": True,
            "current_section": tracking.get('current_section'),
            "current_speed": tracking.get('current_speed'),
            "next_station": tracking.get('next_station'),
            "eta": tracking.get('eta'),
            "delay_minutes": tracking.get('delay_minutes', 0),
            "delay_status": tracking.get('delay_status')
        }
    else:
        live_status = {
            "available": False,
            "message": "Live status unavailable"
        }

    data = {
        "search_type": "PNR" if booking else "TRAIN",
        "pnr": pnr if booking else None,
        "train": {
            "id": train['id'],
            "number": train['train_number'],
            "name": train['train_name'],
            "source_code": train.get('source_code'),
            "source_name": train.get('source_name'),
            "dest_code": train.get('dest_code'),
            "dest_name": train.get('dest_name')
        },
        "train_id": train['id'],
        "train_number": train['train_number'],
        "train_name": train['train_name'],
        "source_code": train.get('source_code'),
        "source_name": train.get('source_name'),
        "source_station": train.get('source_name') or train.get('source_code'),
        "dest_code": train.get('dest_code'),
        "dest_name": train.get('dest_name'),
        "destination_station": train.get('dest_name') or train.get('dest_code'),
        "journey_date": journey_date,
        "passenger_info": passenger_info,
        "route_halts": valid_halts,
        "live_status": live_status
    }

    return api_response(True, "Journey route and delivery stations retrieved successfully.", data)

@food_bp.route('/partners', methods=['GET'])
def get_food_partners():
    """
    Returns list of authorized IRCTC eCatering partners and brand restaurants.
    Supports filtering by category/cuisine if provided.
    """
    category = request.args.get('category', '').strip()
    query = "SELECT id, slug, name, tagline, description, logo_icon, website_url, cuisines, is_featured, is_official FROM food_partners WHERE active = 1"
    params = []
    if category and category.lower() != 'all':
        query += " AND cuisines LIKE %s"
        params.append(f"%{category}%")
    query += " ORDER BY is_featured DESC, id ASC"

    partners = execute_query(query, tuple(params) if params else None, fetchall=True) or []
    return api_response(True, f"Retrieved {len(partners)} catering partner(s).", {
        "partners": partners
    })

@food_bp.route('/stations/<int:station_id>/restaurants', methods=['GET'])
def get_station_restaurants(station_id):
    """
    Returns active food vendors/restaurants available at the specified delivery station.
    """
    # Verify station exists
    station = execute_query("SELECT id, code, name, city FROM stations WHERE id = %s", (station_id,), fetchone=True)
    if not station:
        return api_response(False, "Station not found.", None, 404)

    restaurants = FoodModel.get_restaurants_for_station(station_id)
    return api_response(True, f"Found {len(restaurants)} restaurants at {station['name']} ({station['code']}).", {
        "station": station,
        "restaurants": restaurants
    })

@food_bp.route('/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    """
    Returns the categorized menu items for a restaurant.
    Supports filtering by category and vegetarian preference.
    """
    restaurant = FoodModel.get_restaurant_by_id(restaurant_id)
    if not restaurant:
        return api_response(False, "Restaurant not found.", None, 404)

    category = request.args.get('category')
    veg_only = request.args.get('veg_only', '').lower() in ('1', 'true', 'yes')

    menu_items = FoodModel.get_menu_for_restaurant(restaurant_id, category=category, veg_only=veg_only)

    # Group items by category for UI tabs
    categories_dict = {}
    for item in menu_items:
        cat = item['category']
        if cat not in categories_dict:
            categories_dict[cat] = []
        categories_dict[cat].append(item)

    return api_response(True, "Menu retrieved successfully.", {
        "restaurant": restaurant,
        "categories": list(categories_dict.keys()),
        "menu_by_category": categories_dict,
        "menu_items": menu_items,
        "all_items": menu_items
    })

@food_bp.route('/orders', methods=['POST'])
def place_food_order():
    """
    Places a new railway food order with validation:
    1. User is authenticated (or attached to valid session)
    2. Train exists
    3. Selected delivery station exists and is on the train route
    4. Restaurant is available at selected station
    5. Food items are available and quantities valid
    6. Generates unique FOOD-YYYYMMDD-XXXXX order ID
    """
    data = request.get_json() or {}

    # Check authentication (or session)
    user = session.get('user')
    user_id = user.get('id') if user else None

    # Required fields validation (support both frontend and API aliases)
    passenger_name = (data.get('passenger_name') or data.get('name') or '').strip()
    contact_phone = (data.get('passenger_phone') or data.get('contact_phone') or '').strip()
    train_number = str(data.get('train_number') or '').strip()
    delivery_station_id = data.get('delivery_station_id')
    coach = str(data.get('coach') or data.get('coach_number') or '').strip()
    seat = str(data.get('seat_number') or data.get('seat') or '').strip()
    items = data.get('items', [])

    if not passenger_name:
        return api_response(False, "Passenger name is required.", None, 400)
    if not contact_phone:
        return api_response(False, "Contact mobile number is required.", None, 400)
    if not train_number:
        return api_response(False, "Train number is required.", None, 400)
    if not delivery_station_id:
        return api_response(False, "Please select a delivery station.", None, 400)
    if not coach:
        return api_response(False, "Coach number is required (e.g. B3, S2, A1).", None, 400)
    if not seat:
        return api_response(False, "Seat or berth number is required.", None, 400)
    if not items or len(items) == 0:
        return api_response(False, "Your food cart is empty. Please add items to proceed.", None, 400)

    # 1. Verify train exists
    train_row = execute_query("SELECT id, train_number, train_name FROM trains WHERE train_number = %s", (train_number,), fetchone=True)
    if not train_row:
        return api_response(False, f"Train #{train_number} not found in railway records.", None, 404)

    # 2. Verify station exists
    station_row = execute_query("SELECT id, code, name FROM stations WHERE id = %s", (delivery_station_id,), fetchone=True)
    if not station_row:
        return api_response(False, "Selected delivery station does not exist.", None, 404)

    # 3. Verify selected station belongs to the train route!
    stop_check = execute_query(
        "SELECT id, arrival_time, departure_time FROM train_stops WHERE train_id = %s AND station_id = %s",
        (train_row['id'], delivery_station_id),
        fetchone=True
    )
    if not stop_check:
        return api_response(
            False,
            f"Invalid delivery station! Train #{train_number} does not halt at {station_row['name']} ({station_row['code']}). Food can only be delivered at verified scheduled halts on this route.",
            None,
            400
        )

    # 4. Verify items and availability
    subtotal = 0.0
    verified_items = []
    for itm in items:
        m_id = itm.get('menu_item_id')
        qty = int(itm.get('quantity', 1))
        if qty <= 0:
            return api_response(False, "Item quantity must be greater than zero.", None, 400)

        menu_row = execute_query(
            "SELECT id, name, price, available, active FROM food_menu_items WHERE id = %s",
            (m_id,), fetchone=True
        )
        if not menu_row or not menu_row['active']:
            return api_response(False, f"Item '{itm.get('item_name')}' is no longer available.", None, 400)
        if not menu_row['available']:
            return api_response(False, f"Item '{menu_row['name']}' is currently out of stock at this station.", None, 400)

        unit_p = float(menu_row['price'])
        tot_p = unit_p * qty
        subtotal += tot_p

        verified_items.append({
            "menu_item_id": menu_row['id'],
            "item_name": menu_row['name'],
            "quantity": qty,
            "unit_price": unit_p,
            "total_price": tot_p
        })

    delivery_fee = 20.0
    total_amount = subtotal + delivery_fee

    order_payload = {
        "passenger_name": passenger_name,
        "contact_phone": contact_phone,
        "pnr": data.get('pnr'),
        "train_id": train_row['id'],
        "train_number": train_row['train_number'],
        "delivery_station_id": delivery_station_id,
        "delivery_station_name": f"{station_row['name']} ({station_row['code']})",
        "coach": coach.upper(),
        "seat": seat,
        "delivery_eta": stop_check.get('arrival_time', 'On Train Arrival'),
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total_amount": total_amount,
        "payment_method": data.get('payment_method', 'UPI'),
        "payment_status": 'PAID' if data.get('payment_method') != 'COD' else 'PENDING',
        "notes": data.get('notes', '')
    }

    try:
        new_order = FoodModel.create_order(order_payload, verified_items, user_id=user_id)
        return api_response(True, "Food order successfully placed and confirmed!", {
            "order": new_order,
            "order_number": new_order['order_number'],
            "order_id": new_order['id'],
            **new_order
        }, 201)
    except Exception as e:
        return api_response(False, f"Failed to place food order: {str(e)}", None, 500)

@food_bp.route('/orders/<order_number>', methods=['GET'])
def get_order_details(order_number):
    """
    Retrieves full details of a food order by order number or ID,
    including delivery station, items breakdown, and 7-stage status timeline.
    """
    order = FoodModel.get_order_by_number(order_number)
    if not order:
        return api_response(False, f"Food order '{order_number}' not found.", None, 404)
    return api_response(True, "Order details retrieved.", {
        "order": order,
        **order
    })

@food_bp.route('/orders/my-orders', methods=['GET'])
def get_my_orders():
    """
    Retrieves orders placed by the current session user.
    """
    user = session.get('user')
    user_id = user.get('id') if user else None
    orders = FoodModel.get_all_orders(limit=50, user_id=user_id)
    return api_response(True, f"Retrieved {len(orders)} order(s).", {
        "orders": orders
    })
