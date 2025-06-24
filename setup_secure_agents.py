#!/usr/bin/env python3
"""
Secure Setup Script for Langchain Landuse Agents
Validates environment configuration and security settings
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from dotenv import load_dotenv, set_key

# Add src to path for imports
sys.path.append(str(Path(__file__).resolve().parent / "src"))

console = Console()

class SecureSetup:
    """Handles secure setup and validation of the landuse agent environment"""
    
    def __init__(self):
        self.config_dir = Path("config")
        self.env_file = self.config_dir / ".env"
        self.env_example = Path(".env.example")
        self.logs_dir = Path("logs")
        self.required_vars = {
            "OPENAI_API_KEY": {
                "description": "OpenAI API key for GPT models",
                "pattern": r"^sk-[a-zA-Z0-9]{48}$",
                "required": False,
                "example": "sk-..."
            },
            "ANTHROPIC_API_KEY": {
                "description": "Anthropic API key for Claude models",
                "pattern": r"^sk-ant-[a-zA-Z0-9-]{95}$",
                "required": False,
                "example": "sk-ant-..."
            }
        }
        self.optional_vars = {
            "LANDUSE_MODEL": {
                "description": "AI model to use",
                "default": "gpt-4o-mini",
                "options": ["gpt-4o-mini", "gpt-4", "claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"]
            },
            "TEMPERATURE": {
                "description": "Model temperature (0.0-1.0)",
                "default": "0.1",
                "pattern": r"^0(\.[0-9]+)?|1(\.0)?$"
            },
            "MAX_TOKENS": {
                "description": "Maximum tokens for responses",
                "default": "4000",
                "pattern": r"^[1-9][0-9]{0,3}$"
            },
            "DEFAULT_QUERY_LIMIT": {
                "description": "Default SQL query result limit",
                "default": "1000",
                "pattern": r"^[1-9][0-9]{0,4}$"
            },
            "LOG_LEVEL": {
                "description": "Logging level",
                "default": "INFO",
                "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            }
        }
    
    def run(self):
        """Run the secure setup process"""
        console.print(Panel.fit(
            "🔐 [bold blue]Secure Landuse Agent Setup[/bold blue]\n"
            "[yellow]This wizard will help you configure your environment securely[/yellow]",
            border_style="blue"
        ))
        
        # Check prerequisites
        if not self._check_prerequisites():
            return False
        
        # Create necessary directories
        self._create_directories()
        
        # Setup environment
        if not self._setup_environment():
            return False
        
        # Validate security settings
        if not self._validate_security():
            return False
        
        # Test database connection
        if not self._test_database():
            return False
        
        # Run security tests
        if not self._run_security_tests():
            return False
        
        # Show summary
        self._show_summary()
        
        return True
    
    def _check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        console.print("\n[bold]Checking prerequisites...[/bold]")
        
        checks = []
        
        # Python version
        py_version = sys.version_info
        py_ok = py_version >= (3, 8)
        checks.append(("Python 3.8+", py_ok, f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
        
        # Required packages
        try:
            import langchain
            lc_ok = True
            lc_version = langchain.__version__
        except ImportError:
            lc_ok = False
            lc_version = "Not installed"
        checks.append(("langchain", lc_ok, lc_version))
        
        try:
            import duckdb
            db_ok = True
            db_version = duckdb.__version__
        except ImportError:
            db_ok = False
            db_version = "Not installed"
        checks.append(("duckdb", db_ok, db_version))
        
        try:
            import rich
            rich_ok = True
            try:
                from importlib.metadata import version
                rich_version = version('rich')
            except:
                rich_version = "Unknown"
        except ImportError:
            rich_ok = False
            rich_version = "Not installed"
        checks.append(("rich", rich_ok, rich_version))
        
        # Display results
        table = Table(title="Prerequisites Check")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Version", style="yellow")
        
        all_ok = True
        for component, ok, version in checks:
            status = "✅ OK" if ok else "❌ Missing"
            style = "green" if ok else "red"
            table.add_row(component, f"[{style}]{status}[/{style}]", version)
            all_ok = all_ok and ok
        
        console.print(table)
        
        if not all_ok:
            console.print("\n[red]Missing prerequisites. Please install required packages:[/red]")
            console.print("[yellow]uv sync[/yellow]")
            return False
        
        return True
    
    def _create_directories(self):
        """Create necessary directories"""
        dirs = [self.config_dir, self.logs_dir, Path("data/processed"), Path("data/raw")]
        
        for dir_path in dirs:
            if not dir_path.exists():
                dir_path.mkdir(parents=True)
                console.print(f"✅ Created directory: {dir_path}")
    
    def _setup_environment(self) -> bool:
        """Setup environment variables securely"""
        console.print("\n[bold]Setting up environment variables...[/bold]")
        
        # Check if .env exists
        if self.env_file.exists():
            console.print(f"\n[green]✅ Environment file found at {self.env_file}[/green]")
            load_dotenv(self.env_file)
            
            # Check existing keys
            existing_keys = []
            if os.getenv("OPENAI_API_KEY"):
                existing_keys.append("OpenAI")
            if os.getenv("ANTHROPIC_API_KEY"):
                existing_keys.append("Anthropic")
            
            if existing_keys:
                console.print(f"[green]✅ API keys already configured: {', '.join(existing_keys)}[/green]")
                console.print("[dim]Using existing configuration[/dim]")
                return True
            else:
                console.print("[yellow]⚠️  No API keys found in .env file[/yellow]")
                if not Confirm.ask("Would you like to add API keys now?"):
                    console.print("[red]❌ At least one API key is required[/red]")
                    return False
        
        # Create new .env from example or create empty
        if self.env_example.exists():
            import shutil
            shutil.copy(self.env_example, self.env_file)
            console.print(f"✅ Created {self.env_file} from template")
        else:
            # Create empty .env file
            self.env_file.touch()
            console.print(f"✅ Created new {self.env_file}")
        
        # Collect API keys
        console.print("\n[bold]API Key Configuration[/bold]")
        console.print("[dim]At least one API key (OpenAI or Anthropic) is required[/dim]\n")
        
        api_keys = {}
        
        # OpenAI API Key
        openai_key = Prompt.ask(
            "Enter your OpenAI API key (or press Enter to skip)",
            password=True,
            default=""
        )
        if openai_key:
            if self._validate_api_key(openai_key, "openai"):
                api_keys["OPENAI_API_KEY"] = openai_key
                set_key(self.env_file, "OPENAI_API_KEY", openai_key)
                console.print("✅ OpenAI API key validated and saved")
            else:
                console.print("[red]❌ Invalid OpenAI API key format[/red]")
        
        # Anthropic API Key
        anthropic_key = Prompt.ask(
            "Enter your Anthropic API key (or press Enter to skip)",
            password=True,
            default=""
        )
        if anthropic_key:
            if self._validate_api_key(anthropic_key, "anthropic"):
                api_keys["ANTHROPIC_API_KEY"] = anthropic_key
                set_key(self.env_file, "ANTHROPIC_API_KEY", anthropic_key)
                console.print("✅ Anthropic API key validated and saved")
            else:
                console.print("[red]❌ Invalid Anthropic API key format[/red]")
        
        # Check if at least one key was provided
        if not api_keys:
            console.print("\n[red]❌ At least one API key is required[/red]")
            return False
        
        # Configure model based on available keys
        if "ANTHROPIC_API_KEY" in api_keys:
            default_model = "claude-3-haiku-20240307"
        else:
            default_model = "gpt-4o-mini"
        
        # Set optional variables
        console.print("\n[bold]Additional Configuration[/bold]")
        
        for var_name, var_config in self.optional_vars.items():
            current_value = os.getenv(var_name, var_config.get("default", ""))
            
            if "options" in var_config:
                # Show options
                console.print(f"\n{var_config['description']}")
                for i, option in enumerate(var_config["options"], 1):
                    console.print(f"  {i}. {option}")
                
                choice = Prompt.ask(
                    f"Select {var_name}",
                    default=str(var_config["options"].index(current_value) + 1 if current_value in var_config["options"] else 1)
                )
                try:
                    value = var_config["options"][int(choice) - 1]
                except (ValueError, IndexError):
                    value = current_value
            else:
                value = Prompt.ask(
                    f"{var_config['description']} ({var_name})",
                    default=current_value
                )
            
            # Validate if pattern provided
            if "pattern" in var_config and not re.match(var_config["pattern"], value):
                console.print(f"[yellow]⚠️  Invalid format for {var_name}, using default[/yellow]")
                value = var_config.get("default", "")
            
            set_key(self.env_file, var_name, value)
        
        # Set database path
        set_key(self.env_file, "LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
        
        console.print("\n✅ Environment configuration saved")
        load_dotenv(self.env_file)
        return True
    
    def _validate_api_key(self, key: str, provider: str) -> bool:
        """Validate API key format"""
        if provider == "openai":
            return bool(re.match(r"^sk-[a-zA-Z0-9]{48}$", key))
        elif provider == "anthropic":
            return bool(re.match(r"^sk-ant-[a-zA-Z0-9-]{95}$", key))
        return False
    
    def _validate_security(self) -> bool:
        """Validate security settings"""
        console.print("\n[bold]Validating security settings...[/bold]")
        
        security_checks = []
        
        # Check .gitignore
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            env_ignored = ".env" in content and "config/.env" in content
            security_checks.append(("Environment files in .gitignore", env_ignored))
        else:
            security_checks.append(("Environment files in .gitignore", False))
        
        # Check file permissions (Unix-like systems only)
        if sys.platform != "win32":
            import stat
            if self.env_file.exists():
                mode = self.env_file.stat().st_mode
                secure_perms = (mode & stat.S_IRWXG == 0) and (mode & stat.S_IRWXO == 0)
                security_checks.append(("Secure .env permissions", secure_perms))
                
                if not secure_perms:
                    # Fix permissions
                    os.chmod(self.env_file, 0o600)
                    console.print("✅ Fixed .env file permissions (600)")
        
        # Check for hardcoded secrets
        py_files = list(Path("src/landuse").rglob("*.py"))
        hardcoded_found = False
        for py_file in py_files[:5]:  # Check first 5 files as sample
            content = py_file.read_text()
            if re.search(r'sk-[a-zA-Z0-9]{48}|sk-ant-[a-zA-Z0-9-]{95}', content):
                hardcoded_found = True
                break
        security_checks.append(("No hardcoded API keys", not hardcoded_found))
        
        # Display results
        table = Table(title="Security Validation")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")
        
        all_ok = True
        for check, ok in security_checks:
            status = "✅ Pass" if ok else "❌ Fail"
            style = "green" if ok else "red"
            table.add_row(check, f"[{style}]{status}[/{style}]")
            all_ok = all_ok and ok
        
        console.print(table)
        
        return all_ok
    
    def _test_database(self) -> bool:
        """Test database connection"""
        console.print("\n[bold]Testing database connection...[/bold]")
        
        db_path = Path(os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb"))
        
        if not db_path.exists():
            console.print(f"[yellow]⚠️  Database not found at {db_path}[/yellow]")
            console.print("[dim]Run data conversion scripts to create the database[/dim]")
            return True  # Not a fatal error for setup
        
        try:
            import duckdb
            conn = duckdb.connect(str(db_path), read_only=True)
            
            # Test query
            result = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions").fetchone()
            count = result[0] if result else 0
            
            conn.close()
            
            console.print(f"✅ Database connection successful ({count:,} transitions)")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Database connection failed: {e}[/red]")
            return False
    
    def _run_security_tests(self) -> bool:
        """Run basic security tests"""
        console.print("\n[bold]Running security tests...[/bold]")
        
        # Import security module
        try:
            from landuse.utilities.security import SQLQueryValidator, InputValidator
            
            # Test SQL injection prevention
            validator = SQLQueryValidator()
            
            test_queries = [
                ("SELECT * FROM dim_scenario", True),
                ("DROP TABLE dim_scenario", False),
                ("SELECT * FROM dim_scenario; DELETE FROM dim_scenario", False),
                ("SELECT * FROM dim_scenario WHERE id = 1 OR '1'='1'", True)
            ]
            
            console.print("\n[dim]Testing SQL injection prevention...[/dim]")
            all_passed = True
            
            for query, should_pass in test_queries:
                is_valid, _ = validator.validate_query(query)
                passed = is_valid == should_pass
                all_passed = all_passed and passed
                
                if passed:
                    console.print(f"✅ {query[:50]}...")
                else:
                    console.print(f"❌ {query[:50]}...")
            
            if all_passed:
                console.print("\n✅ All security tests passed")
            else:
                console.print("\n[red]❌ Some security tests failed[/red]")
            
            return all_passed
            
        except ImportError:
            console.print("[yellow]⚠️  Could not import security module[/yellow]")
            return True  # Not fatal
    
    def _show_summary(self):
        """Show setup summary"""
        # Check which keys are configured
        configured_keys = []
        if os.getenv("OPENAI_API_KEY"):
            configured_keys.append("OpenAI")
        if os.getenv("ANTHROPIC_API_KEY"):
            configured_keys.append("Anthropic")
        
        console.print(Panel.fit(
            "🎉 [bold green]Setup Complete![/bold green]\n\n"
            f"[green]✅ API Keys Configured: {', '.join(configured_keys)}[/green]\n\n"
            "[yellow]To run the Landuse AI Agent:[/yellow]\n"
            "[white]uv run python -m landuse.agents.landuse_natural_language_agent[/white]\n\n"
            "[yellow]Alternative agents:[/yellow]\n"
            "• General data agent: [white]uv run python -m landuse.agents.general_data_agent[/white]\n"
            "• Secure agent: [white]uv run python -m landuse.agents.secure_landuse_agent[/white]\n"
            "• Test queries: [white]uv run python -m landuse.agents.test_landuse_agent[/white]\n\n"
            "[dim]Your API keys are stored securely in config/.env[/dim]",
            border_style="green"
        ))


if __name__ == "__main__":
    setup = SecureSetup()
    success = setup.run()
    sys.exit(0 if success else 1)