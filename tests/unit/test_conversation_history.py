#!/usr/bin/env python3
"""
Unit tests for conversation history functionality in the landuse agent.
"""

import os
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from landuse.agents import LanduseAgent
from landuse.core.app_config import AppConfig


class TestConversationHistory:
    """Test conversation history functionality."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent instance with mocked dependencies."""
        # Create a mock database
        db_path = tmp_path / "test.duckdb"
        import duckdb

        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        # Create config with proper API key
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            config = AppConfig(database={"path": str(db_path)})

            with patch("landuse.agents.llm_manager.ChatOpenAI") as mock_llm:
                mock_llm_instance = Mock()
                mock_llm.return_value = mock_llm_instance
                agent = LanduseAgent(config)
                agent._test_llm = mock_llm_instance  # Store for test access
                return agent

    def test_initial_empty_history(self, agent):
        """Test that conversation history starts empty."""
        assert agent.conversation_manager.conversation_history == []
        assert agent.conversation_manager.max_history_length == 20

    def test_update_conversation_history(self, agent):
        """Test updating conversation history."""
        agent.conversation_manager.add_conversation("Hello", "Hi there!")

        assert len(agent.conversation_manager.conversation_history) == 2
        assert agent.conversation_manager.conversation_history[0] == ("user", "Hello")
        assert agent.conversation_manager.conversation_history[1] == ("assistant", "Hi there!")

    def test_history_included_in_simple_query(self, agent):
        """Test that history is included in simple queries when enabled."""
        # Add some history
        agent.conversation_manager.add_conversation("What is forest land?", "Forest land is...")

        # Mock the LLM response with proper AIMessage (not Mock)
        mock_response = AIMessage(content="Based on our previous discussion about forest land...")

        agent._test_llm.bind_tools.return_value.invoke.return_value = mock_response

        # Mock _get_conversation_manager to return the default conversation manager
        # (since simple_query uses thread-isolated managers by design)
        with patch.object(agent, "_get_conversation_manager", return_value=agent.conversation_manager):
            with patch.object(agent.conversation_manager, "add_conversation"):
                # Run a follow-up query with history enabled
                response = agent.simple_query("Tell me more about that", thread_id="test", include_history=True)

        # Check that the LLM was called with history
        call_args = agent._test_llm.bind_tools.return_value.invoke.call_args
        messages = call_args[0][0]

        # Should have: system prompt, previous user, previous assistant, current user
        assert len(messages) >= 4
        assert any("What is forest land?" in str(msg.content) for msg in messages if isinstance(msg, HumanMessage))
        assert any("Forest land is..." in str(msg.content) for msg in messages if isinstance(msg, AIMessage))
        assert any("Tell me more about that" in str(msg.content) for msg in messages if isinstance(msg, HumanMessage))

    def test_history_trimming(self, agent):
        """Test that history is trimmed when it gets too long."""
        # Set a small max history for testing
        agent.conversation_manager.max_history_length = 4

        # Add more messages than the limit
        for i in range(10):
            agent.conversation_manager.add_conversation(f"Question {i}", f"Answer {i}")

        # Should only have the last 4 messages (2 Q&A pairs)
        assert len(agent.conversation_manager.conversation_history) == 4
        assert agent.conversation_manager.conversation_history[0] == ("user", "Question 8")
        assert agent.conversation_manager.conversation_history[1] == ("assistant", "Answer 8")
        assert agent.conversation_manager.conversation_history[2] == ("user", "Question 9")
        assert agent.conversation_manager.conversation_history[3] == ("assistant", "Answer 9")

    def test_clear_history(self, agent):
        """Test clearing conversation history."""
        # Add some history
        agent.conversation_manager.add_conversation("Hello", "Hi!")
        agent.conversation_manager.add_conversation("How are you?", "I'm doing well!")

        assert len(agent.conversation_manager.conversation_history) == 4

        # Clear history
        agent.clear_history()

        assert agent.conversation_manager.conversation_history == []

    def test_history_persists_across_queries(self, agent):
        """Test that history persists across multiple queries when enabled."""
        # Mock responses with proper AIMessage objects (not Mock)
        responses = [
            AIMessage(content="Texas has large forest areas."),
            AIMessage(content="California has even more forest area than Texas."),
        ]

        agent._test_llm.bind_tools.return_value.invoke.side_effect = responses

        # Mock _get_conversation_manager to return the default conversation manager
        with patch.object(agent, "_get_conversation_manager", return_value=agent.conversation_manager):
            # First query - use include_history=True to enable history tracking
            response1 = agent.query("Tell me about Texas forests", use_graph=False,
                                   include_history=True, thread_id="test")
            assert "Texas" in response1

            # Check history was updated
            assert len(agent.conversation_manager.conversation_history) == 2
            assert agent.conversation_manager.conversation_history[0] == ("user", "Tell me about Texas forests")
            assert "Texas" in agent.conversation_manager.conversation_history[1][1]

            # Second query - should have context
            response2 = agent.query("How about California?", use_graph=False,
                                   include_history=True, thread_id="test")
            assert "California" in response2

            # Check history now has both conversations
            assert len(agent.conversation_manager.conversation_history) == 4
            assert agent.conversation_manager.conversation_history[2] == ("user", "How about California?")
            assert "California" in agent.conversation_manager.conversation_history[3][1]

    def test_graph_query_includes_history(self, agent):
        """Test that graph queries also include conversation history."""
        # Add some history
        agent.conversation_manager.add_conversation("What are scenarios?", "Scenarios are...")

        # Build the graph
        agent.graph = agent.graph_builder.build_graph()

        # Mock graph invoke with proper AIMessage (not Mock)
        mock_result = {"messages": [AIMessage(content="Based on the scenarios we discussed...")]}

        with patch.object(agent.graph, "invoke", return_value=mock_result) as mock_invoke:
            response = agent._graph_query("Tell me more about RCP scenarios")

            # Check that initial state included history
            call_args = mock_invoke.call_args
            initial_state = call_args[0][0]
            messages = initial_state["messages"]

            # Should include history
            assert any("What are scenarios?" in str(msg.content) for msg in messages if isinstance(msg, HumanMessage))
            assert any("Scenarios are..." in str(msg.content) for msg in messages if isinstance(msg, AIMessage))

    def test_error_updates_history(self, agent):
        """Test that errors still update conversation history when enabled."""
        # Mock an error
        agent._test_llm.bind_tools.return_value.invoke.side_effect = Exception("Test error")

        # Mock _get_conversation_manager to return the default conversation manager
        with patch.object(agent, "_get_conversation_manager", return_value=agent.conversation_manager):
            # Query should fail but still update history - enable history tracking
            response = agent.query("This will fail", use_graph=False,
                                  include_history=True, thread_id="test")

        assert "error" in response.lower()
        assert len(agent.conversation_manager.conversation_history) == 2
        assert agent.conversation_manager.conversation_history[0] == ("user", "This will fail")
        assert "error" in agent.conversation_manager.conversation_history[1][1].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
