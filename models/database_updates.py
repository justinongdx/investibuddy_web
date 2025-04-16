from models.database_manager import DatabaseManager


def add_password_reset_table():
    """Add the password_reset_tokens table to the database"""
    db_manager = DatabaseManager()

    # Create the password_reset_tokens table if it doesn't exist
    db_manager.execute_action('''
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        token TEXT NOT NULL,
        expiration TEXT NOT NULL,
        FOREIGN KEY (email) REFERENCES users(email)
    )
    ''')

    print("Password reset tokens table created successfully.")


if __name__ == "__main__":
    add_password_reset_table()