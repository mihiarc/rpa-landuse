"""
Streamlit Authentication Module
Simple password-based authentication for the Land Use Analytics application
"""

import streamlit as st
import hashlib
import secrets
import json
import os
from pathlib import Path
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
        
        # Session file path for persistent storage
        self.session_dir = Path.home() / ".streamlit" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
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
        # First check session state (fast)
        if st.session_state.get('authenticated', False):
            return True
        
        # If not in session state, try to load from persistent storage
        return self._load_persistent_session()
    
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
            # Authentication successful
            st.session_state.authenticated = True
            st.session_state.session_token = self.generate_session_token()
            st.session_state.auth_time = datetime.now()
            
            # Save to persistent storage
            self._save_persistent_session()
            
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
        
        # Clear authentication state
        st.session_state.authenticated = False
        if 'session_token' in st.session_state:
            del st.session_state.session_token
        if 'auth_time' in st.session_state:
            del st.session_state.auth_time
        
        # Clear persistent storage
        self._clear_persistent_session()
    
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
    
    def _get_session_file_path(self) -> Path:
        """Get the path to the session file for this browser session"""
        # Use a simple session file approach
        # This creates one session per machine/user - works for single-user apps
        return self.session_dir / "auth_session.json"
    
    def _save_persistent_session(self):
        """Save authentication session to persistent storage"""
        try:
            session_data = {
                'authenticated': st.session_state.get('authenticated', False),
                'session_token': st.session_state.get('session_token'),
                'auth_time': st.session_state.get('auth_time').isoformat() if st.session_state.get('auth_time') else None
            }
            
            session_file = self._get_session_file_path()
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
                
        except Exception as e:
            print(f"DEBUG: Could not save persistent session: {e}")
    
    def _load_persistent_session(self) -> bool:
        """Load authentication session from persistent storage"""
        try:
            session_file = self._get_session_file_path()
            if not session_file.exists():
                return False
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session is still valid
            if not session_data.get('authenticated', False):
                return False
            
            auth_time_str = session_data.get('auth_time')
            if not auth_time_str:
                return False
            
            auth_time = datetime.fromisoformat(auth_time_str)
            
            # Check timeout (8 hours default)
            timeout_hours = self._get_timeout_hours()
            if datetime.now() - auth_time > timedelta(hours=timeout_hours):
                # Session expired, clean up
                self._clear_persistent_session()
                return False
            
            # Restore session state
            st.session_state.authenticated = session_data['authenticated']
            st.session_state.session_token = session_data['session_token']
            st.session_state.auth_time = auth_time
            
            return True
            
        except Exception as e:
            print(f"DEBUG: Could not load persistent session: {e}")
            return False
    
    def _clear_persistent_session(self):
        """Clear persistent session storage"""
        try:
            session_file = self._get_session_file_path()
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            print(f"DEBUG: Could not clear persistent session: {e}")
    
    def _get_timeout_hours(self) -> int:
        """Get session timeout from configuration"""
        # Try Streamlit secrets first
        try:
            if hasattr(st, 'secrets') and 'auth' in st.secrets:
                return int(st.secrets.auth.get('timeout_hours', 8))
        except Exception:
            pass
        
        # Try environment variable
        try:
            return int(os.getenv('STREAMLIT_AUTH_TIMEOUT_HOURS', '8'))
        except ValueError:
            return 8


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
