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
    SECRET_KEY = os.environ.get('SECRET_KEY', '').strip()
    if not SECRET_KEY:
        if os.environ.get('FLASK_ENV', '').lower() == 'production':
            raise RuntimeError(
                "[SECURITY FATAL] SECRET_KEY environment variable is required in production! "
                "Please configure a strong, unique SECRET_KEY in your hosting dashboard."
            )
        SECRET_KEY = 'smart-indian-railway-dev-key-2026'
    
    # Database Settings
    DATABASE_URL = os.environ.get('DATABASE_URL', os.environ.get('POSTGRES_URL', '')).strip()
    # Normalize postgres:// to postgresql:// if needed
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    # DB_TYPE: 'postgres', 'mysql', 'sqlite', or 'auto'
    # If DATABASE_URL is provided, default DB_TYPE to 'postgres'
    DB_TYPE = os.environ.get('DB_TYPE', 'postgres' if DATABASE_URL else 'auto').lower()
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
    
    # Production Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = (
        os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
        or os.environ.get('FLASK_ENV', '').lower() == 'production'
    )
    
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
