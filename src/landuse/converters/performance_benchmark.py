#!/usr/bin/env python3
"""
Performance benchmarking utilities for DuckDB bulk loading operations
"""

import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import duckdb
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..models import ConversionStats
from .bulk_loader import DuckDBBulkLoader

console = Console()


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark"""
    method_name: str
    total_records: int
    processing_time: float
    records_per_second: float
    memory_peak_mb: float
    file_size_mb: float
    success: bool
    error_message: Optional[str] = None


class PerformanceBenchmark:
    """
    Benchmark different data loading methods for DuckDB
    """

    def __init__(self, test_db_path: Optional[str] = None):
        self.test_db_path = test_db_path or tempfile.mktemp(suffix=".duckdb")
        self.results: list[BenchmarkResult] = []

    def create_test_data(self, num_records: int = 100000) -> pd.DataFrame:
        """Create test data for benchmarking"""
        console.print(f"🔬 Generating {num_records:,} test records...")

        import numpy as np

        # Generate realistic landuse transition data
        data = {
            'transition_id': range(1, num_records + 1),
            'scenario_id': np.random.randint(1, 21, num_records),  # 20 scenarios
            'time_id': np.random.randint(1, 7, num_records),       # 6 time periods
            'geography_id': np.random.randint(1, 3076, num_records),  # ~3075 counties
            'from_landuse_id': np.random.randint(1, 6, num_records),  # 5 landuse types
            'to_landuse_id': np.random.randint(1, 6, num_records),    # 5 landuse types
            'acres': np.random.uniform(0.1, 10000.0, num_records),
            'transition_type': np.random.choice(['change', 'same'], num_records, p=[0.3, 0.7])
        }

        return pd.DataFrame(data)

    def setup_test_database(self) -> None:
        """Create test database schema"""
        console.print("🏗️ Setting up test database schema...")

        with duckdb.connect(self.test_db_path) as conn:
            # Create fact table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fact_landuse_transitions (
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

    def benchmark_traditional_insert(self, df: pd.DataFrame, batch_size: int = 10000) -> BenchmarkResult:
        """Benchmark traditional INSERT statements"""
        console.print(f"📊 Benchmarking traditional INSERT (batch size: {batch_size:,})...")

        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            with duckdb.connect(self.test_db_path) as conn:
                # Clear table
                conn.execute("DELETE FROM fact_landuse_transitions")

                # Insert in batches
                total_inserted = 0
                for i in range(0, len(df), batch_size):
                    batch = df.iloc[i:i+batch_size]
                    values = [tuple(row) for row in batch.values]

                    conn.executemany("""
                        INSERT INTO fact_landuse_transitions
                        (transition_id, scenario_id, time_id, geography_id,
                         from_landuse_id, to_landuse_id, acres, transition_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, values)

                    total_inserted += len(batch)

                processing_time = time.time() - start_time
                peak_memory = self._get_memory_usage() - start_memory
                file_size = self._get_file_size(self.test_db_path)
                records_per_second = total_inserted / processing_time if processing_time > 0 else 0

                return BenchmarkResult(
                    method_name="Traditional INSERT",
                    total_records=total_inserted,
                    processing_time=processing_time,
                    records_per_second=records_per_second,
                    memory_peak_mb=peak_memory,
                    file_size_mb=file_size,
                    success=True
                )

        except Exception as e:
            return BenchmarkResult(
                method_name="Traditional INSERT",
                total_records=len(df),
                processing_time=time.time() - start_time,
                records_per_second=0,
                memory_peak_mb=0,
                file_size_mb=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_bulk_copy(self, df: pd.DataFrame) -> BenchmarkResult:
        """Benchmark DuckDB COPY command with Parquet"""
        console.print("🚀 Benchmarking bulk COPY with Parquet...")

        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            # Clear table first
            with duckdb.connect(self.test_db_path) as conn:
                conn.execute("DELETE FROM fact_landuse_transitions")

            # Use our bulk loader
            with DuckDBBulkLoader(self.test_db_path) as loader:
                stats = loader.bulk_load_dataframe(
                    df,
                    "fact_landuse_transitions",
                    columns=[
                        'transition_id', 'scenario_id', 'time_id', 'geography_id',
                        'from_landuse_id', 'to_landuse_id', 'acres', 'transition_type'
                    ]
                )

                peak_memory = self._get_memory_usage() - start_memory
                file_size = self._get_file_size(self.test_db_path)

                return BenchmarkResult(
                    method_name="Bulk COPY (Parquet)",
                    total_records=stats.processed_records,
                    processing_time=stats.processing_time,
                    records_per_second=stats.records_per_second,
                    memory_peak_mb=peak_memory,
                    file_size_mb=file_size,
                    success=True
                )

        except Exception as e:
            return BenchmarkResult(
                method_name="Bulk COPY (Parquet)",
                total_records=len(df),
                processing_time=time.time() - start_time,
                records_per_second=0,
                memory_peak_mb=0,
                file_size_mb=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_pandas_to_sql(self, df: pd.DataFrame) -> BenchmarkResult:
        """Benchmark pandas to_sql method"""
        console.print("🐼 Benchmarking pandas to_sql...")

        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            with duckdb.connect(self.test_db_path) as conn:
                # Clear table
                conn.execute("DELETE FROM fact_landuse_transitions")

                # Use pandas to_sql
                df.to_sql(
                    'fact_landuse_transitions',
                    conn,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=10000
                )

                processing_time = time.time() - start_time
                peak_memory = self._get_memory_usage() - start_memory
                file_size = self._get_file_size(self.test_db_path)
                records_per_second = len(df) / processing_time if processing_time > 0 else 0

                return BenchmarkResult(
                    method_name="Pandas to_sql",
                    total_records=len(df),
                    processing_time=processing_time,
                    records_per_second=records_per_second,
                    memory_peak_mb=peak_memory,
                    file_size_mb=file_size,
                    success=True
                )

        except Exception as e:
            return BenchmarkResult(
                method_name="Pandas to_sql",
                total_records=len(df),
                processing_time=time.time() - start_time,
                records_per_second=0,
                memory_peak_mb=0,
                file_size_mb=0,
                success=False,
                error_message=str(e)
            )

    def run_benchmark_suite(self, record_counts: list[int] = None) -> dict[int, list[BenchmarkResult]]:
        """Run complete benchmark suite with different record counts"""
        if record_counts is None:
            record_counts = [10000, 50000, 100000, 500000]

        console.print(Panel.fit(
            "🏁 [bold blue]DuckDB Performance Benchmark Suite[/bold blue]\n"
            f"[yellow]Testing with record counts: {record_counts}[/yellow]",
            border_style="blue"
        ))

        all_results = {}

        for count in record_counts:
            console.print(f"\n📈 Testing with {count:,} records...")

            # Setup
            self.setup_test_database()
            test_data = self.create_test_data(count)

            # Run benchmarks
            results = []

            # Traditional INSERT
            result = self.benchmark_traditional_insert(test_data)
            results.append(result)

            # Bulk COPY
            result = self.benchmark_bulk_copy(test_data)
            results.append(result)

            # Pandas to_sql
            result = self.benchmark_pandas_to_sql(test_data)
            results.append(result)

            all_results[count] = results

            # Show results for this record count
            self._display_results(results, f"Results for {count:,} records")

        return all_results

    def _display_results(self, results: list[BenchmarkResult], title: str) -> None:
        """Display benchmark results in a table"""
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Method", style="yellow", no_wrap=True)
        table.add_column("Records", justify="right", style="green")
        table.add_column("Time (s)", justify="right", style="blue")
        table.add_column("Records/sec", justify="right", style="magenta")
        table.add_column("Memory (MB)", justify="right", style="cyan")
        table.add_column("File Size (MB)", justify="right", style="white")
        table.add_column("Status", justify="center")

        for result in results:
            status = "✅" if result.success else "❌"
            if not result.success:
                status += f" {result.error_message[:20]}..."

            table.add_row(
                result.method_name,
                f"{result.total_records:,}",
                f"{result.processing_time:.2f}",
                f"{result.records_per_second:,.0f}",
                f"{result.memory_peak_mb:.1f}",
                f"{result.file_size_mb:.1f}",
                status
            )

        console.print(table)

    def generate_performance_report(self, all_results: dict[int, list[BenchmarkResult]]) -> str:
        """Generate a comprehensive performance report"""
        report = ["# DuckDB Bulk Loading Performance Report\n"]

        # Summary
        report.append("## Executive Summary\n")

        # Find best performing method
        best_method = {}
        for count, results in all_results.items():
            successful_results = [r for r in results if r.success]
            if successful_results:
                best = max(successful_results, key=lambda x: x.records_per_second)
                best_method[count] = best

        if best_method:
            report.append("Best performing methods by record count:\n")
            for count, result in best_method.items():
                speedup = result.records_per_second
                report.append(f"- {count:,} records: **{result.method_name}** ({speedup:,.0f} rec/s)\n")

        # Detailed results
        report.append("\n## Detailed Results\n")

        for count, results in all_results.items():
            report.append(f"\n### {count:,} Records\n")
            report.append("| Method | Time (s) | Records/sec | Memory (MB) | File Size (MB) | Status |\n")
            report.append("|--------|----------|-------------|-------------|----------------|--------|\n")

            for result in results:
                status = "✅ Success" if result.success else f"❌ {result.error_message}"
                report.append(f"| {result.method_name} | {result.processing_time:.2f} | {result.records_per_second:,.0f} | {result.memory_peak_mb:.1f} | {result.file_size_mb:.1f} | {status} |\n")

        # Performance recommendations
        report.append("\n## Recommendations\n")
        report.append("1. **Use bulk COPY with Parquet files** for large datasets (>100K records)\n")
        report.append("2. **Traditional INSERT** may be suitable for small datasets (<10K records)\n")
        report.append("3. **Pandas to_sql** provides good balance but may use more memory\n")
        report.append("4. **Always use batching** to control memory usage\n")

        return "".join(report)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0

    def _get_file_size(self, file_path: str) -> float:
        """Get file size in MB"""
        try:
            return Path(file_path).stat().st_size / 1024 / 1024  # Convert to MB
        except:
            return 0.0

    def cleanup(self):
        """Clean up test database"""
        try:
            if os.path.exists(self.test_db_path):
                os.unlink(self.test_db_path)
                console.print(f"🧹 Cleaned up test database: {self.test_db_path}")
        except Exception as e:
            console.print(f"⚠️ Could not clean up test database: {e}")


def run_performance_benchmark(output_file: Optional[str] = None) -> dict[int, list[BenchmarkResult]]:
    """
    Run a comprehensive performance benchmark and optionally save results.

    Args:
        output_file: Optional file to save the performance report

    Returns:
        Dictionary of benchmark results by record count
    """
    benchmark = PerformanceBenchmark()

    try:
        # Run the benchmark suite
        results = benchmark.run_benchmark_suite()

        # Generate and optionally save report
        if output_file:
            report = benchmark.generate_performance_report(results)
            with open(output_file, 'w') as f:
                f.write(report)
            console.print(f"📄 Performance report saved to: {output_file}")

        return results

    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run DuckDB performance benchmarks")
    parser.add_argument("--output", help="Output file for performance report")
    parser.add_argument("--records", nargs="+", type=int,
                       default=[10000, 50000, 100000],
                       help="Record counts to test")

    args = parser.parse_args()

    # Create benchmark with custom record counts
    benchmark = PerformanceBenchmark()
    results = benchmark.run_benchmark_suite(args.records)

    if args.output:
        report = benchmark.generate_performance_report(results)
        with open(args.output, 'w') as f:
            f.write(report)
        console.print(f"📄 Report saved to: {args.output}")

    benchmark.cleanup()
