#!/usr/bin/env python
"""Verify that all files referenced in mkdocs.yml exist in the docs directory."""

import re
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


def extract_md_files_from_mkdocs():
    """Extract .md file references from mkdocs.yml using regex."""
    md_files = []
    
    with open('mkdocs.yml', 'r') as f:
        content = f.read()
    
    # Find nav section
    nav_start = content.find('nav:')
    if nav_start == -1:
        return []
    
    # Extract until the next top-level section (no leading spaces)
    nav_section = ""
    lines = content[nav_start:].split('\n')
    for i, line in enumerate(lines):
        if i > 0 and line and not line.startswith(' ') and not line.startswith('\t'):
            break
        nav_section += line + '\n'
    
    # Find all .md references in the nav section
    # Pattern matches: word.md or path/to/file.md after a colon
    pattern = r':\s*([a-zA-Z0-9_\-/]+\.md)'
    matches = re.findall(pattern, nav_section)
    
    return matches


def main():
    """Main verification function."""
    # Check current directory
    if not Path("mkdocs.yml").exists():
        console.print("[red]Error: mkdocs.yml not found![/red]")
        return False
    
    # Extract all .md files from nav
    nav_files = extract_md_files_from_mkdocs()
    
    # Check docs directory
    docs_dir = Path("docs")
    if not docs_dir.exists():
        console.print("[red]Error: docs directory not found![/red]")
        return False
    
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
    console.print(f"Total unique files referenced: {len(set(nav_files))}")
    console.print(f"[green]Files found: {len(existing_files)}[/green]")
    console.print(f"[red]Files missing: {len(missing_files)}[/red]")
    
    if missing_files:
        console.print("\n[red bold]Missing files:[/red bold]")
        for file in missing_files:
            console.print(f"  - {file}")
    
    # Check for orphaned files (files in docs but not in mkdocs.yml)
    all_md_files = list(docs_dir.rglob("*.md"))
    docs_only_files = []
    
    nav_files_set = set(nav_files)
    for md_path in all_md_files:
        relative_path = md_path.relative_to(docs_dir)
        if str(relative_path) not in nav_files_set:
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