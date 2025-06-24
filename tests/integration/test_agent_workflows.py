"""
Integration tests for agent workflows and interactions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pandas as pd
import duckdb
import sqlite3
import json
import time
from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
from landuse.agents.general_data_agent import GeneralDataAgent
from landuse.agents.secure_landuse_agent import SecureLanduseAgent
from tests.fixtures.agent_fixtures import *


class TestCrossAgentWorkflows:
    """Test workflows that might involve multiple agents"""
    
    @pytest.mark.integration
    def test_data_pipeline_workflow(self, tmp_path, test_database):
        """Test a complete data pipeline workflow"""
        # Step 1: Use general agent to prepare data
        csv_data = pd.DataFrame({
            "county_fips": ["01001", "01003", "06001"],
            "land_type": ["crop", "forest", "urban"],
            "acres": [1000, 2000, 500]
        })
        csv_path = tmp_path / "new_data.csv"
        csv_data.to_csv(csv_path, index=False)
        
        with patch('scripts.agents.general_data_agent.ChatOpenAI'):
            with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
                general_agent = GeneralDataAgent(root_dir=str(tmp_path))
                
                # Analyze the CSV
                analysis = general_agent._analyze_dataframe(str(csv_path))
                # Check that analysis contains expected shape info
                assert '"shape": [' in analysis or "3, 3" in analysis
                assert "county_fips" in analysis
        
        # Step 2: Query existing database with landuse agent
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic'):
            landuse_agent = LanduseNaturalLanguageAgent(str(test_database))
            
            # Execute a query
            result = landuse_agent._execute_landuse_query(
                "SELECT COUNT(*) as count FROM dim_scenario"
            )
            assert "count" in result.lower()
    
    @pytest.mark.integration
    def test_secure_vs_regular_agent_comparison(self, test_database, monkeypatch):
        """Compare behavior of secure vs regular agent"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        # Regular agent
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic') as mock_anthropic:
            mock_llm = Mock()
            mock_anthropic.return_value = mock_llm
            regular_agent = LanduseNaturalLanguageAgent(str(test_database))
            
            # Should execute any query
            result = regular_agent._execute_landuse_query("SELECT * FROM dim_scenario")
            assert "Query Results" in result
        
        # Secure agent
        with patch('scripts.agents.secure_landuse_agent.ChatAnthropic') as mock_anthropic:
            mock_llm = Mock()
            mock_anthropic.return_value = mock_llm
            secure_agent = SecureLanduseAgent()
            
            # Should block dangerous queries
            result = secure_agent._execute_secure_landuse_query("DROP TABLE dim_scenario")
            assert "Security Error" in result
            
            # Should allow safe queries
            result = secure_agent._execute_secure_landuse_query("SELECT * FROM dim_scenario")
            assert "Query Results" in result or "Error" not in result


