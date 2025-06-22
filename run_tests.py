#!/usr/bin/env python3
"""
Test runner script for the Langchain Landuse project
Provides convenient commands for running different test suites
"""

import sys
import subprocess
from pathlib import Path
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_command(cmd: list, description: str) -> int:
    """Run a command and return exit code"""
    console.print(f"\n[bold blue]Running:[/bold blue] {description}")
    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def run_all_tests():
    """Run all tests with coverage"""
    return run_command(
        ["uv", "run", "pytest", "-v", "--cov=scripts", "--cov-report=term-missing"],
        "All tests with coverage"
    )


def run_unit_tests():
    """Run only unit tests"""
    return run_command(
        ["uv", "run", "pytest", "tests/unit", "-v", "-m", "unit or not integration"],
        "Unit tests only"
    )


def run_integration_tests():
    """Run only integration tests"""
    return run_command(
        ["uv", "run", "pytest", "tests/integration", "-v", "-m", "integration"],
        "Integration tests only"
    )


def run_security_tests():
    """Run security-specific tests"""
    return run_command(
        ["uv", "run", "pytest", "-v", "-m", "security", "-k", "security"],
        "Security tests"
    )


def run_coverage_report():
    """Generate HTML coverage report"""
    run_command(
        ["uv", "run", "pytest", "--cov=scripts", "--cov-report=html", "--cov-report=term"],
        "Tests with HTML coverage report"
    )
    console.print("\n[green]Coverage report generated in htmlcov/index.html[/green]")
    return 0


def run_specific_test(test_path: str):
    """Run a specific test file or test"""
    return run_command(
        ["uv", "run", "pytest", test_path, "-v"],
        f"Specific test: {test_path}"
    )


def run_failed_tests():
    """Re-run only failed tests from last run"""
    return run_command(
        ["uv", "run", "pytest", "--lf", "-v"],
        "Re-running failed tests"
    )


def run_parallel_tests():
    """Run tests in parallel for speed"""
    return run_command(
        ["uv", "run", "pytest", "-n", "auto", "-v"],
        "Tests in parallel"
    )


def list_available_markers():
    """List all available test markers"""
    console.print("\n[bold]Available test markers:[/bold]")
    
    markers = [
        ("unit", "Unit tests (fast, isolated)"),
        ("integration", "Integration tests (may require database)"),
        ("security", "Security-specific tests"),
        ("slow", "Tests that take more than 5 seconds"),
        ("requires_api", "Tests that require API keys"),
        ("requires_db", "Tests that require database")
    ]
    
    table = Table(title="Test Markers")
    table.add_column("Marker", style="cyan")
    table.add_column("Description", style="yellow")
    
    for marker, desc in markers:
        table.add_row(f"@pytest.mark.{marker}", desc)
    
    console.print(table)
    console.print("\n[dim]Use: pytest -m <marker> to run specific marker tests[/dim]")


def main():
    parser = argparse.ArgumentParser(description="Run tests for Langchain Landuse project")
    parser.add_argument("command", nargs="?", default="all",
                       choices=["all", "unit", "integration", "security", "coverage", 
                               "failed", "parallel", "markers"],
                       help="Type of tests to run")
    parser.add_argument("-t", "--test", help="Run specific test file or test function")
    parser.add_argument("-m", "--marker", help="Run tests with specific marker")
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword expression")
    parser.add_argument("-x", "--exitfirst", action="store_true", help="Exit on first failure")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--pdb", action="store_true", help="Drop into debugger on failures")
    
    args = parser.parse_args()
    
    console.print(Panel.fit(
        "[bold green]Langchain Landuse Test Runner[/bold green]\n"
        "[yellow]Running tests with pytest[/yellow]",
        border_style="green"
    ))
    
    # Custom test command
    if args.test:
        exit_code = run_specific_test(args.test)
    elif args.marker:
        cmd = ["uv", "run", "pytest", "-m", args.marker, "-v"]
        exit_code = run_command(cmd, f"Tests with marker: {args.marker}")
    elif args.keyword:
        cmd = ["uv", "run", "pytest", "-k", args.keyword, "-v"]
        exit_code = run_command(cmd, f"Tests matching: {args.keyword}")
    else:
        # Predefined test suites
        if args.command == "all":
            exit_code = run_all_tests()
        elif args.command == "unit":
            exit_code = run_unit_tests()
        elif args.command == "integration":
            exit_code = run_integration_tests()
        elif args.command == "security":
            exit_code = run_security_tests()
        elif args.command == "coverage":
            exit_code = run_coverage_report()
        elif args.command == "failed":
            exit_code = run_failed_tests()
        elif args.command == "parallel":
            exit_code = run_parallel_tests()
        elif args.command == "markers":
            list_available_markers()
            exit_code = 0
    
    # Summary
    if exit_code == 0:
        console.print(Panel.fit(
            "[bold green]✅ Tests passed![/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]❌ Tests failed with exit code: {exit_code}[/bold red]",
            border_style="red"
        ))
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())