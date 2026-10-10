from datetime import datetime
import random
from backend.utils.db_connection import execute_query, get_db_type

TTE_ASSISTANCE_TYPES = [
    "Berth / Seat Issue",
    "RAC Assistance",
    "Ticket Verification",
    "Wrong Passenger on Berth",
    "Passenger Dispute",
    "Coach / Berth Assistance",
    "General On-board Assistance",
    "Other"
]

TTE_STATUSES = [
    "Pending",
    "Submitted",
    "Resolved",
    "Cancelled"
]

def ensure_tte_table():
    """Ensures tte_assistance_requests table exists across MySQL and SQLite."""
    db_type = get_db_type()
    if db_type == 'sqlite':
        sql = """
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
        """
    else:
        sql = """
            CREATE TABLE IF NOT EXISTS tte_assistance_requests (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id VARCHAR(50) NOT NULL UNIQUE,
                user_id INT NULL,
                train_number VARCHAR(20) NOT NULL,
                train_name VARCHAR(150) NULL,
                journey_date VARCHAR(30) NOT NULL,
                coach VARCHAR(20) NULL,
                berth VARCHAR(20) NULL,
                pnr VARCHAR(20) NULL,
                assistance_type VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                status VARCHAR(30) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                INDEX idx_tte_train (train_number),
                INDEX idx_tte_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    try:
        execute_query(sql, commit=True)
    except Exception as e:
        print(f"[DB INFO] ensure_tte_table warning: {e}")

def generate_tte_request_id():
    """
    Generates a unique TTE Assistance Request ID: TTE-YYYYMMDD-XXXXX
    e.g. TTE-20261005-00124
    """
    ensure_tte_table()
    date_str = datetime.now().strftime("%Y%m%d")
    for _ in range(10):
        rand_num = f"{random.randint(1, 99999):05d}"
        tid = f"TTE-{date_str}-{rand_num}"
        try:
            existing = execute_query("SELECT id FROM tte_assistance_requests WHERE request_id = %s", (tid,), fetchone=True)
            if not existing:
                return tid
        except Exception:
            return tid
    ms = datetime.now().strftime("%f")[:5]
    return f"TTE-{date_str}-{ms}"

class TTEAssistanceModel:
    @staticmethod
    def create_request(train_number, journey_date, assistance_type, description,
                       coach=None, berth=None, pnr=None, train_name=None, user_id=None):
        ensure_tte_table()
        request_id = generate_tte_request_id()

        clean_train = str(train_number).strip()
        clean_coach = str(coach).strip().upper() if coach else None
        clean_berth = str(berth).strip() if berth else None
        clean_pnr = str(pnr).strip() if pnr else None
        clean_name = str(train_name).strip() if train_name else None
        clean_date = str(journey_date).strip()
        clean_type = str(assistance_type).strip()
        clean_desc = str(description).strip()

        sql = """
            INSERT INTO tte_assistance_requests (
                request_id, user_id, train_number, train_name,
                journey_date, coach, berth, pnr,
                assistance_type, description, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
        """
        execute_query(sql, (
            request_id, user_id, clean_train, clean_name,
            clean_date, clean_coach, clean_berth, clean_pnr,
            clean_type, clean_desc
        ), commit=True)

        return TTEAssistanceModel.get_by_request_id(request_id)

    @staticmethod
    def get_by_request_id(request_id):
        ensure_tte_table()
        sql = "SELECT * FROM tte_assistance_requests WHERE request_id = %s"
        return execute_query(sql, (request_id,), fetchone=True)

    @staticmethod
    def get_all(limit=50):
        ensure_tte_table()
        sql = "SELECT * FROM tte_assistance_requests ORDER BY id DESC LIMIT %s"
        return execute_query(sql, (limit,), fetchall=True)

    @staticmethod
    def get_by_user_id(user_id, limit=50):
        ensure_tte_table()
        sql = "SELECT * FROM tte_assistance_requests WHERE user_id = %s ORDER BY id DESC LIMIT %s"
        return execute_query(sql, (user_id, limit), fetchall=True)

    @staticmethod
    def update_status(request_id, status):
        ensure_tte_table()
        clean_status = str(status).strip()
        # Case-insensitive normalization
        norm_map = {s.lower(): s for s in TTE_STATUSES}
        matched = norm_map.get(clean_status.lower())
        if not matched:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(TTE_STATUSES)}")

        sql = "UPDATE tte_assistance_requests SET status = %s WHERE request_id = %s"
        execute_query(sql, (matched, request_id), commit=True)
        return TTEAssistanceModel.get_by_request_id(request_id)