class TestAgentNLPCapabilities:
    """Test natural language processing capabilities across agents"""
    
    @pytest.mark.integration
    def test_landuse_nlp_variations(self, test_database):
        """Test various natural language query variations"""
        queries_and_expectations = [
            ("Show me agricultural land", ["Agriculture", "Crop", "Pasture"]),
            ("forest changes over time", ["Forest", "time", "year"]),
            ("urban growth patterns", ["Urban", "growth", "expansion"]),
            ("climate scenario comparison", ["scenario", "RCP", "SSP"]),
            ("midwest states analysis", ["state", "midwest", "geographic"])
        ]
        
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic') as mock_anthropic:
            # Mock LLM to return contextually appropriate SQL
            def mock_invoke(prompt_dict):
                query = prompt_dict.get("input", "")
                if "agricultural" in query.lower():
                    return Mock(content="SELECT * FROM fact_landuse_transitions WHERE from_landuse_id IN (1,2)")
                elif "forest" in query.lower():
                    return Mock(content="SELECT * FROM fact_landuse_transitions WHERE from_landuse_id = 3")
                else:
                    return Mock(content="SELECT * FROM fact_landuse_transitions LIMIT 10")
            
            mock_llm = Mock()
            mock_llm.invoke.side_effect = mock_invoke
            mock_anthropic.return_value = mock_llm
            
            agent = LanduseNaturalLanguageAgent(str(test_database))
            
            for nl_query, expected_terms in queries_and_expectations:
                # Mock the agent executor
                agent.agent = Mock()
                agent.agent.invoke.return_value = {
                    "output": f"Analysis of {nl_query} showing relevant results"
                }
                
                response = agent.query(nl_query)
                # Check that response contains analysis or expected terms
                assert "analysis" in response.lower() or any(term.lower() in response.lower() for term in expected_terms)
    
    @pytest.mark.integration
    def test_general_agent_file_format_detection(self, tmp_path):
        """Test general agent's ability to detect and handle file formats"""
        # Create test files
        test_files = {
            "data.csv": pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]}),
            "data.json": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            "data.parquet": pd.DataFrame({"values": [10, 20, 30]})
        }
        
        # Save files
        for filename, data in test_files.items():
            file_path = tmp_path / filename
            if filename.endswith('.csv'):
                data.to_csv(file_path, index=False)
            elif filename.endswith('.json'):
                with open(file_path, 'w') as f:
                    json.dump(data, f)
            elif filename.endswith('.parquet'):
                data.to_parquet(file_path)
        
        with patch('scripts.agents.general_data_agent.ChatOpenAI'):
            with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
                agent = GeneralDataAgent(root_dir=str(tmp_path))
                
                # Test file format detection
                for filename in test_files.keys():
                    file_path = tmp_path / filename
                    result = agent._analyze_dataframe(str(file_path))
                    
                    # Should detect format
                    file_type = filename.split('.')[-1]
                    assert file_type in result.lower() or "analysis" in result.lower()


class TestAgentPerformance:
    """Performance tests for agent operations"""
    
    @pytest.mark.slow
    @pytest.mark.performance
    def test_large_query_result_handling(self, test_database):
        """Test handling of large query results"""
        # Create a large result set
        large_df = pd.DataFrame({
            "scenario_id": list(range(5000)),
            "acres": [i * 100 for i in range(5000)],
            "transition_type": ["change", "same"] * 2500
        })
        
        with patch('scripts.agents.landuse_natural_language_agent.duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.df.return_value = large_df
            
            with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic'):
                agent = LanduseNaturalLanguageAgent(str(test_database))
                
                start_time = time.time()
                result = agent._execute_landuse_query("SELECT * FROM large_table")
                execution_time = time.time() - start_time
                
                # Should complete in reasonable time
                assert execution_time < 5.0  # 5 seconds max
                
                # Should show truncated results
                assert "first 20 rows" in result
                assert "4980 more rows" in result
    
    @pytest.mark.slow
    @pytest.mark.performance  
    def test_concurrent_agent_operations(self, test_database):
        """Test concurrent operations from multiple agents"""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def run_agent_query(agent_class, query, db_path):
            try:
                with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic'):
                    agent = agent_class(db_path)
                    result = agent._execute_landuse_query(query)
                    results.put(result)
            except Exception as e:
                errors.put(str(e))
        
        # Create threads for concurrent operations
        threads = []
        queries = [
            "SELECT COUNT(*) FROM dim_scenario",
            "SELECT * FROM dim_time LIMIT 5",
            "SELECT DISTINCT landuse_name FROM dim_landuse"
        ]
        
        for i, query in enumerate(queries):
            t = threading.Thread(
                target=run_agent_query,
                args=(LanduseNaturalLanguageAgent, query, str(test_database))
            )
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=10)
        
        # Check results
        assert results.qsize() == len(queries)
        assert errors.qsize() == 0


