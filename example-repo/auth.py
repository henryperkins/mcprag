"""
Authentication module for the application.
"""
import hashlib
import jwt
from datetime import datetime, timedelta

class AuthManager:
    """Handles user authentication and token management."""
    
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def hash_password(self, password):
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, hashed_password):
        """Verify a password against its hash."""
        return self.hash_password(password) == hashed_password
    
    def generate_token(self, user_id, expires_in_hours=24):
        """Generate a JWT token for a user."""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token):
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

def authenticate_user(username, password, user_database):
    """Authenticate a user against the database."""
    user = user_database.get(username)
    if not user:
        return False
    
    auth_manager = AuthManager("secret_key")
    return auth_manager.verify_password(password, user['password_hash'])
