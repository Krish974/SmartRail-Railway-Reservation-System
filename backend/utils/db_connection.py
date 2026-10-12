import os
import sqlite3
import re
from backend.config import Config

# Optional PostgreSQL driver
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    RealDictCursor = None

# Optional MySQL driver
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    MySQLError = Exception

_active_db_type = None

def get_db_type():
    global _active_db_type
    if _active_db_type:
        return _active_db_type
    
    if Config.DB_TYPE == 'sqlite':
        _active_db_type = 'sqlite'
        return _active_db_type

    # 1. Check PostgreSQL if configured or if DATABASE_URL is set
    if (Config.DATABASE_URL or Config.DB_TYPE in ('postgres', 'postgresql')) and POSTGRES_AVAILABLE:
        try:
            if Config.DATABASE_URL:
                conn = psycopg2.connect(Config.DATABASE_URL, connect_timeout=4)
            else:
                conn = psycopg2.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT if Config.DB_PORT != 3306 else 5432,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    dbname=Config.DB_NAME,
                    connect_timeout=4
                )
            conn.close()
            _active_db_type = 'postgres'
            print("[DB] Successfully connected to PostgreSQL production database.")
            return _active_db_type
        except Exception as e:
            err_msg = f"[DB FATAL ERROR] PostgreSQL connection failed: {e}."
            if Config.DATABASE_URL:
                err_msg += " Verify that your DATABASE_URL is correct and the PostgreSQL service is running."
            if Config.DATABASE_URL or Config.DB_TYPE in ('postgres', 'postgresql') or os.environ.get('FLASK_ENV', '').lower() == 'production':
                raise RuntimeError(f"{err_msg} Silent fallback to local SQLite is disabled in production to prevent data loss.")
            print(f"[DB WARNING] {e}. Falling back to local SQLite for offline development.")
            _active_db_type = 'sqlite'
            return _active_db_type
    
    # 2. Check MySQL
    if MYSQL_AVAILABLE and Config.DB_TYPE in ('mysql', 'auto'):
        try:
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                connect_timeout=3
            )
            conn.close()
            _active_db_type = 'mysql'
            print(f"[DB] Successfully connected to MySQL database '{Config.DB_NAME}' at {Config.DB_HOST}:{Config.DB_PORT}")
            return _active_db_type
        except Exception as e:
            if Config.DB_TYPE == 'mysql':
                if os.environ.get('FLASK_ENV', '').lower() == 'production':
                    raise RuntimeError(f"[DB FATAL ERROR] MySQL connection failed in production: {e}. Silent fallback to local SQLite is disabled.")
                print(f"[DB WARNING] MySQL connection failed: {e}. Falling back to local SQLite.")
                _active_db_type = 'sqlite'
                return _active_db_type
    
    if os.environ.get('FLASK_ENV', '').lower() == 'production' and Config.DB_TYPE != 'sqlite':
        raise RuntimeError("[DB FATAL ERROR] In production, an external persistent database (PostgreSQL via DATABASE_URL or MySQL) is required. Silent fallback to ephemeral SQLite is disabled to prevent data loss.")

    _active_db_type = 'sqlite'
    print("[DB INFO] PostgreSQL/MySQL not active or unreachable. Falling back to local SQLite database with seeded data seamlessly.")
    return _active_db_type

