#!/usr/bin/env python3
"""CLI commands for schema management."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from landuse.core.app_config import AppConfig

from .manager import SchemaManager

console = Console()


@click.group()
@click.pass_context
def cli(ctx):
    """Schema management commands for DuckDB database."""
    config = AppConfig()
    ctx.obj = {"config": config, "schema_dir": Path("schema")}


@cli.command()
@click.pass_context
def status(ctx):
    """Show current schema status and version."""
    config = ctx.obj["config"]
    schema_dir = ctx.obj["schema_dir"]

    manager = SchemaManager(db_path=Path(config.database.path), schema_dir=schema_dir, config=config, console=console)

    current_version = manager.get_current_version()

    # Create status table
    table = Table(title="Schema Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Database", config.database.path)
    table.add_row("Current Version", current_version or "Not versioned")
    table.add_row("Schema Directory", str(schema_dir))

    # Check if migration needed
    latest_def = sorted(schema_dir.glob("definitions/v*.yaml"))
    if latest_def:
        latest_version = latest_def[-1].stem[1:]  # Remove 'v' prefix
        table.add_row("Latest Available", latest_version)

        if current_version != latest_version:
            table.add_row("Status", "[yellow]Migration available[/yellow]")
        else:
            table.add_row("Status", "[green]Up to date[/green]")

    console.print(table)

    # Validate current schema
    console.print("\n[bold]Validating schema...[/bold]")
    validation_result = manager.validate_schema()

    if validation_result.is_valid:
        console.print("[green]✓ Schema is valid[/green]")
    else:
        console.print(
            f"[red]✗ Schema has {validation_result.error_count} errors, "
            f"{validation_result.warning_count} warnings[/red]"
        )

        for issue in validation_result.issues:
            icon = "❌" if issue.level == "error" else "⚠️" if issue.level == "warning" else "ℹ️"
            console.print(f"{icon} [{issue.level}] {issue.message}")
            if issue.suggestion:
                console.print(f"   → {issue.suggestion}")

    manager.close()


@cli.command()
@click.option("--version", default="latest", help="Target schema version")
@click.option("--dry-run", is_flag=True, help="Plan migration without executing")
@click.pass_context
def migrate(ctx, version, dry_run):
    """Migrate database to target schema version."""
    config = ctx.obj["config"]
    schema_dir = ctx.obj["schema_dir"]

    manager = SchemaManager(
        db_path=Path(config.database.path),
        schema_dir=schema_dir,
        config=config,
        console=console,
        read_only=False,  # Need write access for migrations
    )

    console.print(f"[bold]Migrating to version: {version}[/bold]")

    try:
        result = manager.migrate(target_version=version if version != "latest" else None, dry_run=dry_run)

        if dry_run:
            console.print("\n[yellow]Dry run - no changes made[/yellow]")
            console.print("\nMigration plan:")
            for i, step in enumerate(result.plan.steps, 1):
                console.print(f"{i}. {step.description}")

            if result.plan.requires_downtime:
                console.print("\n[yellow]⚠️  This migration requires downtime[/yellow]")
            if result.plan.data_loss_risk:
                console.print("\n[red]⚠️  This migration has data loss risk[/red]")
        else:
            if result.status == "completed":
                console.print(f"[green]✓ Migration completed successfully in {result.duration_seconds:.1f}s[/green]")
            else:
                console.print(f"[red]✗ Migration failed: {result.status}[/red]")
                for error in result.errors:
                    console.print(f"  - {error}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    manager.close()


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate database schema against definition."""
    config = ctx.obj["config"]
    schema_dir = ctx.obj["schema_dir"]

    manager = SchemaManager(db_path=Path(config.database.path), schema_dir=schema_dir, config=config, console=console)

    console.print("[bold]Validating database schema...[/bold]")
    result = manager.validate_schema()

    # Create results table
    table = Table(title="Validation Results")
    table.add_column("Level", style="cyan")
    table.add_column("Category")
    table.add_column("Issue")
    table.add_column("Location")

    for issue in result.issues:
        level_style = "red" if issue.level == "error" else "yellow" if issue.level == "warning" else "blue"
        location = issue.table or ""
        if issue.column:
            location += f".{issue.column}"

        table.add_row(f"[{level_style}]{issue.level}[/{level_style}]", issue.category, issue.message, location)

    console.print(table)

    # Summary
    if result.is_valid:
        console.print("\n[green]✓ Schema validation passed[/green]")
    else:
        console.print(
            f"\n[red]✗ Schema validation failed with {result.error_count} errors, {result.warning_count} warnings[/red]"
        )

    manager.close()


