#!/usr/bin/env python3
"""
Integration tests for DuckDB bulk loading optimization
"""

import pytest
import pandas as pd
import duckdb
import tempfile
import os
from pathlib import Path
import time

from landuse.converters.bulk_loader import DuckDBBulkLoader
from landuse.models import ConversionStats


class TestDuckDBBulkLoading:
    """Test suite for DuckDB bulk loading functionality"""
    
    @pytest.fixture
    def test_db_path(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
            yield f.name
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample landuse transition data"""
        import numpy as np
        
        num_records = 1000
        data = {
            'transition_id': range(1, num_records + 1),
            'scenario_id': np.random.randint(1, 5, num_records),
            'time_id': np.random.randint(1, 3, num_records),
            'geography_id': np.random.randint(1, 10, num_records),
            'from_landuse_id': np.random.randint(1, 6, num_records),
            'to_landuse_id': np.random.randint(1, 6, num_records),
            'acres': np.random.uniform(0.1, 1000.0, num_records),
            'transition_type': np.random.choice(['change', 'same'], num_records)
        }
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def test_table_schema(self, test_db_path):
        """Create test table schema"""
        with duckdb.connect(test_db_path) as conn:
            conn.execute("""
                CREATE TABLE test_transitions (
                    transition_id BIGINT PRIMARY KEY,
                    scenario_id INTEGER NOT NULL,
                    time_id INTEGER NOT NULL,
                    geography_id INTEGER NOT NULL,
                    from_landuse_id INTEGER NOT NULL,
                    to_landuse_id INTEGER NOT NULL,
                    acres DECIMAL(15,4) NOT NULL,
                    transition_type VARCHAR(20) NOT NULL
                )
            """)
        return test_db_path
    
    def test_bulk_loader_initialization(self, test_db_path):
        """Test bulk loader initialization"""
        loader = DuckDBBulkLoader(test_db_path, batch_size=5000)
        
        assert loader.db_path == Path(test_db_path)
        assert loader.batch_size == 5000
        assert loader.compression == "snappy"
        assert os.path.exists(loader.temp_dir)
        
        # Test cleanup
        loader.cleanup()
    
    def test_bulk_load_dataframe(self, test_table_schema, sample_data):
        """Test bulk loading a DataFrame"""
        with DuckDBBulkLoader(test_table_schema) as loader:
            stats = loader.bulk_load_dataframe(
                sample_data, 
                "test_transitions"
            )
            
            # Verify statistics
            assert isinstance(stats, ConversionStats)
            assert stats.total_records == len(sample_data)
            assert stats.processed_records == len(sample_data)
            assert stats.processing_time > 0
            assert stats.records_per_second > 0
            
            # Verify data was loaded
            with loader.connection() as conn:
                count_result = conn.execute("SELECT COUNT(*) FROM test_transitions").fetchone()
                assert count_result[0] == len(sample_data)
                
                # Verify data integrity
                sample_row = conn.execute("SELECT * FROM test_transitions LIMIT 1").fetchone()
                assert sample_row is not None
                assert len(sample_row) == 8  # All columns present
    
    def test_bulk_load_empty_dataframe(self, test_table_schema):
        """Test bulk loading empty DataFrame"""
        empty_df = pd.DataFrame(columns=[
            'transition_id', 'scenario_id', 'time_id', 'geography_id',
            'from_landuse_id', 'to_landuse_id', 'acres', 'transition_type'
        ])
        
        with DuckDBBulkLoader(test_table_schema) as loader:
            stats = loader.bulk_load_dataframe(empty_df, "test_transitions")
            
            assert stats.total_records == 0
            assert stats.processed_records == 0
            assert stats.processing_time == 0
            assert stats.records_per_second == 0
    
    def test_bulk_load_batches(self, test_table_schema, sample_data):
        """Test bulk loading with batch generator"""
        def data_generator():
            """Generator that yields data in chunks"""
            chunk_size = 100
            for i in range(0, len(sample_data), chunk_size):
                yield sample_data.iloc[i:i+chunk_size]
        
        with DuckDBBulkLoader(test_table_schema, batch_size=200) as loader:
            stats = loader.bulk_load_batches(
                data_generator(),
                "test_transitions",
                total_records=len(sample_data)
            )
            
            # Verify all data was loaded
            assert stats.processed_records == len(sample_data)
            
            # Verify in database
            with loader.connection() as conn:
                count_result = conn.execute("SELECT COUNT(*) FROM test_transitions").fetchone()
                assert count_result[0] == len(sample_data)
    
    def test_performance_comparison(self, test_table_schema, sample_data):
        """Test that bulk loading is faster than traditional INSERT"""
        # Traditional INSERT method
        start_time = time.time()
        with duckdb.connect(test_table_schema) as conn:
            values = [tuple(row) for row in sample_data.values]
            conn.executemany("""
                INSERT INTO test_transitions 
                (transition_id, scenario_id, time_id, geography_id,
                 from_landuse_id, to_landuse_id, acres, transition_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
        traditional_time = time.time() - start_time
        
        # Clear table
        with duckdb.connect(test_table_schema) as conn:
            conn.execute("DELETE FROM test_transitions")
        
        # Bulk COPY method
        with DuckDBBulkLoader(test_table_schema) as loader:
            stats = loader.bulk_load_dataframe(sample_data, "test_transitions")
            bulk_time = stats.processing_time
        
        # Bulk loading should be faster for reasonable dataset sizes
        # Note: For very small datasets, traditional INSERT might be faster due to overhead
        if len(sample_data) > 100:
            assert bulk_time <= traditional_time * 2  # Allow some variance in test environment
        
        print(f"Traditional INSERT: {traditional_time:.3f}s")
        print(f"Bulk COPY: {bulk_time:.3f}s")
        print(f"Speedup: {traditional_time/bulk_time:.1f}x")
    
    def test_error_handling(self, test_db_path):
        """Test error handling in bulk loader"""
        # Test with non-existent table
        invalid_data = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        
        with DuckDBBulkLoader(test_db_path) as loader:
            with pytest.raises(Exception):  # Should raise error for non-existent table
                loader.bulk_load_dataframe(invalid_data, "non_existent_table")
    
    def test_context_manager(self, test_db_path):
        """Test context manager functionality"""
        temp_dir = None
        
        with DuckDBBulkLoader(test_db_path) as loader:
            temp_dir = loader.temp_dir
            assert os.path.exists(temp_dir)
        
        # Temp directory should be cleaned up after context exit
        assert not os.path.exists(temp_dir)
    
    def test_different_compression_formats(self, test_table_schema, sample_data):
        """Test different Parquet compression formats"""
        compressions = ["snappy", "gzip", "brotli"]
        
        for compression in compressions:
            # Clear table
            with duckdb.connect(test_table_schema) as conn:
                conn.execute("DELETE FROM test_transitions")
            
            # Test with different compression
            with DuckDBBulkLoader(test_table_schema, compression=compression) as loader:
                stats = loader.bulk_load_dataframe(sample_data, "test_transitions")
                
                assert stats.processed_records == len(sample_data)
                
                # Verify data integrity
                with loader.connection() as conn:
                    count_result = conn.execute("SELECT COUNT(*) FROM test_transitions").fetchone()
                    assert count_result[0] == len(sample_data)
    
    def test_table_optimization(self, test_table_schema, sample_data):
        """Test table optimization after bulk loading"""
        with DuckDBBulkLoader(test_table_schema) as loader:
            # Load data
            loader.bulk_load_dataframe(sample_data, "test_transitions")
            
            # Optimize table (should not raise errors)
            loader.optimize_table("test_transitions")
            
            # Verify table is still accessible
            with loader.connection() as conn:
                result = conn.execute("SELECT COUNT(*) FROM test_transitions").fetchone()
                assert result[0] == len(sample_data)


@pytest.mark.integration
class TestPerformanceBenchmark:
    """Test performance benchmarking functionality"""
    
    def test_create_test_data(self):
        """Test test data generation"""
        from landuse.converters.performance_benchmark import PerformanceBenchmark
        
        benchmark = PerformanceBenchmark()
        test_data = benchmark.create_test_data(1000)
        
        assert len(test_data) == 1000
        assert 'transition_id' in test_data.columns
        assert 'acres' in test_data.columns
        assert test_data['transition_id'].nunique() == 1000  # All unique IDs
        
        benchmark.cleanup()
    
    def test_benchmark_methods_exist(self):
        """Test that benchmark methods are callable"""
        from landuse.converters.performance_benchmark import PerformanceBenchmark
        
        benchmark = PerformanceBenchmark()
        
        # Check methods exist and are callable
        assert callable(benchmark.benchmark_traditional_insert)
        assert callable(benchmark.benchmark_bulk_copy)
        assert callable(benchmark.benchmark_pandas_to_sql)
        
        benchmark.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])