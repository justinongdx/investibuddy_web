from typing import Optional, Tuple
from models.database_manager import DatabaseManager
import re
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime


class UserManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def is_strong_password(self, password: str) -> Tuple[bool, str]:
        """Check if password meets strength requirements"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        return True, "Password is strong"

    def generate_verification_code(self) -> str:
        """Generate a random 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))

    def send_verification_email(self, email: str, verification_code: str) -> bool:
        """Send verification email with 2FA code"""
        try:
            # Get email credentials from environment variables
            # You would need to set these in your actual environment
            sender_email = os.environ.get('EMAIL_USER', 'your_email@example.com')
            sender_password = os.environ.get('EMAIL_PASSWORD', 'your_email_password')

            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = "InvestiBuddy - Verify Your Account"

            # Email body
            body = f"""
            Welcome to InvestiBuddy!

            Your verification code is: {verification_code}

            Please enter this code to complete your registration.

            Thank you,
            The InvestiBuddy Team
            """

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def register_user(self, username: str, email: str, password: str, risk_tolerance: str) -> Tuple[bool, str, str]:
        """Register a new user with email verification"""

        # Check if username or email already exists
        result = self.db_manager.execute_query(
            "SELECT user_id FROM users WHERE username = ? OR email = ?",
            (username, email))

        if result:
            return False, "Username or email already exists", ""

        # Validate email format
        if not self.is_valid_email(email):
            return False, "Invalid email format", ""

        # Check password strength
        is_strong, message = self.is_strong_password(password)
        if not is_strong:
            return False, message, ""

        # Generate verification code
        verification_code = self.generate_verification_code()

        try:
            # Insert new user with verification code
            self.db_manager.execute_action(
                "INSERT INTO users (username, email, password, risk_tolerance, verification_code, verified) VALUES (?, ?, ?, ?, ?, 0)",
                (username, email, password, risk_tolerance, verification_code))

            # Send verification email
            email_sent = self.send_verification_email(email, verification_code)
            if not email_sent:
                return True, "Registration successful but failed to send verification email. Please contact support.", verification_code

            return True, "Registration successful! Please check your email for verification code.", verification_code
        except Exception:
            return False, "An error occurred during registration", ""

    def verify_user(self, email: str, verification_code: str) -> bool:
        """Verify user with 2FA code"""
        result = self.db_manager.execute_query(
            "SELECT user_id FROM users WHERE email = ? AND verification_code = ?",
            (email, verification_code))

        if result:
            # Update user to verified status
            self.db_manager.execute_action(
                "UPDATE users SET verified = 1 WHERE email = ?",
                (email,))
            return True
        return False

    def login_user(self, email: str, password: str) -> Optional[Tuple[int, str]]:
        """Login user with email and password"""
        result = self.db_manager.execute_query(
            "SELECT user_id, username, verified FROM users WHERE email = ? AND password = ?",
            (email, password))

        if not result:
            return None

        user_id, username, verified = result[0]

        # Check if user is verified
        if not verified:
            return None

        return user_id, username

    def get_user_risk_tolerance(self, user_id: int) -> str:
        result = self.db_manager.execute_query(
            "SELECT risk_tolerance FROM users WHERE user_id = ?", (user_id,))
        return result[0][0] if result else "Low"

    def update_risk_tolerance(self, user_id: int, new_risk: str) -> None:
        self.db_manager.execute_action(
            "UPDATE users SET risk_tolerance = ? WHERE user_id = ?",
            (new_risk, user_id))

    def get_user_by_email(self, email: str):
        """Get user by email address"""
        result = self.db_manager.execute_query(
            "SELECT user_id, username, email FROM users WHERE email = ?",
            (email,))

        return result[0] if result else None

    def save_reset_token(self, email: str, token: str, expiration: datetime) -> bool:
        """Save password reset token in the database"""
        try:
            # First, check if a token already exists for this user and delete it
            self.db_manager.execute_action(
                "DELETE FROM password_reset_tokens WHERE email = ?",
                (email,))

            # Insert the new token
            self.db_manager.execute_action(
                "INSERT INTO password_reset_tokens (email, token, expiration) VALUES (?, ?, ?)",
                (email, token, expiration.strftime('%Y-%m-%d %H:%M:%S')))

            return True
        except Exception as e:
            print(f"Error saving reset token: {e}")
            return False

    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify that a reset token is valid and not expired"""
        result = self.db_manager.execute_query(
            "SELECT email, expiration FROM password_reset_tokens WHERE token = ?",
            (token,))

        if not result:
            return None

        email, expiration_str = result[0]
        expiration = datetime.strptime(expiration_str, '%Y-%m-%d %H:%M:%S')

        # Check if token is expired
        if datetime.now() > expiration:
            # Delete expired token
            self.db_manager.execute_action(
                "DELETE FROM password_reset_tokens WHERE token = ?",
                (token,))
            return None

        return email

    def update_password(self, email: str, new_password: str) -> bool:
        """Update user password"""
        try:
            self.db_manager.execute_action(
                "UPDATE users SET password = ? WHERE email = ?",
                (new_password, email))

            # Remove the reset token after successful password update
            self.db_manager.execute_action(
                "DELETE FROM password_reset_tokens WHERE email = ?",
                (email,))

            return True
        except Exception as e:
            print(f"Error updating password: {e}")
            return False

    def send_password_reset_email(self, email: str, reset_link: str) -> bool:
        """Send password reset email with link"""
        try:
            # Get email credentials from environment variables
            sender_email = os.environ.get('EMAIL_USER')
            sender_password = os.environ.get('EMAIL_PASSWORD')

            # Check if email credentials are set
            if not sender_email or not sender_password:
                print("Warning: EMAIL_USER or EMAIL_PASSWORD environment variables not set!")
                print(f"Would send reset link to {email}: {reset_link}")
                return False

            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = "InvestiBuddy - Password Reset Request"

            # Email body
            body = f"""
            Hello,

            You recently requested to reset your password for your InvestiBuddy account.
            Click the link below to reset your password:

            {reset_link}

            This link will expire in 1 hour.

            If you did not request a password reset, please ignore this email or contact support if you have concerns.

            Thank you,
            The InvestiBuddy Team
            """

            msg.attach(MIMEText(body, 'plain'))

            # Print details for debugging
            print(f"Sending password reset email to: {email}")
            print(f"Reset link: {reset_link}")

            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False