#!/usr/bin/env python
"""Verify that all files referenced in mkdocs.yml exist in the docs directory."""

import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


def extract_md_files_from_nav(nav_items, prefix=""):
    """Recursively extract all .md file references from the navigation structure."""
    md_files = []
    
    if isinstance(nav_items, list):
        for item in nav_items:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, str) and value.endswith('.md'):
                        md_files.append(value)
                    elif isinstance(value, list):
                        md_files.extend(extract_md_files_from_nav(value, prefix))
            elif isinstance(item, str) and item.endswith('.md'):
                md_files.append(item)
    
    return md_files


def main():
    """Main verification function."""
    # Read mkdocs.yml
    mkdocs_path = Path("mkdocs.yml")
    if not mkdocs_path.exists():
        console.print("[red]Error: mkdocs.yml not found![/red]")
        return
    
    with open(mkdocs_path, 'r') as f:
        # Use unsafe loader to handle Python tags in mkdocs.yml
        config = yaml.unsafe_load(f)
    
    # Extract all .md files from nav
    nav_files = extract_md_files_from_nav(config.get('nav', []))
    
    # Check docs directory
    docs_dir = Path("docs")
    if not docs_dir.exists():
        console.print("[red]Error: docs directory not found![/red]")
        return
    
    # Create results table
    table = Table(title="MkDocs File Verification Report")
    table.add_column("File Reference", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Full Path", style="yellow")
    
    missing_files = []
    existing_files = []
    
    # Check each file
    for md_file in sorted(set(nav_files)):
        file_path = docs_dir / md_file
        if file_path.exists():
            table.add_row(md_file, "✓ Exists", str(file_path))
            existing_files.append(md_file)
        else:
            table.add_row(md_file, "✗ Missing", str(file_path))
            missing_files.append(md_file)
    
    # Display results
    console.print(table)
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"Total files referenced: {len(nav_files)}")
    console.print(f"[green]Files found: {len(existing_files)}[/green]")
    console.print(f"[red]Files missing: {len(missing_files)}[/red]")
    
    if missing_files:
        console.print("\n[red bold]Missing files:[/red bold]")
        for file in missing_files:
            console.print(f"  - {file}")
    
    # Check for orphaned files (files in docs but not in mkdocs.yml)
    all_md_files = list(docs_dir.rglob("*.md"))
    docs_only_files = []
    
    for md_path in all_md_files:
        relative_path = md_path.relative_to(docs_dir)
        if str(relative_path) not in nav_files:
            docs_only_files.append(str(relative_path))
    
    if docs_only_files:
        console.print("\n[yellow bold]Files in docs/ but not in mkdocs.yml:[/yellow bold]")
        for file in sorted(docs_only_files):
            console.print(f"  - {file}")
    
    # Return status
    return len(missing_files) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)