class TestAgentErrorRecovery:
    """Test error recovery and resilience"""
    
    @pytest.mark.integration
    def test_database_connection_recovery(self, test_database):
        """Test recovery from database connection issues"""
        with patch('scripts.agents.landuse_natural_language_agent.duckdb.connect') as mock_connect:
            # Mock connection that always returns a mock connection object
            mock_conn = Mock()
            mock_conn.execute.return_value.df.return_value = pd.DataFrame({"result": [1]})
            mock_connect.return_value = mock_conn
            
            with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic'):
                agent = LanduseNaturalLanguageAgent(str(test_database))
                
                # Test that queries can be executed
                result = agent._execute_landuse_query("SELECT 1")
                assert "Query Results" in result or "1" in result
                
                # Now simulate a connection failure
                mock_connect.side_effect = Exception("Connection failed")
                result_error = agent._execute_landuse_query("SELECT 1") 
                assert "Error" in result_error
                assert "Connection failed" in result_error
    
    @pytest.mark.integration
    def test_llm_failure_handling(self, test_database):
        """Test handling of LLM failures"""
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic') as mock_anthropic:
            # Mock LLM that fails occasionally
            mock_llm = Mock()
            mock_llm.invoke.side_effect = [
                Exception("API rate limit exceeded"),
                Mock(content="SELECT COUNT(*) FROM dim_scenario")
            ]
            mock_anthropic.return_value = mock_llm
            
            agent = LanduseNaturalLanguageAgent(str(test_database))
            
            # Mock agent executor
            agent.agent = Mock()
            agent.agent.invoke.side_effect = [
                Exception("API rate limit exceeded"),
                {"output": "Query executed successfully"}
            ]
            
            # First query should fail
            result1 = agent.query("How many scenarios exist?")
            assert "Error" in result1
            
            # Second query should succeed
            result2 = agent.query("How many scenarios exist?")
            assert "success" in result2.lower()
    
    @pytest.mark.integration
    def test_malformed_data_handling(self, tmp_path):
        """Test handling of malformed data files"""
        # Create malformed CSV
        bad_csv = tmp_path / "bad.csv"
        with open(bad_csv, 'w') as f:
            f.write("col1,col2\n1,2,3\n4,5")  # Inconsistent columns
        
        # Create malformed JSON
        bad_json = tmp_path / "bad.json"
        with open(bad_json, 'w') as f:
            f.write("{invalid json}")
        
        with patch('scripts.agents.general_data_agent.ChatOpenAI'):
            with patch('scripts.agents.general_data_agent.FileManagementToolkit'):
                agent = GeneralDataAgent(root_dir=str(tmp_path))
                
                # Should handle bad CSV gracefully
                csv_result = agent._analyze_dataframe(str(bad_csv))
                assert "error" in csv_result.lower() or "analysis" in csv_result.lower()
                
                # Should handle bad JSON gracefully
                json_params = {
                    "file_path": str(bad_json),
                    "query": "SELECT * FROM df"
                }
                json_result = agent._query_data(json_params)
                assert "error" in json_result.lower()


class TestAgentBusinessLogic:
    """Test business logic and domain-specific features"""
    
    @pytest.mark.integration
    def test_landuse_business_insights(self, test_database):
        """Test generation of business insights"""
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic'):
            agent = LanduseNaturalLanguageAgent(str(test_database))
            
            # Test various business insight tools
            
            # Get default assumptions
            assumptions = agent._get_default_assumptions()
            assert "Climate Scenarios" in assumptions
            assert "average across all" in assumptions.lower()
            
            # Get query examples
            examples = agent._suggest_query_examples("agricultural_loss")
            assert "Agriculture" in examples
            assert "JOIN" in examples
            
            # Explain results
            explanation = agent._explain_query_results("Sample results with 1000 acres lost")
            assert "Business Insights" in explanation
            assert "agricultural loss" in explanation.lower()
    
    @pytest.mark.integration
    def test_secure_agent_audit_trail(self, test_database, tmp_path, monkeypatch):
        """Test security audit trail generation"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        log_file = tmp_path / "security.log"
        
        with patch('scripts.agents.secure_landuse_agent.SecurityLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            
            with patch('scripts.agents.secure_landuse_agent.ChatAnthropic'):
                agent = SecureLanduseAgent()
                
                # Execute various queries
                queries = [
                    ("SELECT * FROM dim_scenario", "success"),
                    ("DROP TABLE users", "blocked"),
                    ("SELECT * FROM nonexistent", "error")
                ]
                
                for query, expected_status in queries:
                    agent._execute_secure_landuse_query(query)
                
                # Verify logging calls
                assert mock_logger.log_query.call_count >= 3
                
                # Check for blocked query logging
                blocked_calls = [
                    call for call in mock_logger.log_query.call_args_list
                    if "blocked" in str(call)
                ]
                assert len(blocked_calls) >= 1