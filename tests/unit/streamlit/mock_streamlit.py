#!/usr/bin/env python3
"""
Mock Streamlit module for testing
Provides mock implementations of Streamlit decorators and functions
"""

from unittest.mock import Mock
from functools import wraps
import types


def cache_resource(func=None, *, ttl=None, max_entries=None, show_spinner=True, validate=None):
    """Mock implementation of st.cache_resource decorator"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def cache_data(func=None, *, ttl=None, max_entries=None, show_spinner=True, persist=None):
    """Mock implementation of st.cache_data decorator"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def fragment(func=None):
    """Mock implementation of st.fragment decorator"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


# Create mock streamlit module as a proper module
mock_st = types.ModuleType('streamlit')
mock_st.__file__ = __file__
mock_st.cache_resource = cache_resource
mock_st.cache_data = cache_data
mock_st.fragment = fragment

# Add common Streamlit functions
mock_st.title = Mock()
mock_st.markdown = Mock()
mock_st.write = Mock()
mock_st.header = Mock()
mock_st.subheader = Mock()
mock_st.text = Mock()
mock_st.code = Mock()
mock_st.info = Mock()
mock_st.warning = Mock()
mock_st.error = Mock()
mock_st.success = Mock()
mock_st.empty = Mock()
mock_st.json = Mock()
mock_st.dataframe = Mock()
mock_st.table = Mock()
mock_st.metric = Mock()
mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock()])
mock_st.container = Mock()
mock_st.expander = Mock()
mock_st.spinner = Mock()
mock_st.progress = Mock()
mock_st.balloons = Mock()
mock_st.snow = Mock()
mock_st.button = Mock(return_value=False)
mock_st.download_button = Mock(return_value=False)
mock_st.checkbox = Mock(return_value=False)
mock_st.radio = Mock()
mock_st.selectbox = Mock()
mock_st.multiselect = Mock(return_value=[])
mock_st.slider = Mock()
mock_st.select_slider = Mock()
mock_st.text_input = Mock(return_value="")
mock_st.number_input = Mock(return_value=0)
mock_st.text_area = Mock(return_value="")
mock_st.date_input = Mock()
mock_st.time_input = Mock()
mock_st.file_uploader = Mock()
mock_st.color_picker = Mock()
mock_st.image = Mock()
mock_st.audio = Mock()
mock_st.video = Mock()
mock_st.plotly_chart = Mock()
mock_st.pyplot = Mock()
mock_st.altair_chart = Mock()
mock_st.graphviz_chart = Mock()
mock_st.map = Mock()
mock_st.sidebar = Mock()
mock_st.echo = Mock()
mock_st.form = Mock()
mock_st.form_submit_button = Mock(return_value=False)
mock_st.tabs = Mock(return_value=[Mock(), Mock(), Mock()])
mock_st.chat_input = Mock()
mock_st.chat_message = Mock()
mock_st.status = Mock()
mock_st.toast = Mock()
mock_st.connection = Mock()

# Session state mock
class SessionState:
    def __init__(self):
        self._state = {}
    
    def __getattr__(self, name):
        return self._state.get(name, None)
    
    def __setattr__(self, name, value):
        if name == '_state':
            super().__setattr__(name, value)
        else:
            self._state[name] = value
    
    def __contains__(self, key):
        return key in self._state
    
    def get(self, key, default=None):
        return self._state.get(key, default)

mock_st.session_state = SessionState()

# Experimental features
mock_st.experimental_rerun = Mock()
mock_st.experimental_memo = Mock()
mock_st.experimental_singleton = Mock()

# Context managers
class MockContainer:
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def __getattr__(self, name):
        return Mock()

mock_st.container.return_value = MockContainer()
mock_st.spinner.return_value = MockContainer()
mock_st.form.return_value = MockContainer()
mock_st.expander.return_value = MockContainer()
mock_st.echo.return_value = MockContainer()
mock_st.chat_message.return_value = MockContainer()
mock_st.status.return_value = MockContainer()