@cli.command()
@click.option("--output", "-o", help="Output file path")
@click.pass_context
def generate_models(ctx, output):
    """Generate Pydantic models from current schema."""
    config = ctx.obj["config"]
    schema_dir = ctx.obj["schema_dir"]

    manager = SchemaManager(db_path=Path(config.database.path), schema_dir=schema_dir, config=config, console=console)

    console.print("[bold]Generating Pydantic models...[/bold]")
    models_path = manager.generate_models()

    if output:
        # Copy to specified output path
        output_path = Path(output)
        output_path.write_text(models_path.read_text())
        console.print(f"[green]✓ Models written to {output_path}[/green]")
    else:
        console.print(f"[green]✓ Models generated at {models_path}[/green]")

    manager.close()


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["sql", "markdown", "json", "mermaid"]),
    default="markdown",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path (stdout if not specified)")
@click.pass_context
def export(ctx, format, output):
    """Export schema in various formats."""
    config = ctx.obj["config"]
    schema_dir = ctx.obj["schema_dir"]

    manager = SchemaManager(db_path=Path(config.database.path), schema_dir=schema_dir, config=config, console=console)

    console.print(f"[bold]Exporting schema as {format}...[/bold]")
    content = manager.export_schema(format)

    if output:
        output_path = Path(output)
        output_path.write_text(content)
        console.print(f"[green]✓ Schema exported to {output_path}[/green]")
    else:
        console.print("\n" + content)

    manager.close()


@cli.command()
@click.pass_context
def checkpoint(ctx):
    """Create a checkpoint of current schema state."""
    config = ctx.obj["config"]
    schema_dir = ctx.obj["schema_dir"]

    manager = SchemaManager(db_path=Path(config.database.path), schema_dir=schema_dir, config=config, console=console)

    console.print("[bold]Creating schema checkpoint...[/bold]")
    checkpoint_path = manager.create_checkpoint()
    console.print(f"[green]✓ Checkpoint created at {checkpoint_path}[/green]")

    manager.close()


@cli.command()
@click.argument("from_version")
@click.argument("to_version")
@click.pass_context
def create_migration(ctx, from_version, to_version):
    """Create a new migration file template."""
    schema_dir = ctx.obj["schema_dir"]
    migrations_dir = schema_dir / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    migration_file = migrations_dir / f"v{from_version}_to_v{to_version}.sql"

    if migration_file.exists():
        console.print(f"[red]Migration already exists: {migration_file}[/red]")
        return

    template = f"""-- Migration: v{from_version} to v{to_version}
-- Author: TODO
-- Date: {datetime.utcnow().isoformat()}
-- Description: TODO

-- Pre-migration checks
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM schema_version WHERE version_number = '{from_version}') THEN
    RAISE EXCEPTION 'Current version must be {from_version}';
  END IF;
END $$;

-- Migration
BEGIN TRANSACTION;

-- TODO: Add migration steps here
-- Example:
-- ALTER TABLE fact_landuse_transitions ADD COLUMN new_column VARCHAR(100);

-- Update version
INSERT INTO schema_version (version_number, description, applied_by)
VALUES ('{to_version}', 'TODO: Description', 'migration_system');

COMMIT;

-- Post-migration validation
SELECT 'Migration to v{to_version} successful' WHERE EXISTS (
  SELECT 1 FROM schema_version
  WHERE version_number = '{to_version}'
);
"""

    migration_file.write_text(template)
    console.print(f"[green]✓ Created migration template: {migration_file}[/green]")
    console.print("Edit the file to add your migration steps")


if __name__ == "__main__":
    from datetime import datetime

    cli()
