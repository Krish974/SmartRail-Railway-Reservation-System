from flask import Blueprint, request, session
from backend.models.user_model import UserModel
from backend.utils.helpers import api_response

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not name or not email or not phone or not password:
        return api_response(False, "All fields are required.", None, 400)

    if password != confirm_password:
        return api_response(False, "Passwords do not match.", None, 400)

    if len(password) < 6:
        return api_response(False, "Password must be at least 6 characters long.", None, 400)

    existing = UserModel.get_by_email(email)
    if existing:
        return api_response(False, "An account with this email already exists. Please log in.", None, 409)

    try:
        user = UserModel.create(name, email, phone, password, role='USER')
        session['user'] = user
        return api_response(True, "Registration successful! Welcome to Smart Railway.", user, 201)
    except Exception as e:
        return api_response(False, f"Registration failed: {str(e)}", None, 500)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return api_response(False, "Email and password are required.", None, 400)

    user = UserModel.verify_credentials(email, password)
    if not user:
        return api_response(False, "Invalid email address or password.", None, 401)

    session['user'] = user
    return api_response(True, f"Welcome back, {user['name']}!", user, 200)

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('user', None)
    return api_response(True, "Logged out successfully.", None, 200)

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    user = session.get('user')
    if not user:
        return api_response(False, "Not logged in.", None, 401)
    return api_response(True, "User session active.", user, 200)
