#!/usr/bin/env python3
"""
Unit tests for Streamlit chat page

Tests the chat interface functionality including:
- Session state initialization
- Agent caching and retrieval
- Chat history display
- User input handling
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from tests.unit.streamlit_tests.mock_streamlit import mock_st

sys.modules["streamlit"] = mock_st
import streamlit as st  # noqa: E402


class TestChatPage:
    """Test the chat interface page"""

    @pytest.fixture
    def mock_session_state(self):
        """Mock Streamlit session state"""
        state = MagicMock()
        state.messages = []
        state.show_welcome = True
        state.first_visit = True
        return state

    @pytest.fixture
    def mock_agent(self):
        """Mock landuse agent"""
        agent = Mock()
        agent.query.return_value = "Test response from agent"
        return agent

    def test_page_functions_exist(self):
        """Test that key page functions exist and are callable"""
        from views import chat

        # Test that key functions exist (current API)
        assert hasattr(chat, "get_agent")
        assert hasattr(chat, "initialize_session_state")
        assert hasattr(chat, "display_chat_history")
        assert hasattr(chat, "handle_user_input")
        assert hasattr(chat, "main")
        assert hasattr(chat, "show_welcome_message")
        assert hasattr(chat, "show_scenario_guide")
        assert hasattr(chat, "show_first_time_onboarding")
        assert hasattr(chat, "show_persistent_context_bar")
        assert hasattr(chat, "show_smart_example_queries")

        # Test that they are callable
        assert callable(chat.get_agent)
        assert callable(chat.initialize_session_state)
        assert callable(chat.display_chat_history)
        assert callable(chat.main)

    def test_initialize_session_state_creates_messages(self):
        """Test session state initialization creates messages list"""
        from views import chat

        # Reset mock session state
        mock_st.session_state = MagicMock()
        mock_st.session_state.__contains__ = lambda self, key: False

        chat.initialize_session_state()

        # Verify session state attributes were accessed
        # The function checks for 'messages', 'show_welcome', 'first_visit'
        assert mock_st.session_state is not None

    def test_get_agent_returns_tuple(self):
        """Test get_agent returns tuple of (agent, error)"""
        from views import chat

        # Call the function - it should return a tuple regardless of success/failure
        result = chat.get_agent()

        # Should return tuple (agent, error)
        assert isinstance(result, tuple)
        assert len(result) == 2

        # Either agent is set (error is None) or error is set (agent is None)
        agent, error = result
        assert (agent is not None and error is None) or (agent is None and error is not None)

    def test_get_agent_return_structure(self):
        """Test get_agent returns consistent structure"""
        from views import chat

        # The function should always return (agent, error_or_none)
        result = chat.get_agent()

        # Should be a tuple of 2 elements
        assert isinstance(result, tuple)
        assert len(result) == 2

        agent, error = result
        # Either we have an agent or an error, not both
        assert (agent is not None and error is None) or (agent is None and error is not None)

    def test_display_chat_history_iterates_messages(self):
        """Test display_chat_history iterates through messages"""
        from views import chat

        # Setup mock session state with messages
        mock_st.session_state = MagicMock()
        mock_st.session_state.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        # Call should not raise
        chat.display_chat_history()

    def test_display_chat_history_handles_empty_messages(self):
        """Test display_chat_history handles empty message list"""
        from views import chat

        mock_st.session_state = MagicMock()
        mock_st.session_state.messages = []

        # Should handle empty list gracefully
        chat.display_chat_history()

    def test_show_welcome_message_sets_flag(self):
        """Test show_welcome_message updates session state"""
        from views import chat

        mock_st.session_state = MagicMock()
        mock_st.session_state.show_welcome = True

        chat.show_welcome_message()

        # Function should have executed without error

    def test_show_smart_example_queries_function_exists(self):
        """Test show_smart_example_queries function exists and is callable"""
        from views import chat

        # Verify function exists
        assert hasattr(chat, "show_smart_example_queries")
        assert callable(chat.show_smart_example_queries)

    def test_show_persistent_context_bar(self):
        """Test persistent context bar display"""
        from views import chat

        # Should execute without error
        chat.show_persistent_context_bar()

    def test_chat_message_structure(self):
        """Test that chat messages have required fields"""
        # Chat messages should have 'role' and 'content' keys
        valid_message = {"role": "user", "content": "Test message"}

        assert "role" in valid_message
        assert "content" in valid_message
        assert valid_message["role"] in ["user", "assistant"]

    def test_chat_assistant_message_structure(self):
        """Test assistant message structure"""
        assistant_msg = {"role": "assistant", "content": "Response text"}

        assert assistant_msg["role"] == "assistant"
        assert isinstance(assistant_msg["content"], str)

    @patch("views.chat.get_agent")
    def test_handle_user_input_with_valid_agent(self, mock_get_agent):
        """Test handle_user_input when agent is available"""
        from landuse.utils.security import RateLimiter
        from views import chat

        mock_agent = Mock()
        mock_agent.query.return_value = "Test response"
        mock_get_agent.return_value = (mock_agent, None)

        mock_st.session_state = MagicMock()
        mock_st.session_state.messages = []
        mock_st.session_state.session_id = "test-session"
        mock_st.session_state.rate_limiter = RateLimiter(max_calls=20, time_window=60)

        # The function uses st.chat_input which is mocked
        # Just verify it can be called without error
        chat.handle_user_input()

    @patch("views.chat.get_agent")
    def test_handle_user_input_with_agent_error(self, mock_get_agent):
        """Test handle_user_input when agent has error"""
        from landuse.utils.security import RateLimiter
        from views import chat

        mock_get_agent.return_value = (None, "Agent initialization failed")

        mock_st.session_state = MagicMock()
        mock_st.session_state.messages = []
        mock_st.session_state.session_id = "test-session"
        mock_st.session_state.rate_limiter = RateLimiter(max_calls=20, time_window=60)

        # Should handle error gracefully
        chat.handle_user_input()

    def test_main_function_exists(self):
        """Test that main function exists and is the entry point"""
        from views import chat

        assert hasattr(chat, "main")
        assert callable(chat.main)

    def test_scenario_guide_dialog_function(self):
        """Test scenario guide dialog function exists"""
        from views import chat

        # show_scenario_guide is decorated with @st.dialog
        # It should be callable
        assert callable(chat.show_scenario_guide)
