"""Base converter class for data transformation operations."""

import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional

import duckdb
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

from landuse.config.landuse_config import LanduseConfig
from landuse.connections.duckdb_connection import DuckDBConnection
from landuse.utils.retry_decorators import database_retry


class BaseConverter(ABC):
    """Base class for data converters with common functionality."""

    def __init__(
        self,
        input_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
        config: Optional[LanduseConfig] = None
    ):
        """
        Initialize the converter.

        Args:
            input_path: Path to input data file
            output_path: Path to output database or file
            config: Configuration object
        """
        self.config = config or LanduseConfig()
        self.console = Console()

        # Set default paths if not provided
        self.input_path = input_path or Path(self.config.base_dir) / "data/raw/state_landuse_county.json"
        self.output_path = output_path or Path(self.config.duckdb_path)

        # Ensure paths exist
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        # Create output directory if needed
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database connection if output is DuckDB
        if str(self.output_path).endswith('.duckdb'):
            self.db_connection = DuckDBConnection(
                database_path=str(self.output_path),
                read_only=False
            )
        else:
            self.db_connection = None

    @abstractmethod
    def convert(self) -> None:
        """
        Execute the conversion process.
        Must be implemented by subclasses.
        """
        pass

    def read_json_stream(self) -> Iterator[dict[str, Any]]:
        """
        Read large JSON file as a stream of objects.

        Yields:
            Dictionary objects from the JSON file
        """
        self.console.print(f"[blue]Reading JSON data from: {self.input_path}[/blue]")

        with open(self.input_path) as f:
            # Determine if it's a JSON array or newline-delimited JSON
            first_char = f.read(1)
            f.seek(0)

            if first_char == '[':
                # JSON array - use streaming parser
                import ijson
                parser = ijson.items(f, 'item')
                yield from parser
            else:
                # Assume newline-delimited JSON
                for line in f:
                    if line.strip():
                        yield json.loads(line)

    @database_retry(max_attempts=3)
    def execute_sql(self, query: str, params: Optional[tuple] = None) -> Any:
        """
        Execute a SQL query with retry logic.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            Query result
        """
        if not self.db_connection:
            raise ValueError("No database connection available")

        conn = self.db_connection._instance
        if params:
            return conn.execute(query, params)
        else:
            return conn.execute(query)

    def create_table(self, table_name: str, schema: str) -> None:
        """
        Create a table with the given schema.

        Args:
            table_name: Name of the table to create
            schema: SQL schema definition
        """
        self.console.print(f"[yellow]Creating table: {table_name}[/yellow]")

        # Drop existing table
        self.execute_sql(f"DROP TABLE IF EXISTS {table_name}")

        # Create new table
        create_query = f"CREATE TABLE {table_name} ({schema})"
        self.execute_sql(create_query)

        self.console.print(f"[green]✓ Created table: {table_name}[/green]")

    def create_index(self, table_name: str, columns: list[str], index_name: Optional[str] = None) -> None:
        """
        Create an index on the specified columns.

        Args:
            table_name: Table to index
            columns: List of column names
            index_name: Optional index name (auto-generated if not provided)
        """
        if not index_name:
            index_name = f"idx_{table_name}_{'_'.join(columns)}"

        self.console.print(f"[yellow]Creating index: {index_name}[/yellow]")

        columns_str = ", ".join(columns)
        self.execute_sql(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_str})")

        self.console.print(f"[green]✓ Created index: {index_name}[/green]")

    def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        result = self.execute_sql(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0

    def analyze_table(self, table_name: str) -> None:
        """Run ANALYZE on a table for query optimization."""
        self.console.print(f"[yellow]Analyzing table: {table_name}[/yellow]")
        self.execute_sql(f"ANALYZE {table_name}")
        self.console.print(f"[green]✓ Analyzed table: {table_name}[/green]")

    def create_progress_bar(self, total: Optional[int] = None, description: str = "Processing") -> Progress:
        """
        Create a rich progress bar for tracking conversion progress.

        Args:
            total: Total number of items to process
            description: Description of the process

        Returns:
            Progress bar instance
        """
        if total:
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            )
        else:
            # Indeterminate progress
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            )

    def validate_output(self) -> bool:
        """
        Validate the conversion output.
        Can be overridden by subclasses for specific validation.

        Returns:
            True if validation passes
        """
        if self.db_connection:
            # Check if any tables were created
            result = self.execute_sql("""
                SELECT COUNT(*) as table_count
                FROM information_schema.tables
                WHERE table_schema = 'main'
            """).fetchone()

            table_count = result[0] if result else 0

            if table_count == 0:
                self.console.print("[red]✗ No tables created[/red]")
                return False

            self.console.print(f"[green]✓ Created {table_count} tables[/green]")
            return True

        # For non-database outputs, check if file exists
        if self.output_path.exists():
            size_mb = self.output_path.stat().st_size / (1024 * 1024)
            self.console.print(f"[green]✓ Output file created: {size_mb:.1f} MB[/green]")
            return True

        return False

    def print_summary(self, start_time: float) -> None:
        """
        Print a summary of the conversion process.

        Args:
            start_time: Start time from time.time()
        """
        import time

        elapsed = time.time() - start_time
        self.console.print("\n[bold blue]Conversion Summary:[/bold blue]")
        self.console.print(f"Input: {self.input_path}")
        self.console.print(f"Output: {self.output_path}")
        self.console.print(f"Time elapsed: {elapsed:.1f} seconds")

        if self.db_connection:
            # Print table statistics
            tables_result = self.execute_sql("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                ORDER BY table_name
            """).fetchall()

            self.console.print("\n[bold]Table Statistics:[/bold]")
            for (table_name,) in tables_result:
                row_count = self.get_row_count(table_name)
                self.console.print(f"  {table_name}: {row_count:,} rows")
