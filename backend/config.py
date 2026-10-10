import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))

# Load .env file from project root
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-indian-railway-secret-key-2026-secure')
    
    # Database Settings
    DB_TYPE = os.environ.get('DB_TYPE', 'auto') # 'mysql', 'sqlite', or 'auto'
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'railway_db')
    
    # SQLite fallback file
    SQLITE_PATH = os.path.join(PROJECT_ROOT, 'database', 'railway_db.sqlite')
    
    # Session / Token Settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SEAT_LOCK_DURATION_SECONDS = 300  # 5 minutes seat lock
    
    # CORS
    CORS_HEADERS = 'Content-Type'

    # Qrail API Configuration (Legacy/Disabled)
    QRAIL_API_KEY = os.environ.get('QRAIL_API_KEY', '').strip()
    QRAIL_BASE_URL = os.environ.get('QRAIL_BASE_URL', 'https://api.qrail.in').strip().rstrip('/')
    QRAIL_IMPORT_LIMIT = int(os.environ.get('QRAIL_IMPORT_LIMIT', 5))

    # RailRadar API Configuration (Active Data Provider)
    RAILRADAR_API_KEY = os.environ.get('RAILRADAR_API_KEY', '').strip()
    RAILRADAR_BASE_URL = os.environ.get('RAILRADAR_BASE_URL', 'https://api.railradar.in').strip().rstrip('/')
    RAILRADAR_ROUTE_DELAY = float(os.environ.get('RAILRADAR_ROUTE_DELAY', 1.0))
