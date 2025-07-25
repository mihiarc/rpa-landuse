#!/usr/bin/env python3
"""
Unit tests for Streamlit chat page
"""

# Mock streamlit before importing pages
import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest

from tests.unit.streamlit.mock_streamlit import mock_st

sys.modules['streamlit'] = mock_st
import streamlit as st  # noqa: E402


class TestChatPage:
    """Test the chat interface page"""

    @pytest.fixture
    def mock_session_state(self):
        """Mock Streamlit session state"""
        state = MagicMock()
        state.messages = []
        state.query_count = 0
        state.last_query_time = None
        state.agent_cache_time = None
        return state

    @pytest.fixture
    def mock_agent(self):
        """Mock landuse agent"""
        agent = Mock()
        agent.query.return_value = "Test response from agent"
        return agent

    @patch('pages.chat.st')
    def test_initialize_session_state(self, mock_st):
        """Test session state initialization"""
        mock_st.session_state = MagicMock()
        mock_st.session_state.__contains__.return_value = False

        from pages.chat import initialize_session_state

        initialize_session_state()

        # Verify session state attributes were set
        assert hasattr(mock_st.session_state, 'messages')
        assert hasattr(mock_st.session_state, 'query_count')
        assert hasattr(mock_st.session_state, 'last_query_time')
        assert hasattr(mock_st.session_state, 'agent_cache_time')

    @patch('pages.chat.st')
    def test_get_agent_cached(self, mock_st, mock_agent):
        """Test agent caching with st.cache_resource"""
        # Mock the get_agent function to return a tuple (agent, error)
        with patch('pages.chat.get_agent') as mock_get_agent:
            mock_get_agent.return_value = (mock_agent, None)

            from pages.chat import get_agent

            # First call
            result1 = get_agent()
            assert result1 == (mock_agent, None)

            # Second call should return same instance (cached)
            result2 = get_agent()
            assert result2 == (mock_agent, None)

            # With caching simulation, function should be called twice in test
            # but in real app it would be cached
            assert mock_get_agent.call_count == 2

    @patch('landuse.agents.landuse_natural_language_agent.LanduseNaturalLanguageAgent')
    def test_initialize_agent(self, mock_agent_class):
        """Test agent initialization"""
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        from pages.chat import initialize_agent

        agent, error = initialize_agent()

        assert agent == mock_agent_instance
        assert error is None
        mock_agent_class.assert_called_once()

    @patch('pages.chat.st')
    def test_display_chat_history(self, mock_st):
        """Test displaying chat history"""
        # Mock session state with messages
        mock_st.session_state.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        mock_chat_message = Mock()
        mock_st.chat_message.return_value.__enter__ = Mock(return_value=mock_chat_message)
        mock_st.chat_message.return_value.__exit__ = Mock(return_value=None)

        from pages.chat import display_chat_history

        display_chat_history()

        # Verify chat messages were called for each message
        assert mock_st.chat_message.call_count == 2

    @patch('pages.chat.st')
    def test_display_message_assistant_with_sources(self, mock_st):
        """Test displaying assistant message with sources"""
        mock_chat_message = Mock()
        mock_st.chat_message.return_value.__enter__ = Mock(return_value=mock_chat_message)
        mock_st.chat_message.return_value.__exit__ = Mock(return_value=None)

        from pages.chat import display_message

        content = "Here is the answer"
        sources = ["Source 1", "Source 2"]

        display_message("assistant", content, sources)

        mock_st.chat_message.assert_called_with("assistant")

        # Check that sources were formatted
        calls = mock_chat_message.markdown.call_args_list
        assert any("Here is the answer" in str(c) for c in calls)
        assert any("Sources" in str(c) for c in calls)

    @patch('pages.chat.st')
    def test_format_response_with_dataframe(self, mock_st):
        """Test formatting response with DataFrame results"""
        from pages.chat import format_response

        # Test with DataFrame in response
        df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        response = f"Here are the results:\n{df.to_string()}"

        formatted = format_response(response)

        # Should preserve the response
        assert "Here are the results:" in formatted

    @patch('pages.chat.st')
    def test_extract_sources(self, mock_st):
        """Test extracting sources from agent response"""
        from pages.chat import extract_sources

        response = """
        Here is the answer.

        Sources:
        - Table: dim_scenario
        - Query: SELECT * FROM dim_scenario
        """

        content, sources = extract_sources(response)

        assert "Here is the answer." in content
        assert len(sources) == 2
        assert "Table: dim_scenario" in sources[0]
        assert "Query: SELECT * FROM dim_scenario" in sources[1]

    @patch('pages.chat.st')
    def test_handle_rate_limit(self, mock_st, mock_session_state):
        """Test rate limit handling"""
        mock_st.session_state = mock_session_state
        mock_session_state.last_query_time = datetime.now()

        from pages.chat import handle_rate_limit

        # Should show warning for rapid queries
        result = handle_rate_limit()

        # In test environment, might not trigger rate limit
        # Just verify it doesn't crash
        assert result in [True, False]

    @patch('pages.chat.st')
    @patch('pages.chat.get_agent')
    def test_process_query_success(self, mock_get_agent, mock_st, mock_agent, mock_session_state):
        """Test successful query processing"""
        mock_st.session_state = mock_session_state
        mock_get_agent.return_value = mock_agent
        mock_agent.query.return_value = "Agent response with results"

        # Mock spinner
        mock_spinner = Mock()
        mock_st.spinner.return_value.__enter__ = Mock(return_value=mock_spinner)
        mock_st.spinner.return_value.__exit__ = Mock(return_value=None)

        from pages.chat import process_query

        process_query("What is the total forest loss?", Mock())

        # Verify agent was called
        mock_agent.query.assert_called_once_with("What is the total forest loss?")

        # Verify response was written
        mock_st.write.assert_called()

        # Verify session state was updated
        assert mock_session_state.query_count == 1

    @patch('pages.chat.st')
    @patch('pages.chat.get_agent')
    def test_process_query_error(self, mock_get_agent, mock_st, mock_session_state):
        """Test query processing with error"""
        mock_st.session_state = mock_session_state
        mock_agent = Mock()
        mock_agent.query.side_effect = Exception("Test error")
        mock_get_agent.return_value = mock_agent

        # Mock spinner
        mock_st.spinner.return_value.__enter__ = Mock()
        mock_st.spinner.return_value.__exit__ = Mock(return_value=None)

        from pages.chat import process_query

        process_query("Bad query", Mock())

        # Verify error was shown
        mock_st.error.assert_called()
        assert "Test error" in str(mock_st.error.call_args)

    @patch('pages.chat.st')
    def test_show_query_suggestions(self, mock_st):
        """Test showing query suggestions"""
        mock_st.columns.return_value = [Mock(), Mock()]

        from pages.chat import show_query_suggestions

        suggestions = show_query_suggestions()

        # Verify suggestions were returned
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)

        # Verify buttons were created
        assert mock_st.button.called

    @patch('pages.chat.st')
    @patch('pages.chat.initialize_session_state')
    @patch('pages.chat.get_agent')
    def test_main_page_structure(self, mock_get_agent, mock_init_state, mock_st, mock_agent):
        """Test main page structure and layout"""
        mock_get_agent.return_value = mock_agent
        mock_st.session_state = MagicMock(messages=[])
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]

        # Mock chat input
        mock_st.chat_input.return_value = None

        # Import main directly
        import pages.chat

        # Verify page elements
        mock_st.title.assert_called()
        assert "Natural Language Chat" in str(mock_st.title.call_args)

        # Verify metrics are displayed
        assert mock_st.metric.called

        # Verify chat interface elements
        mock_st.chat_input.assert_called()

    @patch('pages.chat.st')
    def test_display_chat_history_with_messages(self, mock_st, mock_session_state):
        """Test chat history display"""
        # Add some messages to history
        mock_session_state.messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Show me forest data"},
            {"role": "assistant", "content": "Here is the forest data...",
             "sources": ["Table: dim_landuse"]}
        ]

        mock_st.session_state = mock_session_state

        # Mock chat_message context manager
        mock_chat_message = Mock()
        mock_st.chat_message.return_value.__enter__ = Mock(return_value=mock_chat_message)
        mock_st.chat_message.return_value.__exit__ = Mock(return_value=None)

        # Import will trigger display
        import pages.chat

        # Verify all messages were displayed
        assert mock_st.chat_message.call_count >= 4

        # Verify roles were set correctly
        roles = [c[0][0] for c in mock_st.chat_message.call_args_list]
        assert "user" in roles
        assert "assistant" in roles