def get_connection():
    db_type = get_db_type()
    if db_type == 'postgres':
        if Config.DATABASE_URL:
            return psycopg2.connect(Config.DATABASE_URL)
        return psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT if Config.DB_PORT != 3306 else 5432,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            dbname=Config.DB_NAME
        )
    elif db_type == 'mysql':
        return mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            autocommit=True
        )
    else:
        os.makedirs(os.path.dirname(Config.SQLITE_PATH), exist_ok=True)
        conn = sqlite3.connect(Config.SQLITE_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(sql, params=None, fetchone=False, fetchall=False, commit=False):
    """
    Unified query runner. Works seamlessly across PostgreSQL, MySQL, and SQLite.
    Parameters in sql use '%s' placeholder syntax.
    """
    db_type = get_db_type()
    conn = get_connection()
    cursor = None
    try:
        if db_type == 'postgres':
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Auto-handle returning id for INSERT if lastrowid is expected
            is_insert = sql.strip().upper().startswith('INSERT')
            has_returning = 'RETURNING' in sql.upper()
            query_sql = sql
            return_id = False
            
            if is_insert and not has_returning and not fetchone and not fetchall:
                query_sql = sql.rstrip().rstrip(';') + ' RETURNING id'
                return_id = True
                
            try:
                cursor.execute(query_sql, params or ())
            except Exception:
                if return_id:
                    conn.rollback()
                    query_sql = sql
                    return_id = False
                    cursor.execute(query_sql, params or ())
                else:
                    raise

            last_id = None
            if return_id:
                try:
                    res_row = cursor.fetchone()
                    if res_row and 'id' in res_row:
                        last_id = res_row['id']
                except Exception:
                    pass

            if commit:
                conn.commit()
            if fetchone:
                res = cursor.fetchone()
                return dict(res) if res else None
            if fetchall:
                res = cursor.fetchall()
                return [dict(r) for r in res] if res else []
            return last_id

        elif db_type == 'mysql':
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params or ())
            if commit:
                conn.commit()
            if fetchone:
                res = cursor.fetchone()
                return res
            if fetchall:
                res = cursor.fetchall()
                return res
            return cursor.lastrowid
        else:
            # SQLite adaptation
            # Replace %s with ? safely
            sqlite_sql = sql.replace('%s', '?')
            # SQLite ON DUPLICATE KEY UPDATE replacement if present
            if 'ON DUPLICATE KEY UPDATE' in sqlite_sql.upper():
                sqlite_sql = re.sub(r'ON DUPLICATE KEY UPDATE.*$', '', sqlite_sql, flags=re.IGNORECASE).strip()
                sqlite_sql = sqlite_sql.replace('INSERT INTO', 'INSERT OR IGNORE INTO')
            
            cursor = conn.cursor()
            cursor.execute(sqlite_sql, params or ())
            if commit:
                conn.commit()
            if fetchone:
                row = cursor.fetchone()
                return dict(row) if row else None
            if fetchall:
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            return cursor.lastrowid
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def init_db():
    """
    Initializes SQLite fallback database if MySQL/Postgres is not being used or if tables do not exist.
    Never overwrites or deletes existing production or local data.
    """
    db_type = get_db_type()
    if db_type == 'postgres':
        print("[DB INFO] PostgreSQL active. Preserving existing production database without automatic modifications.")
        return
    elif db_type == 'sqlite':
        os.makedirs(os.path.dirname(Config.SQLITE_PATH), exist_ok=True)
        conn = sqlite3.connect(Config.SQLITE_PATH)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("[DB SETUP] Initializing SQLite tables and seeding initial Indian Railway data...")
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'USER',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS stations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    aliases TEXT
                );

                CREATE TABLE IF NOT EXISTS trains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    train_number TEXT NOT NULL UNIQUE,
                    train_name TEXT NOT NULL,
                    source_station_id INTEGER,
                    dest_station_id INTEGER,
                    departure_time TEXT,
                    arrival_time TEXT,
                    duration TEXT,
                    running_days TEXT,
                    train_type TEXT DEFAULT 'Superfast Express',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS train_stops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    train_id INTEGER NOT NULL,
                    station_id INTEGER NOT NULL,
                    stop_sequence INTEGER NOT NULL,
                    arrival_time TEXT NOT NULL,
                    departure_time TEXT NOT NULL,
                    halt_minutes INTEGER DEFAULT 0,
                    distance_km REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
                    FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE CASCADE,
                    UNIQUE(train_id, station_id)
                );

                CREATE TABLE IF NOT EXISTS coaches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    train_id INTEGER NOT NULL,
                    coach_number TEXT NOT NULL,
                    coach_class TEXT NOT NULL,
                    total_seats INTEGER NOT NULL DEFAULT 72,
                    base_fare REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS seats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coach_id INTEGER NOT NULL,
                    seat_number INTEGER NOT NULL,
                    seat_type TEXT NOT NULL,
                    is_window INTEGER DEFAULT 0,
                    is_aisle INTEGER DEFAULT 0,
                    deck_or_position TEXT DEFAULT 'STANDARD',
                    UNIQUE(coach_id, seat_number)
                );

                CREATE TABLE IF NOT EXISTS quotas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    discount_or_premium_pct REAL DEFAULT 0.0,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_reference TEXT NOT NULL UNIQUE,
                    pnr TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    train_id INTEGER NOT NULL,
                    coach_id INTEGER NOT NULL,
                    journey_date TEXT NOT NULL,
                    quota_code TEXT DEFAULT 'GN',
                    base_fare REAL NOT NULL,
                    tax_amount REAL NOT NULL DEFAULT 0.0,
                    convenience_fee REAL NOT NULL DEFAULT 17.70,
                    total_fare REAL NOT NULL,
                    status TEXT DEFAULT 'CONFIRMED',
                    chart_prepared INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS passengers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id INTEGER NOT NULL,
                    seat_id INTEGER,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    gender TEXT NOT NULL,
                    id_type TEXT NOT NULL,
                    id_number TEXT NOT NULL,
                    seat_number_assigned TEXT,
                    berth_type TEXT,
                    status TEXT DEFAULT 'CONFIRMED'
                );

                CREATE TABLE IF NOT EXISTS pnr_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pnr TEXT NOT NULL UNIQUE,
                    booking_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    chart_status TEXT DEFAULT 'Chart Not Prepared',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS seat_locks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seat_id INTEGER NOT NULL,
                    journey_date TEXT NOT NULL,
                    user_id INTEGER,
                    session_id TEXT NOT NULL,
                    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                );

                CREATE TABLE IF NOT EXISTS train_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    train_id INTEGER NOT NULL UNIQUE,
                    current_latitude REAL NOT NULL,
                    current_longitude REAL NOT NULL,
                    current_speed REAL NOT NULL,
                    delay_minutes INTEGER DEFAULT 0,
                    next_station TEXT NOT NULL,
                    eta TEXT NOT NULL,
                    distance_travelled_km REAL NOT NULL,
                    route_coordinates_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS emergency_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER,
                    user_name TEXT NOT NULL,
                    user_phone TEXT NOT NULL,
                    emergency_type TEXT NOT NULL,
                    train_number TEXT NOT NULL,
                    coach TEXT NOT NULL,
                    seat TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'RECEIVED',
                    response_note TEXT DEFAULT 'Alert logged. RPF Control Room notified.',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS cleaning_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER,
                    passenger_name TEXT NOT NULL,
                    contact_mobile TEXT NOT NULL,
                    train_number TEXT NOT NULL,
                    coach_number TEXT NOT NULL,
                    seat_number TEXT,
                    issue_type TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );
            ''')
            
            # Seed initial data into SQLite
            from werkzeug.security import generate_password_hash
            from backend.utils.seed_dataset import STATIONS, QUOTAS, TRAINS, STOPS, COACHES
            admin_pwd = generate_password_hash('Admin@12345')
            user_pwd = generate_password_hash('User@12345')

            cursor.executescript(f'''
                INSERT OR IGNORE INTO users (id, name, email, phone, password_hash, role) VALUES
                (1, 'Railway Super Admin', 'admin@railway.gov.in', '9876543210', '{admin_pwd}', 'ADMIN'),
                (2, 'Rahul Sharma', 'rahul.sharma@example.com', '9812345678', '{user_pwd}', 'USER'),
                (3, 'Priya Patel', 'priya.patel@example.com', '9898765432', '{user_pwd}', 'USER');
            ''')

            cursor.executemany('''
                INSERT OR IGNORE INTO stations (id, code, name, city, state, latitude, longitude, aliases)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', STATIONS)

            cursor.executemany('''
                INSERT OR IGNORE INTO quotas (id, code, name, discount_or_premium_pct, description)
                VALUES (?, ?, ?, ?, ?)
            ''', QUOTAS)

            cursor.executemany('''
                INSERT OR IGNORE INTO trains (id, train_number, train_name, source_station_id, dest_station_id, departure_time, arrival_time, duration, running_days, train_type, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', TRAINS)

            cursor.executemany('''
                INSERT OR IGNORE INTO train_stops (train_id, station_id, stop_sequence, arrival_time, departure_time, halt_minutes, distance_km)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', STOPS)

            cursor.executemany('''
                INSERT OR IGNORE INTO coaches (id, train_id, coach_number, coach_class, total_seats, base_fare)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', COACHES)

            cursor.executescript('''
                INSERT OR IGNORE INTO bookings (id, booking_reference, pnr, user_id, train_id, coach_id, journey_date, quota_code, base_fare, tax_amount, convenience_fee, total_fare, status, chart_prepared) VALUES
                (1, 'IRCTC-2026-98101', '2846190532', 2, 1, 1, '2026-10-05', 'GN', 2050.00, 102.50, 17.70, 2170.20, 'CONFIRMED', 1),
                (2, 'IRCTC-2026-98102', '4198273641', 2, 1, 1, '2026-10-10', 'GN', 4100.00, 205.00, 17.70, 4322.70, 'RAC', 0),
                (3, 'IRCTC-2026-98103', '6720491823', 3, 17, 45, '2026-10-12', 'GN', 2050.00, 102.50, 17.70, 2170.20, 'WAITLIST', 0);

                INSERT OR IGNORE INTO passengers (id, booking_id, seat_id, name, age, gender, id_type, id_number, seat_number_assigned, berth_type, status) VALUES
                (1, 1, 1, 'Rahul Sharma', 32, 'Male', 'Aadhaar', 'XXXX-XXXX-9021', 'B1-1', 'LOWER', 'CONFIRMED'),
                (2, 2, NULL, 'Sunita Sharma', 58, 'Female', 'Aadhaar', 'XXXX-XXXX-1122', 'B1-RAC-1', 'SIDE_LOWER', 'RAC'),
                (3, 2, NULL, 'Amit Sharma', 34, 'Male', 'PAN Card', 'ABCDE1234F', 'B1-RAC-2', 'SIDE_LOWER', 'RAC'),
                (4, 3, NULL, 'Priya Patel', 28, 'Female', 'Voter ID', 'VTR8923019', 'WL-14', 'WAITLIST', 'WAITLIST');

                INSERT OR IGNORE INTO pnr_records (id, pnr, booking_id, status, chart_status) VALUES
                (1, '2846190532', 1, 'CONFIRMED', 'Chart Prepared'),
                (2, '4198273641', 2, 'RAC 1, RAC 2', 'Chart Not Prepared'),
                (3, '6720491823', 3, 'WL 14', 'Chart Not Prepared');

                INSERT OR IGNORE INTO train_tracking (id, train_id, current_latitude, current_longitude, current_speed, delay_minutes, next_station, eta, distance_travelled_km, route_coordinates_json) VALUES
                (1, 1, 24.5854, 73.7125, 128.5, 5, 'Ratlam Junction (RTM)', '19:40', 492.0, '[[28.6427,77.2197],[27.4924,77.6737],[26.9196,75.7878],[25.2138,75.8648],[23.3341,75.0376],[22.3072,73.1812],[21.1702,72.8311],[18.9696,72.8193]]'),
                (2, 2, 21.1702, 72.8311, 115.0, 0, 'Vadodara Junction (BRC)', '20:15', 263.0, '[[18.9696,72.8193],[21.1702,72.8311],[22.3072,73.1812],[23.3341,75.0376],[25.2138,75.8648],[26.9196,75.7878],[27.4924,77.6737],[28.6427,77.2197]]'),
                (3, 9, 26.9196, 75.7878, 125.0, 2, 'Jaipur Junction (JP)', '10:35', 308.0, '[[28.6427,77.2197],[28.4595,77.0266],[28.1920,76.6190],[27.5530,76.6346],[26.9196,75.7878],[26.4526,74.6399]]');

                INSERT OR IGNORE INTO emergency_logs (id, incident_id, user_id, user_name, user_phone, emergency_type, train_number, coach, seat, description, status, response_note) VALUES
                (1, 'SOS-2026-0091', 2, 'Rahul Sharma', '9812345678', 'Medical Emergency', '12952', 'B1', '14', 'Passenger feeling severe dizziness and requiring immediate doctor assistance at next halt.', 'DISPATCHED', 'Station Doctor at Kota Jn alerted. RPF escort standing by.'),
                (2, 'SOS-2026-0092', 3, 'Priya Patel', '9898765432', 'Women Safety', '12015', 'C1', '23', 'Suspicious person without reservation disturbing coach passengers.', 'RESOLVED', 'RPF squad attended coach at Jaipur Junction. Situation resolved peacefully.');
            ''')
            
            # Populate seats for all coaches (1 through 15)
            # 3A/SL: 72 seats, 2A: 48 seats, CC: 75 seats, 1A: 24 seats
            cursor.execute("SELECT id, coach_class, total_seats FROM coaches")
            coach_records = cursor.fetchall()
            for c_id, c_class, total_s in coach_records:
                for seat_no in range(1, total_s + 1):
                    is_win = 0
                    is_aisle = 0
                    if c_class in ('3A', 'SL'):
                        mod = seat_no % 8
                        if mod in (1, 4):
                            b_type = 'LOWER'
                            if mod == 1: is_win = 1
                            else: is_aisle = 1
                        elif mod in (2, 5):
                            b_type = 'MIDDLE'
                        elif mod in (3, 6):
                            b_type = 'UPPER'
                        elif mod == 7:
                            b_type = 'SIDE_LOWER'
                            is_win = 1
                        else:
                            b_type = 'SIDE_UPPER'
                    elif c_class == '2A':
                        mod = seat_no % 6
                        if mod in (1, 3):
                            b_type = 'LOWER'
                            if mod == 1: is_win = 1
                            else: is_aisle = 1
                        elif mod in (2, 4):
                            b_type = 'UPPER'
                        elif mod == 5:
                            b_type = 'SIDE_LOWER'
                            is_win = 1
                        else:
                            b_type = 'SIDE_UPPER'
                    elif c_class == 'CC':
                        mod = seat_no % 5
                        if mod in (1, 0):
                            b_type = 'WINDOW'
                            is_win = 1
                        elif mod in (2, 4):
                            b_type = 'AISLE'
                            is_aisle = 1
                        else:
                            b_type = 'MIDDLE'
                    else: # 1A / EC
                        mod = seat_no % 4
                        if mod in (1, 0):
                            b_type = 'LOWER'
                            is_win = 1
                        else:
                            b_type = 'UPPER'
                            is_aisle = 1
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO seats (coach_id, seat_number, seat_type, is_window, is_aisle, deck_or_position)
                        VALUES (?, ?, ?, ?, ?, 'STANDARD')
                    ''', (c_id, seat_no, b_type, is_win, is_aisle))
            
            conn.commit()
            print("[DB SETUP] Initialized tables and populated 800+ seats successfully!")
        
        # Ensure cleaning_requests table exists for existing databases
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleaning_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                user_id INTEGER,
                passenger_name TEXT NOT NULL,
                contact_mobile TEXT NOT NULL,
                train_number TEXT NOT NULL,
                coach_number TEXT NOT NULL,
                seat_number TEXT,
                issue_type TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')

        # Ensure tte_assistance_requests table exists for existing databases
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tte_assistance_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                user_id INTEGER,
                train_number TEXT NOT NULL,
                train_name TEXT,
                journey_date TEXT NOT NULL,
                coach TEXT,
                berth TEXT,
                pnr TEXT,
                assistance_type TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')

        # Ensure train_route_points table exists for passing stations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS train_route_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                train_id INTEGER NOT NULL,
                station_id INTEGER,
                point_name TEXT NOT NULL,
                point_code TEXT,
                route_sequence INTEGER NOT NULL,
                point_type TEXT DEFAULT 'PASSING',
                estimated_time TEXT,
                distance_km REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (train_id) REFERENCES trains(id) ON DELETE CASCADE,
                FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE SET NULL
            )
        ''')

        # Seed passing points if table is empty
        cursor.execute("SELECT COUNT(*) as cnt FROM train_route_points")
        if cursor.fetchone()[0] == 0:
            from backend.utils.seed_dataset import PASSING_POINTS
            cursor.executemany('''
                INSERT INTO train_route_points (train_id, station_id, point_name, point_code, route_sequence, point_type, estimated_time, distance_km)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', PASSING_POINTS)

        conn.commit()
        conn.close()

    # Ensure route cache metadata columns exist across SQLite and MySQL
    ensure_route_cache_columns()

    # Ensure railway food ordering tables exist and are seeded
    ensure_food_order_tables()

