#!/usr/bin/env python3
"""
Unit tests for conversation history functionality in the landuse agent.
"""

import pytest
from unittest.mock import Mock, patch
import os

from landuse.agents import LanduseAgent
from landuse.config.landuse_config import LanduseConfig
from langchain_core.messages import HumanMessage, AIMessage


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
        
        # Skip validation in test
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(db_path=str(db_path))
            
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('landuse.agents.landuse_agent.ChatOpenAI') as mock_llm:
                mock_llm_instance = Mock()
                mock_llm.return_value = mock_llm_instance
                agent = LanduseAgent(config)
                agent._test_llm = mock_llm_instance  # Store for test access
                return agent
    
    def test_initial_empty_history(self, agent):
        """Test that conversation history starts empty."""
        assert agent.conversation_history == []
        assert agent.max_history_length == 20
    
    def test_update_conversation_history(self, agent):
        """Test updating conversation history."""
        agent._update_conversation_history("Hello", "Hi there!")
        
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0] == ("user", "Hello")
        assert agent.conversation_history[1] == ("assistant", "Hi there!")
    
    def test_history_included_in_simple_query(self, agent):
        """Test that history is included in simple queries."""
        # Add some history
        agent._update_conversation_history("What is forest land?", "Forest land is...")
        
        # Mock the LLM response
        mock_response = Mock()
        mock_response.tool_calls = []
        mock_response.content = "Based on our previous discussion about forest land..."
        
        agent._test_llm.bind_tools.return_value.invoke.return_value = mock_response
        
        # Run a follow-up query
        with patch.object(agent, '_update_conversation_history'):
            response = agent.simple_query("Tell me more about that")
        
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
        agent.max_history_length = 4
        
        # Add more messages than the limit
        for i in range(10):
            agent._update_conversation_history(f"Question {i}", f"Answer {i}")
        
        # Should only have the last 4 messages (2 Q&A pairs)
        assert len(agent.conversation_history) == 4
        assert agent.conversation_history[0] == ("user", "Question 8")
        assert agent.conversation_history[1] == ("assistant", "Answer 8")
        assert agent.conversation_history[2] == ("user", "Question 9")
        assert agent.conversation_history[3] == ("assistant", "Answer 9")
    
    def test_clear_history(self, agent):
        """Test clearing conversation history."""
        # Add some history
        agent._update_conversation_history("Hello", "Hi!")
        agent._update_conversation_history("How are you?", "I'm doing well!")
        
        assert len(agent.conversation_history) == 4
        
        # Clear history
        agent.clear_history()
        
        assert agent.conversation_history == []
    
    def test_history_persists_across_queries(self, agent):
        """Test that history persists across multiple queries."""
        # Mock responses
        responses = [
            Mock(tool_calls=[], content="Texas has large forest areas."),
            Mock(tool_calls=[], content="California has even more forest area than Texas.")
        ]
        
        agent._test_llm.bind_tools.return_value.invoke.side_effect = responses
        
        # First query
        response1 = agent.query("Tell me about Texas forests")
        assert "Texas" in response1
        
        # Check history was updated
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0] == ("user", "Tell me about Texas forests")
        assert "Texas" in agent.conversation_history[1][1]
        
        # Second query - should have context
        response2 = agent.query("How about California?")
        assert "California" in response2
        
        # Check history now has both conversations
        assert len(agent.conversation_history) == 4
        assert agent.conversation_history[2] == ("user", "How about California?")
        assert "California" in agent.conversation_history[3][1]
    
    def test_graph_query_includes_history(self, agent):
        """Test that graph queries also include conversation history."""
        # Add some history
        agent._update_conversation_history("What are scenarios?", "Scenarios are...")
        
        # Build the graph
        agent.graph = agent._build_graph()
        
        # Mock graph invoke
        mock_result = {
            "messages": [
                Mock(content="Based on the scenarios we discussed...")
            ]
        }
        
        with patch.object(agent.graph, 'invoke', return_value=mock_result) as mock_invoke:
            response = agent._graph_query("Tell me more about RCP scenarios")
            
            # Check that initial state included history
            call_args = mock_invoke.call_args
            initial_state = call_args[0][0]
            messages = initial_state["messages"]
            
            # Should include history
            assert any("What are scenarios?" in str(msg.content) for msg in messages if isinstance(msg, HumanMessage))
            assert any("Scenarios are..." in str(msg.content) for msg in messages if isinstance(msg, AIMessage))
    
    def test_error_updates_history(self, agent):
        """Test that errors still update conversation history."""
        # Mock an error
        agent._test_llm.bind_tools.return_value.invoke.side_effect = Exception("Test error")
        
        # Query should fail but still update history
        response = agent.query("This will fail")
        
        assert "Error processing query" in response
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0] == ("user", "This will fail")
        assert "Error" in agent.conversation_history[1][1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])