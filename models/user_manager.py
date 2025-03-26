from typing import Optional
from models.database_manager import DatabaseManager

class UserManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def register_user(self, username: str, password: str, risk_tolerance: str) -> bool:
        try:
            self.db_manager.execute_action(
                "INSERT INTO users (username, password, risk_tolerance) VALUES (?, ?, ?)",
                (username, password, risk_tolerance))
            return True
        except Exception:
            return False

    def login_user(self, username: str, password: str) -> Optional[int]:
        result = self.db_manager.execute_query(
            "SELECT user_id FROM users WHERE username = ? AND password = ?",
            (username, password))
        return result[0][0] if result else None

    def get_user_risk_tolerance(self, user_id: int) -> str:
        result = self.db_manager.execute_query(
            "SELECT risk_tolerance FROM users WHERE user_id = ?", (user_id,))
        return result[0][0] if result else "Low"

    def update_risk_tolerance(self, user_id: int, new_risk: str) -> None:
        self.db_manager.execute_action(
            "UPDATE users SET risk_tolerance = ? WHERE user_id = ?",
            (new_risk, user_id))
