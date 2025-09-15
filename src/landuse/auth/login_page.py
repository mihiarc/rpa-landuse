"""
Login Page Component for Streamlit Land Use Analytics
Provides login form and authentication checking functionality
"""

import streamlit as st
from datetime import datetime
from .streamlit_auth import StreamlitAuth


def login_form():
    """
    Display login form using Streamlit fragment for better performance
    """
    auth = StreamlitAuth()
    
    # Create centered login container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Title and description
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1>🔐 Authentication Required</h1>
            <p style='color: #666; font-size: 1.1rem;'>
                Please enter your password to access the application
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### Login")
            
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
                placeholder="Enter your password",
                help="Contact your administrator if you don't have the password"
            )
            
            col_login, col_info = st.columns([1, 1])
            
            with col_login:
                submit = st.form_submit_button(
                    "🔑 Login", 
                    use_container_width=True,
                    type="primary"
                )
            
            with col_info:
                if st.form_submit_button("ℹ️ Help", use_container_width=True):
                    st.info("""
                    **Need help accessing the application?**
                    
                    - Contact your system administrator for the password
                    - Session persists across page refreshes (stored locally)
                    - Sessions automatically expire after 8 hours of inactivity
                    - Try refreshing the page if you're experiencing issues
                    """)
            
            # Handle form submission
            if submit:
                if password:
                    if auth.authenticate(password):
                        st.success("✅ Authentication successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid password. Please try again.")
                else:
                    st.warning("⚠️ Please enter a password.")
        


def require_authentication() -> bool:
    """
    Check authentication and show login if needed
    
    Returns:
        bool: True if user is authenticated, False if login form is shown
    """
    auth = StreamlitAuth()
    
    # Check if already authenticated
    if not auth.is_authenticated():
        login_form()
        return False
    
    # Check session timeout
    timeout_hours = _get_timeout_hours()
    if not auth.check_session_timeout(timeout_hours):
        st.warning(f"🕒 Session expired after {timeout_hours} hours of inactivity. Please log in again.")
        login_form()
        return False
    
    return True


def show_logout_button(location: str = "sidebar"):
    """
    Show logout button in specified location
    
    Args:
        location: Where to show the button ("sidebar", "main", or "header")
    """
    auth = StreamlitAuth()
    
    if not auth.is_authenticated():
        return
    
    # Show auth info and logout button based on location
    if location == "sidebar":
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 Authentication")
            
            # Show session info
            auth_time = st.session_state.get('auth_time')
            if auth_time:
                time_str = auth_time.strftime("%H:%M")
                st.caption(f"Logged in at {time_str}")
            
            # Logout button
            if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
                auth.logout()
                st.success("✅ Logged out successfully!")
                st.rerun()
                
    elif location == "main":
        col1, col2, col3 = st.columns([6, 1, 1])
        with col3:
            if st.button("🚪 Logout", key="main_logout"):
                auth.logout()
                st.success("✅ Logged out successfully!")
                st.rerun()
                
    elif location == "header":
        # Create a header container
        header_container = st.container()
        with header_container:
            col1, col2 = st.columns([8, 1])
            with col2:
                if st.button("🚪 Logout", key="header_logout"):
                    auth.logout()
                    st.success("✅ Logged out successfully!")
                    st.rerun()


def _get_timeout_hours() -> int:
    """
    Get session timeout from configuration
    
    Returns:
        int: Timeout in hours (default 8)
    """
    # Try Streamlit secrets first
    try:
        if hasattr(st, 'secrets') and 'auth' in st.secrets:
            return int(st.secrets.auth.get('timeout_hours', 8))
    except Exception:
        pass
    
    # Try environment variable
    import os
    try:
        return int(os.getenv('STREAMLIT_AUTH_TIMEOUT_HOURS', '8'))
    except ValueError:
        return 8


@st.fragment
def authentication_status_widget():
    """
    Show current authentication status (can be used in sidebar)
    """
    auth = StreamlitAuth()
    
    if auth.is_authenticated():
        st.success("🔐 Authenticated")
        
        auth_time = st.session_state.get('auth_time')
        if auth_time:
            elapsed = datetime.now() - auth_time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            
            if hours > 0:
                st.caption(f"Session: {hours}h {minutes}m")
            else:
                st.caption(f"Session: {minutes}m")
    else:
        st.error("🔒 Not authenticated")


def check_configuration() -> dict:
    """
    Check if authentication is properly configured
    
    Returns:
        dict: Configuration status information
    """
    auth = StreamlitAuth()
    status = {
        'configured': False,
        'password_hash_found': False,
        'timeout_configured': False,
        'security_logger_available': False,
        'messages': []
    }
    
    # Check password hash
    password_hash = auth.get_stored_password_hash()
    if password_hash:
        status['password_hash_found'] = True
        status['messages'].append("✅ Password hash found in configuration")
    else:
        status['messages'].append("❌ No password hash configured")
    
    # Check timeout configuration
    timeout_hours = _get_timeout_hours()
    status['timeout_configured'] = True
    status['messages'].append(f"⏱️ Session timeout: {timeout_hours} hours")
    
    # Check security logger
    if auth.security_logger:
        status['security_logger_available'] = True
        status['messages'].append("✅ Security logging available")
    else:
        status['messages'].append("⚠️ Security logging not available")
    
    # Overall status
    status['configured'] = status['password_hash_found']
    
    return status


if __name__ == "__main__":
    # For testing the login form standalone
    st.set_page_config(
        page_title="Authentication Test",
        page_icon="🔐",
        layout="centered"
    )
    
    st.title("Authentication Test")
    
    if require_authentication():
        st.success("🎉 Authentication successful!")
        show_logout_button("main")
        
        with st.expander("Configuration Status"):
            config_status = check_configuration()
            for message in config_status['messages']:
                st.write(message)
