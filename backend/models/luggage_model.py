from datetime import datetime
import random
from backend.utils.db_connection import execute_query, get_db_type

LUGGAGE_STATUSES = [
    "Submitted",
    "Under Investigation",
    "Found",
    "Returned",
    "Closed",
    "Cancelled"
]

def ensure_luggage_table():
    """Ensures left_luggage_requests table exists across MySQL and SQLite."""
    db_type = get_db_type()
    if db_type == 'sqlite':
        sql = """
            CREATE TABLE IF NOT EXISTS left_luggage_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                user_id INTEGER,
                pnr TEXT,
                train_number TEXT NOT NULL,
                train_name TEXT,
                journey_date TEXT NOT NULL,
                boarding_station TEXT,
                deboarding_station TEXT NOT NULL,
                coach_number TEXT NOT NULL,
                seat_number TEXT NOT NULL,
                luggage_description TEXT NOT NULL,
                luggage_contents TEXT,
                passenger_mobile TEXT NOT NULL,
                additional_details TEXT,
                status TEXT DEFAULT 'Submitted',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """
    else:
        sql = """
            CREATE TABLE IF NOT EXISTS left_luggage_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id VARCHAR(50) NOT NULL UNIQUE,
                user_id INT NULL,
                pnr VARCHAR(20) NULL,
                train_number VARCHAR(20) NOT NULL,
                train_name VARCHAR(150) NULL,
                journey_date VARCHAR(30) NOT NULL,
                boarding_station VARCHAR(100) NULL,
                deboarding_station VARCHAR(100) NOT NULL,
                coach_number VARCHAR(20) NOT NULL,
                seat_number VARCHAR(20) NOT NULL,
                luggage_description TEXT NOT NULL,
                luggage_contents TEXT NULL,
                passenger_mobile VARCHAR(20) NOT NULL,
                additional_details TEXT NULL,
                admin_notes TEXT NULL,
                status VARCHAR(30) DEFAULT 'Submitted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_luggage_train (train_number),
                INDEX idx_luggage_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    try:
        execute_query(sql, commit=True)
        # Ensure admin_notes column exists if table was created earlier without it
        try:
            execute_query("ALTER TABLE left_luggage_requests ADD COLUMN admin_notes TEXT", commit=True)
        except Exception:
            pass
    except Exception as e:
        print(f"[DB INFO] ensure_luggage_table warning: {e}")

def _normalize_row(row):
    if not row:
        return row
    d = dict(row)
    if 'coach_number' in d and 'coach' not in d:
        d['coach'] = d['coach_number']
    if 'seat_number' in d and 'seat' not in d:
        d['seat'] = d['seat_number']
    return d

def generate_luggage_request_id():
    """
    Generates a unique Left Luggage Request ID: LUG-YYYYMMDD-XXXXX
    Uses actual current date dynamically.
    e.g. LUG-20261007-00124
    """
    ensure_luggage_table()
    date_str = datetime.now().strftime("%Y%m%d")
    for _ in range(10):
        rand_num = f"{random.randint(1, 99999):05d}"
        lid = f"LUG-{date_str}-{rand_num}"
        try:
            existing = execute_query("SELECT id FROM left_luggage_requests WHERE request_id = %s", (lid,), fetchone=True)
            if not existing:
                return lid
        except Exception:
            return lid
    ms = datetime.now().strftime("%f")[:5]
    return f"LUG-{date_str}-{ms}"

class LuggageAssistanceModel:
    @staticmethod
    def create_request(train_number, journey_date, coach_number=None, seat_number=None,
                       deboarding_station=None, luggage_description=None, passenger_mobile=None,
                       pnr=None, train_name=None, boarding_station=None,
                       luggage_contents=None, additional_details=None, user_id=None,
                       coach=None, seat=None):
        ensure_luggage_table()
        request_id = generate_luggage_request_id()

        clean_train = str(train_number).strip()
        clean_date = str(journey_date).strip()
        coach_val = str(coach_number or coach or '').strip().upper()
        seat_val = str(seat_number or seat or '').strip()
        clean_deboarding = str(deboarding_station or '').strip()
        clean_desc = str(luggage_description or '').strip()
        clean_mobile = str(passenger_mobile or '').strip()

        clean_pnr = str(pnr).strip() if pnr else None
        clean_train_name = str(train_name).strip() if train_name else None
        clean_boarding = str(boarding_station).strip() if boarding_station else None
        clean_contents = str(luggage_contents).strip() if luggage_contents else None
        clean_details = str(additional_details).strip() if additional_details else None

        sql = """
            INSERT INTO left_luggage_requests (
                request_id, user_id, pnr, train_number, train_name,
                journey_date, boarding_station, deboarding_station,
                coach_number, seat_number, luggage_description,
                luggage_contents, passenger_mobile, additional_details,
                status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Submitted')
        """
        execute_query(sql, (
            request_id, user_id, clean_pnr, clean_train, clean_train_name,
            clean_date, clean_boarding, clean_deboarding,
            coach_val, seat_val, clean_desc,
            clean_contents, clean_mobile, clean_details
        ), commit=True)

        return LuggageAssistanceModel.get_by_request_id(request_id)

    @staticmethod
    def get_by_request_id(request_id):
        ensure_luggage_table()
        sql = "SELECT * FROM left_luggage_requests WHERE request_id = %s"
        row = execute_query(sql, (request_id,), fetchone=True)
        return _normalize_row(row)

    @staticmethod
    def get_all(limit=50):
        ensure_luggage_table()
        sql = "SELECT * FROM left_luggage_requests ORDER BY id DESC LIMIT %s"
        rows = execute_query(sql, (limit,), fetchall=True)
        return [_normalize_row(r) for r in rows] if rows else []

    @staticmethod
    def get_by_user_id(user_id, limit=50):
        ensure_luggage_table()
        sql = "SELECT * FROM left_luggage_requests WHERE user_id = %s ORDER BY id DESC LIMIT %s"
        rows = execute_query(sql, (user_id, limit), fetchall=True)
        return [_normalize_row(r) for r in rows] if rows else []

    @staticmethod
    def update_status(request_id, status, admin_notes=None):
        ensure_luggage_table()
        clean_status = str(status).strip()
        norm_map = {s.lower(): s for s in LUGGAGE_STATUSES}
        matched = norm_map.get(clean_status.lower())
        if not matched:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(LUGGAGE_STATUSES)}")

        if admin_notes is not None:
            try:
                execute_query("UPDATE left_luggage_requests SET status = %s, admin_notes = %s WHERE request_id = %s", (matched, admin_notes, request_id), commit=True)
            except Exception:
                execute_query("UPDATE left_luggage_requests SET status = %s WHERE request_id = %s", (matched, request_id), commit=True)
        else:
            execute_query("UPDATE left_luggage_requests SET status = %s WHERE request_id = %s", (matched, request_id), commit=True)

        res = LuggageAssistanceModel.get_by_request_id(request_id)
        if res and admin_notes is not None and ('admin_notes' not in res or not res['admin_notes']):
            res['admin_notes'] = admin_notes
        return res

