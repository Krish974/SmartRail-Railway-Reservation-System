import random
import string
import time
import functools
from flask import jsonify, session, request
from werkzeug.security import generate_password_hash, check_password_hash

def api_response(success=True, message="", data=None, status_code=200):
    """
    Standard API response formatter matching specification.
    """
    payload = {
        "success": success,
        "message": message,
        "data": data if data is not None else {}
    }
    return jsonify(payload), status_code

def hash_password(password: str) -> str:
    return generate_password_hash(password)

def check_password(p_hash: str, password: str) -> bool:
    if not p_hash or not password:
        return False
    return check_password_hash(p_hash, password)

def generate_pnr() -> str:
    """
    Generate a realistic 10-digit Indian Railway PNR number.
    Usually starts with 2, 4, 6, or 8 (zone prefixes).
    """
    prefix = random.choice(["2", "4", "6", "8"])
    suffix = "".join([str(random.randint(0, 9)) for _ in range(9)])
    return prefix + suffix

def generate_booking_reference() -> str:
    """
    Generate a booking transaction reference: IRCTC-2026-XXXXX
    """
    chars = string.ascii_uppercase + string.digits
    rand_str = "".join(random.choices(chars, k=6))
    return f"IRCTC-2026-{rand_str}"

def generate_incident_id() -> str:
    """
    Generate an SOS incident ID: SOS-2026-XXXX
    """
    rand_num = random.randint(1000, 9999)
    return f"SOS-2026-{rand_num}"

def calculate_fare_breakdown(base_fare: float, quota_code: str = 'GN', passenger_count: int = 1):
    """
    Calculate fare breakdown including class base fare, quota adjustment, GST, and convenience fee.
    """
    total_base = float(base_fare) * passenger_count
    quota_adjustment = 0.0
    
    code = (quota_code or 'GN').upper()
    if code == 'TQ':  # Tatkal (+30%)
        quota_adjustment = total_base * 0.30
    elif code == 'PT':  # Premium Tatkal (+50%)
        quota_adjustment = total_base * 0.50
    elif code == 'SS':  # Senior Citizen (-30%)
        quota_adjustment = -(total_base * 0.30)
    elif code == 'HP':  # Divyang (-50%)
        quota_adjustment = -(total_base * 0.50)
    
    subtotal = total_base + quota_adjustment
    # 5% GST on AC/Express fares
    gst = round(subtotal * 0.05, 2)
    convenience_fee = 17.70  # Standard IRCTC convenience charge
    total = round(subtotal + gst + convenience_fee, 2)
    
    return {
        "base_fare": round(total_base, 2),
        "quota_code": code,
        "quota_adjustment": round(quota_adjustment, 2),
        "subtotal": round(subtotal, 2),
        "gst": gst,
        "convenience_fee": convenience_fee,
        "total_fare": total
    }

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user:
            # Check Authorization header as alternative for REST API clients
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return api_response(False, "Authentication required. Please log in.", None, 401)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user.get('role') != 'ADMIN':
            return api_response(False, "Access denied. Admin privileges required.", None, 403)
        return f(*args, **kwargs)
    return decorated_function
