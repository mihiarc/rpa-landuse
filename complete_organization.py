#!/usr/bin/env python3
"""
Complete the organization migration safely
This script finishes moving files to their correct locations with safety features
"""

import shutil
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import time
from datetime import datetime

console = Console()

class SafeOrganizer:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.backup_dir = Path(".organization_backup")
        self.changes_log = []
        
    def create_backup_dir(self):
        """Create backup directory with timestamp"""
        if not self.dry_run:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_dir = Path(f".organization_backup_{timestamp}")
            self.backup_dir.mkdir(exist_ok=True)
            console.print(f"[green]✓[/green] Created backup directory: {self.backup_dir}")
    
    def backup_file(self, file_path):
        """Create backup of file before moving"""
        if not self.dry_run and file_path.exists():
            backup_path = self.backup_dir / file_path.name
            shutil.copy2(file_path, backup_path)
            console.print(f"[blue]📋[/blue] Backed up: {file_path.name}")
    
    def safe_move(self, src, dst):
        """Safely move file with backup and validation"""
        src_path = Path(src)
        dst_path = Path(dst)
        
        # Validate source exists
        if not src_path.exists():
            console.print(f"[yellow]⚠️[/yellow] Skipped: {src} (not found)")
            return False
        
        # Create destination directory
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check for conflicts
        if dst_path.exists():
            console.print(f"[red]❌[/red] Conflict: {dst} already exists")
            return False
        
        if self.dry_run:
            console.print(f"[cyan]🔍[/cyan] WOULD MOVE: {src} → {dst}")
            self.changes_log.append(f"MOVE: {src} → {dst}")
            return True
        
        # Backup original file
        self.backup_file(src_path)
        
        # Move file
        try:
            shutil.move(str(src_path), str(dst_path))
            console.print(f"[green]✅[/green] Moved: {src} → {dst}")
            self.changes_log.append(f"MOVED: {src} → {dst}")
            return True
        except Exception as e:
            console.print(f"[red]❌[/red] Error moving {src}: {e}")
            return False
    
    def create_directory(self, dir_path):
        """Create directory if it doesn't exist"""
        path = Path(dir_path)
        if self.dry_run:
            if not path.exists():
                console.print(f"[cyan]🔍[/cyan] WOULD CREATE: {dir_path}")
                self.changes_log.append(f"CREATE_DIR: {dir_path}")
        else:
            existed_before = path.exists()
            path.mkdir(parents=True, exist_ok=True)
            if not existed_before:
                console.print(f"[green]✅[/green] Created directory: {dir_path}")
                self.changes_log.append(f"CREATED_DIR: {dir_path}")
    
    def save_changes_log(self):
        """Save log of all changes made"""
        if not self.dry_run:
            log_file = self.backup_dir / "changes.log"
            with open(log_file, 'w') as f:
                f.write(f"Organization Migration Log\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"Changes:\n")
                for change in self.changes_log:
                    f.write(f"  {change}\n")
            console.print(f"[green]✓[/green] Changes logged to: {log_file}")

def complete_organization(dry_run=False):
    """Complete the organization migration"""
    
    organizer = SafeOrganizer(dry_run=dry_run)
    
    console.print(Panel.fit(
        f"🔧 [bold blue]Completing Organization Migration[/bold blue]\n"
        f"[cyan]Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}[/cyan]",
        border_style="blue"
    ))
    
    if not dry_run:
        organizer.create_backup_dir()
    
    # Define the moves needed to complete organization
    moves_needed = [
        # Sample data files that are in wrong location
        ("data/inventory.json", "data/samples/inventory.json"),
        ("data/sample_data.csv", "data/samples/sample_data.csv"), 
        ("data/sensor_data.parquet", "data/samples/sensor_data.parquet"),
    ]
    
    # Create required directories
    directories_needed = [
        "data/samples",
    ]
    
    console.print("\n[bold cyan]📁 Creating directories...[/bold cyan]")
    for directory in directories_needed:
        organizer.create_directory(directory)
    
    console.print("\n[bold cyan]📦 Moving files...[/bold cyan]")
    success_count = 0
    for src, dst in moves_needed:
        if organizer.safe_move(src, dst):
            success_count += 1
    
    # Update .gitignore to ensure sample files are tracked
    gitignore_updates = [
        "# Keep sample data files",
        "!data/samples/*.json",
        "!data/samples/*.csv", 
        "!data/samples/*.parquet"
    ]
    
    console.print("\n[bold cyan]📝 Updating .gitignore...[/bold cyan]")
    gitignore_path = Path(".gitignore")
    
    if gitignore_path.exists():
        current_content = gitignore_path.read_text()
        
        # Check if updates are needed
        needs_update = False
        for line in gitignore_updates:
            if line not in current_content:
                needs_update = True
                break
        
        if needs_update:
            if dry_run:
                console.print("[cyan]🔍[/cyan] WOULD UPDATE: .gitignore with sample file exceptions")
                organizer.changes_log.append("UPDATE: .gitignore")
            else:
                # Backup current .gitignore
                organizer.backup_file(gitignore_path)
                
                # Add updates
                with open(gitignore_path, 'a') as f:
                    f.write("\n# Sample data tracking (added by organization script)\n")
                    for line in gitignore_updates[1:]:  # Skip the comment
                        f.write(f"{line}\n")
                
                console.print("[green]✅[/green] Updated .gitignore to track sample files")
                organizer.changes_log.append("UPDATED: .gitignore")
        else:
            console.print("[green]✓[/green] .gitignore already up to date")
    
    # Save changes log
    if not dry_run:
        organizer.save_changes_log()
    
    # Display summary
    console.print("\n")
    summary_table = Table(title="📊 Organization Migration Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Mode", "DRY RUN" if dry_run else "EXECUTED")
    summary_table.add_row("Files Moved", f"{success_count}/{len(moves_needed)}")
    summary_table.add_row("Directories Created", str(len(directories_needed)))
    summary_table.add_row("Total Changes", str(len(organizer.changes_log)))
    
    if not dry_run:
        summary_table.add_row("Backup Location", str(organizer.backup_dir))
    
    console.print(summary_table)
    
    # Show next steps
    if dry_run:
        next_steps = Panel(
            """[bold yellow]🔍 DRY RUN COMPLETE[/bold yellow]

[green]✓ No actual changes made[/green]
[green]✓ All operations validated[/green]

[bold cyan]To execute for real:[/bold cyan]
```bash
uv run python complete_organization.py --execute
```

[bold cyan]Or run interactively:[/bold cyan]
```bash
uv run python complete_organization.py
```""",
            title="Next Steps",
            border_style="yellow"
        )
    else:
        next_steps = Panel(
            f"""[bold green]✅ ORGANIZATION MIGRATION COMPLETE![/bold green]

[yellow]📋 Backup created at:[/yellow] {organizer.backup_dir}
[yellow]📝 Changes logged for rollback[/yellow]

[bold cyan]Verify everything works:[/bold cyan]
```bash
uv run python scripts/agents/test_agent.py
```

[bold cyan]If you need to rollback:[/bold cyan]
```bash
# Restore from backup directory
cp {organizer.backup_dir}/* data/
```

[bold cyan]Commit the changes:[/bold cyan]
```bash
git add .
git commit -m "Complete organization migration - move sample files to data/samples/"
```""",
            title="Migration Complete!",
            border_style="green"
        )
    
    console.print(next_steps)
    
    return success_count == len(moves_needed)

if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if "--execute" in sys.argv:
        dry_run = False
    elif "--dry-run" in sys.argv:
        dry_run = True
    else:
        # Interactive mode
        console.print("[bold yellow]🤔 Choose execution mode:[/bold yellow]")
        console.print("1. [cyan]Dry run[/cyan] - Preview changes without executing")
        console.print("2. [green]Execute[/green] - Perform the migration")
        
        choice = console.input("\nEnter choice (1 or 2): ").strip()
        dry_run = choice != "2"
    
    # Run the organization
    success = complete_organization(dry_run=dry_run)
    
    if dry_run:
        console.print("\n[bold blue]🔍 Dry run completed. Run with --execute to apply changes.[/bold blue]")
    elif success:
        console.print("\n[bold green]🎉 Organization migration completed successfully![/bold green]")
    else:
        console.print("\n[bold red]❌ Some operations failed. Check the output above.[/bold red]")
        sys.exit(1) 