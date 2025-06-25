#!/usr/bin/env python3
"""
Organize project files into a cleaner structure
"""

import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

console = Console()

def organize_files():
    """Organize project files into directories"""

    console.print(Panel.fit("📁 [bold blue]Organizing Project Files[/bold blue]", border_style="blue"))

    # Define the new directory structure
    directories = [
        "scripts/converters",
        "scripts/agents",
        "scripts/utilities",
        "data/raw",
        "data/processed",
        "data/samples",
        "docs",
        "config"
    ]

    # Create directories
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created {dir_path}")

    # Define file moves
    file_moves = {
        # Converter scripts
        "convert_landuse_nested.py": "scripts/converters/convert_landuse_nested.py",
        "convert_landuse_to_db.py": "scripts/converters/convert_landuse_to_db.py",
        "convert_landuse_transitions.py": "scripts/converters/convert_landuse_transitions.py",
        "convert_landuse_with_agriculture.py": "scripts/converters/convert_landuse_with_agriculture.py",
        "add_change_views.py": "scripts/converters/add_change_views.py",
        "data/convert_json_to_parquet.py": "scripts/converters/convert_json_to_parquet.py",

        # Agent scripts
        "data_engineering_agent.py": "scripts/agents/data_engineering_agent.py",
        "test_agent.py": "scripts/agents/test_agent.py",

        # Raw data
        "data/county_landuse_projections_RPA.json": "data/raw/county_landuse_projections_RPA.json",

        # Processed data
        "data/landuse_projections.db": "data/processed/landuse_projections.db",
        "data/landuse_transitions.db": "data/processed/landuse_transitions.db",
        "data/landuse_transitions_with_ag.db": "data/processed/landuse_transitions_with_ag.db",
        "data/county_landuse_projections_RPA.db": "data/processed/county_landuse_projections_RPA.db",

        # Sample data
        "data/inventory.json": "data/samples/inventory.json",
        "data/sample_data.csv": "data/samples/sample_data.csv",
        "data/sensor_data.parquet": "data/samples/sensor_data.parquet",

        # Config files
        ".env": "config/.env",
        "requirements.txt": "config/requirements.txt",

        # Documentation
        "CLAUDE.local.md": "docs/CLAUDE.local.md"
    }

    # Move files
    console.print("\n[bold cyan]Moving files...[/bold cyan]")
    for src, dst in file_moves.items():
        src_path = Path(src)
        dst_path = Path(dst)

        if src_path.exists():
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            console.print(f"[green]✓[/green] Moved {src} → {dst}")
        else:
            console.print(f"[yellow]![/yellow] Skipped {src} (not found)")

    # Create README files
    readme_content = {
        "scripts/converters/README.md": """# Converter Scripts

Scripts for converting land use data between formats:

- `convert_landuse_with_agriculture.py` - Main converter with agriculture aggregation
- `add_change_views.py` - Adds change-focused views to the database
- `convert_json_to_parquet.py` - Original Parquet converter
- Other converters are earlier versions kept for reference
""",
        "scripts/agents/README.md": """# Agent Scripts

LangChain-based agents for data analysis:

- `data_engineering_agent.py` - Main data engineering agent with file operations
- `test_agent.py` - Test script with sample data generation
""",
        "data/README.md": """# Data Directory

## Structure:
- `raw/` - Original source data files
- `processed/` - Converted databases and processed files
- `samples/` - Small sample datasets for testing

## Main Database:
- `processed/landuse_transitions_with_ag.db` - Primary database with agriculture aggregation

## Available Views:
- `individual_transitions` - All transitions with crop/pasture separate
- `agriculture_transitions` - All transitions with crop+pasture combined
- `individual_changes` - Only actual changes (no same-to-same)
- `agriculture_changes` - Only actual changes with agriculture combined
""",
        "README.md": """# LangChain Land Use Analysis Project

Analyzes county-level land use transitions using LangChain agents and SQLite.

## Quick Start:

1. Install dependencies:
   ```bash
   uv pip install -r config/requirements.txt
   ```

2. Set OpenAI API key in `config/.env`

3. Run the agent:
   ```bash
   uv run python scripts/agents/test_agent.py
   ```

## Project Structure:
- `scripts/` - Python scripts
  - `converters/` - Data conversion tools
  - `agents/` - LangChain agents
- `data/` - Data files
  - `raw/` - Source data
  - `processed/` - Converted databases
  - `samples/` - Test data
- `config/` - Configuration files
- `docs/` - Documentation

## Main Database:
`data/processed/landuse_transitions_with_ag.db` contains land use transitions with views for:
- Individual land uses (crop/pasture separate)
- Agriculture aggregated (crop+pasture combined)
- Change-only views (excluding same-to-same transitions)
"""
    }

    console.print("\n[bold cyan]Creating README files...[/bold cyan]")
    for readme_path, content in readme_content.items():
        Path(readme_path).write_text(content)
        console.print(f"[green]✓[/green] Created {readme_path}")

    # Create .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
ENV/

# Data files
*.db
*.parquet
data/raw/*.json
data/processed/*.db

# Config
.env
config/.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Keep sample data
!data/samples/*
"""

    Path(".gitignore").write_text(gitignore_content)
    console.print("[green]✓[/green] Created .gitignore")

    # Display new structure
    console.print("\n[bold blue]New Project Structure:[/bold blue]")

    tree = Tree("📁 langchain-landuse/")

    # Scripts
    scripts = tree.add("📂 scripts/")
    converters = scripts.add("📂 converters/")
    converters.add("📄 convert_landuse_with_agriculture.py")
    converters.add("📄 add_change_views.py")
    converters.add("📄 README.md")

    agents = scripts.add("📂 agents/")
    agents.add("📄 data_engineering_agent.py")
    agents.add("📄 test_agent.py")
    agents.add("📄 README.md")

    # Data
    data = tree.add("📂 data/")
    raw = data.add("📂 raw/")
    raw.add("📄 county_landuse_projections_RPA.json")

    processed = data.add("📂 processed/")
    processed.add("🗄️ landuse_transitions_with_ag.db [PRIMARY]")
    processed.add("🗄️ landuse_transitions.db")
    processed.add("🗄️ landuse_projections.db")

    samples = data.add("📂 samples/")
    samples.add("📄 inventory.json")
    samples.add("📄 sample_data.csv")
    samples.add("📄 sensor_data.parquet")

    # Config
    config = tree.add("📂 config/")
    config.add("📄 .env")
    config.add("📄 requirements.txt")

    # Docs
    docs = tree.add("📂 docs/")
    docs.add("📄 CLAUDE.local.md")

    # Root files
    tree.add("📄 README.md")
    tree.add("📄 .gitignore")
    tree.add("📄 organize_project.py")

    console.print(tree)

    # Summary
    summary = Panel(
        """[bold green]✅ Project organized successfully![/bold green]

[yellow]Key locations:[/yellow]
• Main agent: scripts/agents/data_engineering_agent.py
• Primary database: data/processed/landuse_transitions_with_ag.db
• Configuration: config/.env
• Documentation: README.md files in each directory

[yellow]Next steps:[/yellow]
1. Update any import paths in your scripts
2. Run: git add -A && git commit -m "Reorganize project structure"
3. Test the agent: uv run python scripts/agents/test_agent.py""",
        title="📋 Organization Complete",
        border_style="green"
    )

    console.print("\n", summary)

if __name__ == "__main__":
    organize_files()
