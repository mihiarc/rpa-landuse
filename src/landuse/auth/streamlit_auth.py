"""
Streamlit Authentication Module
Simple password-based authentication for the Land Use Analytics application
"""

import streamlit as st
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional

# Try to import the SecurityLogger if available
try:
    from landuse.infrastructure.security import SecurityLogger
    SECURITY_LOGGER_AVAILABLE = True
except ImportError:
    # Fallback if SecurityLogger is not available
    SECURITY_LOGGER_AVAILABLE = False
    print("DEBUG: SecurityLogger not available, using basic logging")


class StreamlitAuth:
    """Simple password-based authentication for Streamlit applications"""
    
    def __init__(self):
        """Initialize the authentication system"""
        if SECURITY_LOGGER_AVAILABLE:
            try:
                self.security_logger = SecurityLogger()
            except Exception as e:
                print(f"DEBUG: Could not initialize SecurityLogger: {e}")
                self.security_logger = None
        else:
            self.security_logger = None
        
        # No persistent storage needed - using only Streamlit session state
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using SHA256
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hexadecimal string of SHA256 hash
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain text password to verify
            hashed: Stored password hash
            
        Returns:
            True if password matches hash
        """
        return self.hash_password(password) == hashed
    
    def generate_session_token(self) -> str:
        """
        Generate secure session token
        
        Returns:
            URL-safe random token string
        """
        return secrets.token_urlsafe(32)
    
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated
        
        Returns:
            True if user has valid authentication session
        """
        # Only check session state - no persistent storage
        # This ensures each browser tab has independent sessions
        return st.session_state.get('authenticated', False)
    
    def get_stored_password_hash(self) -> Optional[str]:
        """
        Get the stored password hash from Streamlit secrets or environment
        
        Returns:
            Password hash if found, None otherwise
        """
        # Try Streamlit secrets first
        try:
            if hasattr(st, 'secrets') and 'auth' in st.secrets:
                return st.secrets.auth.get('password_hash')
        except Exception:
            pass
        
        # Try environment variable
        import os
        return os.getenv('STREAMLIT_AUTH_PASSWORD_HASH')
    
    def authenticate(self, password: str) -> bool:
        """
        Authenticate user with password
        
        Args:
            password: Password to authenticate with
            
        Returns:
            True if authentication successful
        """
        stored_hash = self.get_stored_password_hash()
        
        if not stored_hash:
            print("DEBUG: No password hash configured")
            if self.security_logger:
                self.security_logger.log_access(
                    user_id="unknown",
                    resource="streamlit_app",
                    action="login_attempt",
                    result="no_password_configured"
                )
            return False
        
        if self.verify_password(password, stored_hash):
            # Authentication successful - only set session state
            st.session_state.authenticated = True
            st.session_state.session_token = self.generate_session_token()
            st.session_state.auth_time = datetime.now()
            
            if self.security_logger:
                self.security_logger.log_access(
                    user_id="authenticated_user",
                    resource="streamlit_app",
                    action="login",
                    result="success"
                )
            
            return True
        
        # Authentication failed
        if self.security_logger:
            self.security_logger.log_access(
                user_id="unknown",
                resource="streamlit_app",
                action="login",
                result="failure"
            )
        
        return False
    
    def logout(self):
        """Log out user and clear session"""
        # Log the logout event if possible
        if self.security_logger and self.is_authenticated():
            self.security_logger.log_access(
                user_id="authenticated_user",
                resource="streamlit_app",
                action="logout",
                result="success"
            )
        
        # Clear authentication state - no persistent storage
        st.session_state.authenticated = False
        if 'session_token' in st.session_state:
            del st.session_state.session_token
        if 'auth_time' in st.session_state:
            del st.session_state.auth_time
    
    def check_session_timeout(self, timeout_hours: int = 8) -> bool:
        """
        Check if session has timed out
        
        Args:
            timeout_hours: Number of hours before session expires
            
        Returns:
            True if session is valid, False if timed out
        """
        if not self.is_authenticated():
            return False
        
        auth_time = st.session_state.get('auth_time')
        if not auth_time:
            return False
        
        if datetime.now() - auth_time > timedelta(hours=timeout_hours):
            # Session expired
            self.logout()
            return False
        
        return True
    



def generate_password_hash(password: str) -> str:
    """
    Utility function to generate password hash for configuration
    
    Args:
        password: Plain text password
        
    Returns:
        SHA256 hash of password
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


if __name__ == "__main__":
    # Utility for generating password hashes
    import sys
    
    if len(sys.argv) > 1:
        password = sys.argv[1]
        hash_value = generate_password_hash(password)
        print(f"Password hash for '{password}': {hash_value}")
    else:
        print("Usage: python streamlit_auth.py <password>")
        print("This will generate a SHA256 hash for the password to use in configuration")
