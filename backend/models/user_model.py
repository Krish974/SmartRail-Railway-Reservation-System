from backend.utils.db_connection import execute_query
from backend.utils.helpers import hash_password, check_password

class UserModel:
    @staticmethod
    def get_by_id(user_id):
        sql = "SELECT id, name, email, phone, role, created_at FROM users WHERE id = %s"
        return execute_query(sql, (user_id,), fetchone=True)

    @staticmethod
    def get_by_email(email):
        sql = "SELECT * FROM users WHERE email = %s"
        return execute_query(sql, (email,), fetchone=True)

    @staticmethod
    def create(name, email, phone, password, role='USER'):
        hashed = hash_password(password)
        sql = """
            INSERT INTO users (name, email, phone, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
        """
        user_id = execute_query(sql, (name, email, phone, hashed, role), commit=True)
        return UserModel.get_by_id(user_id)

    @staticmethod
    def verify_credentials(email, password):
        user = UserModel.get_by_email(email)
        if not user:
            return None
        if check_password(user['password_hash'], password):
            # Do not leak password_hash
            user_clean = {k: v for k, v in user.items() if k != 'password_hash'}
            return user_clean
        return None

    @staticmethod
    def get_all(limit=50):
        sql = "SELECT id, name, email, phone, role, created_at FROM users ORDER BY id DESC LIMIT %s"
        return execute_query(sql, (limit,), fetchall=True)