def ensure_route_cache_columns():
    """
    Ensures trains table has route metadata columns:
    - route_status: 'pending', 'complete', 'failed', 'not_available'
    - route_synced_at: TIMESTAMP
    - route_error: TEXT
    - route_stop_count: INTEGER
    Also marks existing trains with >= 2 stops as 'complete'.
    """
    db_type = get_db_type()
    if db_type == 'postgres':
        return
    conn = get_connection()
    cursor = conn.cursor() if db_type == 'sqlite' else conn.cursor(dictionary=True)
    try:
        if db_type == 'sqlite':
            cursor.execute("PRAGMA table_info(trains)")
            existing_cols = [row[1] if isinstance(row, (tuple, list)) else row['name'] for row in cursor.fetchall()]
            
            if 'route_status' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_status TEXT DEFAULT 'pending'")
            if 'route_synced_at' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_synced_at TIMESTAMP NULL")
            if 'route_error' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_error TEXT NULL")
            if 'route_stop_count' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_stop_count INTEGER DEFAULT 0")

            # Update existing complete routes
            cursor.execute("""
                UPDATE trains
                SET route_status = 'complete',
                    route_synced_at = COALESCE(route_synced_at, CURRENT_TIMESTAMP),
                    route_stop_count = (
                        SELECT COUNT(*) FROM train_stops WHERE train_stops.train_id = trains.id
                    )
                WHERE (
                    SELECT COUNT(*) FROM train_stops WHERE train_stops.train_id = trains.id
                ) >= 2 AND (route_status IS NULL OR route_status = 'pending')
            """)
            conn.commit()
        else:
            # MySQL
            cursor.execute("SHOW COLUMNS FROM trains")
            existing_cols = [row['Field'] for row in cursor.fetchall()]
            if 'route_status' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_status VARCHAR(20) DEFAULT 'pending'")
            if 'route_synced_at' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_synced_at TIMESTAMP NULL")
            if 'route_error' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_error TEXT NULL")
            if 'route_stop_count' not in existing_cols:
                cursor.execute("ALTER TABLE trains ADD COLUMN route_stop_count INT DEFAULT 0")
            
            cursor.execute("""
                UPDATE trains t
                JOIN (
                    SELECT train_id, COUNT(*) as cnt FROM train_stops GROUP BY train_id HAVING cnt >= 2
                ) s ON t.id = s.train_id
                SET t.route_status = 'complete',
                    t.route_synced_at = COALESCE(t.route_synced_at, CURRENT_TIMESTAMP),
                    t.route_stop_count = s.cnt
                WHERE t.route_status IS NULL OR t.route_status = 'pending'
            """)
            conn.commit()
    except Exception as e:
        print(f"[DB MIGRATION WARNING] ensure_route_cache_columns: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def ensure_food_order_tables():
    """
    Ensures all tables for Railway Food Ordering exist:
    - food_restaurants
    - food_menu_items
    - food_orders
    - food_order_items
    - food_order_status_history
    And seeds initial verified partner demo vendors and categorized menu if empty.
    """
    db_type = get_db_type()
    if db_type == 'postgres':
        return
    conn = get_connection()
    cursor = conn.cursor() if db_type == 'sqlite' else conn.cursor(dictionary=True)
    try:
        if db_type == 'sqlite':
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS food_partners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    tagline TEXT,
                    description TEXT,
                    logo_icon TEXT,
                    website_url TEXT NOT NULL,
                    cuisines TEXT,
                    is_featured INTEGER DEFAULT 0,
                    is_official INTEGER DEFAULT 1,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS food_restaurants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    cuisine TEXT,
                    rating REAL DEFAULT 4.2,
                    image_url TEXT,
                    prep_time TEXT DEFAULT '20-25 min',
                    min_order REAL DEFAULT 100.0,
                    is_veg_only INTEGER DEFAULT 0,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS food_menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restaurant_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    price REAL NOT NULL,
                    is_veg INTEGER DEFAULT 1,
                    image_url TEXT,
                    rating REAL DEFAULT 4.5,
                    available INTEGER DEFAULT 1,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (restaurant_id) REFERENCES food_restaurants(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS food_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT NOT NULL UNIQUE,
                    user_id INTEGER,
                    passenger_name TEXT NOT NULL,
                    contact_phone TEXT NOT NULL,
                    pnr TEXT,
                    train_id INTEGER,
                    train_number TEXT NOT NULL,
                    delivery_station_id INTEGER NOT NULL,
                    delivery_station_name TEXT NOT NULL,
                    coach TEXT NOT NULL,
                    seat TEXT NOT NULL,
                    delivery_eta TEXT,
                    subtotal REAL NOT NULL,
                    delivery_fee REAL DEFAULT 20.0,
                    total_amount REAL NOT NULL,
                    payment_method TEXT DEFAULT 'UPI',
                    payment_status TEXT DEFAULT 'PAID',
                    order_status TEXT DEFAULT 'Placed',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (delivery_station_id) REFERENCES stations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS food_order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    menu_item_id INTEGER,
                    item_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES food_orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (menu_item_id) REFERENCES food_menu_items(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS food_order_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    note TEXT,
                    FOREIGN KEY (order_id) REFERENCES food_orders(id) ON DELETE CASCADE
                );
            ''')
            conn.commit()

            # Check if seeding is needed
            cursor.execute("SELECT COUNT(*) FROM food_restaurants")
            cnt = cursor.fetchone()[0]
            if cnt == 0:
                print("[DB SETUP] Seeding verified Railway Food Ordering vendors and menus...")
                from backend.utils.seed_food_dataset import DEMO_RESTAURANTS, STANDARD_ITEMS

                for r in DEMO_RESTAURANTS:
                    cursor.execute("SELECT id, name FROM stations WHERE code = ?", (r["station_code"],))
                    st = cursor.fetchone()
                    if not st:
                        continue
                    st_id = st[0]

                    cursor.execute('''
                        INSERT INTO food_restaurants (station_id, name, description, cuisine, rating, image_url, prep_time, min_order, is_veg_only, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ''', (
                        st_id, r["name"], r["description"], r["cuisine"], r["rating"],
                        r["image_url"], r["prep_time"], r["min_order"], r["is_veg_only"]
                    ))
                    restaurant_id = cursor.lastrowid

                    # Insert menu items
                    for cat, items in STANDARD_ITEMS.items():
                        for itm in items:
                            # If restaurant is veg only and item is non-veg, skip
                            if r["is_veg_only"] and not itm["is_veg"]:
                                continue
                            cursor.execute('''
                                INSERT INTO food_menu_items (restaurant_id, name, description, category, price, is_veg, image_url, rating, available, active)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
                            ''', (
                                restaurant_id, itm["name"], itm["description"], itm["category"],
                                itm["price"], itm["is_veg"], itm["image_url"], itm["rating"]
                            ))
                conn.commit()
                print("[DB SETUP] Railway Food Ordering tables and demo vendors initialized.")

            # Check if food_partners seeding is needed
            cursor.execute("SELECT COUNT(*) FROM food_partners")
            if cursor.fetchone()[0] == 0:
                from backend.utils.seed_food_dataset import OFFICIAL_PARTNERS
                for p in OFFICIAL_PARTNERS:
                    cursor.execute('''
                        INSERT OR IGNORE INTO food_partners (slug, name, tagline, description, logo_icon, website_url, cuisines, is_featured, is_official, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ''', (
                        p["slug"], p["name"], p["tagline"], p["description"], p["logo_icon"],
                        p["website_url"], p["cuisines"], p["is_featured"], p["is_official"]
                    ))
                conn.commit()
        else:
            # MySQL DDL
            mysql_tables = [
                """
                CREATE TABLE IF NOT EXISTS food_partners (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    slug VARCHAR(100) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    tagline VARCHAR(255),
                    description TEXT,
                    logo_icon VARCHAR(100),
                    website_url VARCHAR(500) NOT NULL,
                    cuisines VARCHAR(255),
                    is_featured TINYINT(1) DEFAULT 0,
                    is_official TINYINT(1) DEFAULT 1,
                    active TINYINT(1) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """,
                """
                CREATE TABLE IF NOT EXISTS food_restaurants (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    station_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    cuisine VARCHAR(255),
                    rating DECIMAL(3,1) DEFAULT 4.2,
                    image_url VARCHAR(500),
                    prep_time VARCHAR(50) DEFAULT '20-25 min',
                    min_order DECIMAL(10,2) DEFAULT 100.0,
                    is_veg_only TINYINT(1) DEFAULT 0,
                    active TINYINT(1) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (station_id) REFERENCES stations(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """,
                """
                CREATE TABLE IF NOT EXISTS food_menu_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    restaurant_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    category VARCHAR(100) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    is_veg TINYINT(1) DEFAULT 1,
                    image_url VARCHAR(500),
                    rating DECIMAL(3,1) DEFAULT 4.5,
                    available TINYINT(1) DEFAULT 1,
                    active TINYINT(1) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (restaurant_id) REFERENCES food_restaurants(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """,
                """
                CREATE TABLE IF NOT EXISTS food_orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_number VARCHAR(50) NOT NULL UNIQUE,
                    user_id INT NULL,
                    passenger_name VARCHAR(255) NOT NULL,
                    contact_phone VARCHAR(50) NOT NULL,
                    pnr VARCHAR(20) NULL,
                    train_id INT NULL,
                    train_number VARCHAR(20) NOT NULL,
                    delivery_station_id INT NOT NULL,
                    delivery_station_name VARCHAR(255) NOT NULL,
                    coach VARCHAR(20) NOT NULL,
                    seat VARCHAR(20) NOT NULL,
                    delivery_eta VARCHAR(50),
                    subtotal DECIMAL(10,2) NOT NULL,
                    delivery_fee DECIMAL(10,2) DEFAULT 20.0,
                    total_amount DECIMAL(10,2) NOT NULL,
                    payment_method VARCHAR(50) DEFAULT 'UPI',
                    payment_status VARCHAR(50) DEFAULT 'PAID',
                    order_status VARCHAR(50) DEFAULT 'Placed',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (delivery_station_id) REFERENCES stations(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """,
                """
                CREATE TABLE IF NOT EXISTS food_order_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    menu_item_id INT NULL,
                    item_name VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total_price DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES food_orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (menu_item_id) REFERENCES food_menu_items(id) ON DELETE SET NULL
                ) ENGINE=InnoDB;
                """,
                """
                CREATE TABLE IF NOT EXISTS food_order_status_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    note TEXT,
                    FOREIGN KEY (order_id) REFERENCES food_orders(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """
            ]
            for sql in mysql_tables:
                cursor.execute(sql)
            conn.commit()

            cursor.execute("SELECT COUNT(*) as cnt FROM food_restaurants")
            row = cursor.fetchone()
            cnt = row['cnt'] if isinstance(row, dict) else row[0]
            if cnt == 0:
                print("[DB SETUP] Seeding verified Railway Food Ordering vendors and menus (MySQL)...")
                from backend.utils.seed_food_dataset import DEMO_RESTAURANTS, STANDARD_ITEMS
                for r in DEMO_RESTAURANTS:
                    cursor.execute("SELECT id FROM stations WHERE code = %s", (r["station_code"],))
                    st = cursor.fetchone()
                    if not st:
                        continue
                    st_id = st['id'] if isinstance(st, dict) else st[0]
                    cursor.execute("""
                        INSERT INTO food_restaurants (station_id, name, description, cuisine, rating, image_url, prep_time, min_order, is_veg_only, active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, (
                        st_id, r["name"], r["description"], r["cuisine"], r["rating"],
                        r["image_url"], r["prep_time"], r["min_order"], r["is_veg_only"]
                    ))
                    restaurant_id = cursor.lastrowid

                    for cat, items in STANDARD_ITEMS.items():
                        for itm in items:
                            if r["is_veg_only"] and not itm["is_veg"]:
                                continue
                            cursor.execute("""
                                INSERT INTO food_menu_items (restaurant_id, name, description, category, price, is_veg, image_url, rating, available, active)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 1)
                            """, (
                                restaurant_id, itm["name"], itm["description"], itm["category"],
                                itm["price"], itm["is_veg"], itm["image_url"], itm["rating"]
                            ))
                conn.commit()

            cursor.execute("SELECT COUNT(*) as cnt FROM food_partners")
            row_p = cursor.fetchone()
            cnt_p = row_p['cnt'] if isinstance(row_p, dict) else row_p[0]
            if cnt_p == 0:
                from backend.utils.seed_food_dataset import OFFICIAL_PARTNERS
                for p in OFFICIAL_PARTNERS:
                    cursor.execute("""
                        INSERT IGNORE INTO food_partners (slug, name, tagline, description, logo_icon, website_url, cuisines, is_featured, is_official, active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, (
                        p["slug"], p["name"], p["tagline"], p["description"], p["logo_icon"],
                        p["website_url"], p["cuisines"], p["is_featured"], p["is_official"]
                    ))
                conn.commit()
    except Exception as e:
        print(f"[DB MIGRATION WARNING] ensure_food_order_tables: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

