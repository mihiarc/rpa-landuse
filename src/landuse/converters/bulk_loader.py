#!/usr/bin/env python3
"""
DuckDB Bulk Loader for Landuse Data
Optimized bulk loading utilities using DuckDB's COPY command and Parquet files
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
import time
from contextlib import contextmanager

from ..models import ConversionConfig, ConversionStats, ProcessedTransition
from ..converter_models import ConversionMode

console = Console()


class DuckDBBulkLoader:
    """
    High-performance bulk loader for DuckDB using COPY command with Parquet files.
    
    This loader provides significant performance improvements over traditional INSERT
    statements by leveraging DuckDB's native bulk loading capabilities.
    """
    
    def __init__(
        self, 
        db_path: Union[str, Path], 
        temp_dir: Optional[str] = None,
        batch_size: int = 100000,
        compression: str = "snappy"
    ):
        self.db_path = Path(db_path)
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="duckdb_bulk_")
        self.batch_size = batch_size
        self.compression = compression
        self.conn = None
        
        # Ensure temp directory exists
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        
        console.print(f"🚀 Initialized DuckDB bulk loader")
        console.print(f"   📁 Database: {self.db_path}")
        console.print(f"   📂 Temp dir: {self.temp_dir}")
        console.print(f"   📦 Batch size: {self.batch_size:,}")
    
    @contextmanager
    def connection(self):
        """Context manager for DuckDB connections"""
        try:
            self.conn = duckdb.connect(str(self.db_path))
            yield self.conn
        finally:
            if self.conn:
                self.conn.close()
                self.conn = None
    
    def bulk_load_dataframe(
        self, 
        df: pd.DataFrame, 
        table_name: str, 
        columns: Optional[List[str]] = None,
        mode: str = "append"
    ) -> ConversionStats:
        """
        Bulk load a DataFrame into a DuckDB table using COPY.
        
        Args:
            df: DataFrame to load
            table_name: Target table name
            columns: Specific columns to load (if None, uses all DataFrame columns)
            mode: Load mode - 'append', 'replace', or 'create'
            
        Returns:
            ConversionStats: Statistics about the loading operation
        """
        start_time = time.time()
        
        if df.empty:
            return ConversionStats(
                total_records=0,
                processed_records=0,
                processing_time=0.0,
                records_per_second=0.0
            )
        
        # Prepare column specification
        column_spec = ""
        if columns:
            column_spec = f"({', '.join(columns)})"
        
        # Create temporary Parquet file
        temp_file = Path(self.temp_dir) / f"{table_name}_{int(time.time())}.parquet"
        
        try:
            # Write DataFrame to Parquet with optimizations
            df.to_parquet(
                temp_file, 
                index=False, 
                compression=self.compression,
                engine='pyarrow'
            )
            
            with self.connection() as conn:
                # Execute the COPY command
                copy_sql = f"""
                    COPY {table_name} {column_spec}
                    FROM '{temp_file}' (FORMAT PARQUET)
                """
                
                conn.execute(copy_sql)
                
                # Get actual row count from table
                count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                actual_count = count_result[0] if count_result else 0
                
            processing_time = time.time() - start_time
            records_per_second = len(df) / processing_time if processing_time > 0 else 0
            
            console.print(f"✅ Loaded {len(df):,} records into {table_name} in {processing_time:.2f}s ({records_per_second:,.0f} rec/s)")
            
            return ConversionStats(
                total_records=len(df),
                processed_records=len(df),
                processing_time=processing_time,
                records_per_second=records_per_second
            )
            
        except Exception as e:
            console.print(f"❌ Error loading data into {table_name}: {e}")
            raise
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()
    
    def bulk_load_batches(
        self,
        data_generator,
        table_name: str,
        columns: Optional[List[str]] = None,
        total_records: Optional[int] = None
    ) -> ConversionStats:
        """
        Bulk load data in batches from a generator.
        
        Args:
            data_generator: Generator yielding dictionaries or DataFrames
            table_name: Target table name
            columns: Specific columns to load
            total_records: Total number of records (for progress tracking)
            
        Returns:
            ConversionStats: Aggregated statistics
        """
        start_time = time.time()
        total_processed = 0
        batch_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"Bulk loading {table_name}...", 
                total=total_records or 100
            )
            
            current_batch = []
            
            for item in data_generator:
                if isinstance(item, dict):
                    current_batch.append(item)
                elif isinstance(item, pd.DataFrame):
                    # Handle DataFrame directly
                    stats = self.bulk_load_dataframe(item, table_name, columns)
                    total_processed += stats.processed_records
                    batch_count += 1
                    continue
                else:
                    raise ValueError(f"Unsupported data type: {type(item)}")
                
                # Process batch when it reaches batch_size
                if len(current_batch) >= self.batch_size:
                    df = pd.DataFrame(current_batch)
                    stats = self.bulk_load_dataframe(df, table_name, columns)
                    total_processed += stats.processed_records
                    batch_count += 1
                    current_batch = []
                    
                    # Update progress
                    if total_records:
                        progress.update(task, completed=total_processed)
                    else:
                        progress.update(task, advance=len(df))
            
            # Process remaining data
            if current_batch:
                df = pd.DataFrame(current_batch)
                stats = self.bulk_load_dataframe(df, table_name, columns)
                total_processed += stats.processed_records
                batch_count += 1
                
                if total_records:
                    progress.update(task, completed=total_processed)
            
            progress.update(task, completed=total_processed)
        
        total_time = time.time() - start_time
        records_per_second = total_processed / total_time if total_time > 0 else 0
        
        console.print(f"🎯 Completed bulk loading: {total_processed:,} records in {batch_count} batches")
        console.print(f"   ⏱️ Total time: {total_time:.2f}s ({records_per_second:,.0f} rec/s)")
        
        return ConversionStats(
            total_records=total_processed,
            processed_records=total_processed,
            processing_time=total_time,
            records_per_second=records_per_second
        )
    
    def bulk_load_transitions(
        self,
        transitions: List[ProcessedTransition],
        table_name: str = "fact_landuse_transitions"
    ) -> ConversionStats:
        """
        Bulk load landuse transitions using optimized data structures.
        
        Args:
            transitions: List of processed transitions
            table_name: Target table name
            
        Returns:
            ConversionStats: Loading statistics
        """
        console.print(f"🔄 Bulk loading {len(transitions):,} transitions...")
        
        def transition_generator():
            """Generator that yields transition data in batches"""
            batch = []
            for transition in transitions:
                batch.append({
                    'transition_id': transition.transition_id,
                    'scenario_id': transition.scenario_id,
                    'time_id': transition.time_id,
                    'geography_id': transition.geography_id,
                    'from_landuse_id': transition.from_landuse_id,
                    'to_landuse_id': transition.to_landuse_id,
                    'acres': transition.acres,
                    'transition_type': transition.transition_type
                })
                
                if len(batch) >= self.batch_size:
                    yield pd.DataFrame(batch)
                    batch = []
            
            # Yield remaining data
            if batch:
                yield pd.DataFrame(batch)
        
        columns = [
            'transition_id', 'scenario_id', 'time_id', 'geography_id',
            'from_landuse_id', 'to_landuse_id', 'acres', 'transition_type'
        ]
        
        return self.bulk_load_batches(
            transition_generator(),
            table_name,
            columns=columns,
            total_records=len(transitions)
        )
    
    def optimize_table(self, table_name: str) -> None:
        """
        Optimize table after bulk loading by analyzing and updating statistics.
        
        Args:
            table_name: Table to optimize
        """
        console.print(f"🔧 Optimizing table {table_name}...")
        
        with self.connection() as conn:
            # Analyze table for better query planning
            conn.execute(f"ANALYZE {table_name}")
            
            # Get table statistics
            stats = conn.execute(f"""
                SELECT 
                    COUNT(*) as row_count,
                    COUNT(DISTINCT COLUMNS(*)) as distinct_values
                FROM {table_name}
            """).fetchone()
            
            if stats:
                console.print(f"   📊 {stats[0]:,} rows analyzed")
    
    def cleanup(self) -> None:
        """Clean up temporary files and directories"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                console.print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            console.print(f"⚠️ Warning: Could not clean up temp directory: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_bulk_loader(
    db_path: Union[str, Path],
    config: Optional[ConversionConfig] = None
) -> DuckDBBulkLoader:
    """
    Factory function to create a DuckDB bulk loader with configuration.
    
    Args:
        db_path: Path to DuckDB database
        config: Optional conversion configuration
        
    Returns:
        DuckDBBulkLoader: Configured bulk loader
    """
    if config is None:
        config = ConversionConfig()
    
    return DuckDBBulkLoader(
        db_path=db_path,
        batch_size=config.batch_size,
        temp_dir=str(config.temp_dir) if config.temp_dir else None
    )