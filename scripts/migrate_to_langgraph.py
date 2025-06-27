#!/usr/bin/env python3
"""
Migration script to transition from traditional LangChain agents to LangGraph architecture.
This script updates imports and provides migration guidance.
"""

import sys
from pathlib import Path
import re
from typing import List, Tuple

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))


def find_files_with_old_imports(root_dir: Path) -> List[Path]:
    """Find all Python files that import the old agents"""
    files_to_migrate = []
    
    patterns = [
        r"from.*landuse\.agents\.base_agent import",
        r"from.*landuse\.agents\.landuse_natural_language_agent import",
        r"from.*landuse\.agents\.langgraph_map_agent import",
        r"import.*landuse\.agents\.base_agent",
        r"import.*landuse\.agents\.landuse_natural_language_agent",
        r"import.*landuse\.agents\.langgraph_map_agent",
        r"BaseLanduseAgent",
        r"LanduseNaturalLanguageAgent",
        r"LangGraphMapAgent"
    ]
    
    for py_file in root_dir.rglob("*.py"):
        # Skip migration-related files
        if "migrate" in py_file.name or "_v2" in py_file.name:
            continue
            
        try:
            content = py_file.read_text()
            for pattern in patterns:
                if re.search(pattern, content):
                    files_to_migrate.append(py_file)
                    break
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return list(set(files_to_migrate))


def create_migration_report(files: List[Path]) -> str:
    """Create a detailed migration report"""
    report = """# LangGraph Migration Report

## Overview
This report outlines the migration from traditional LangChain agents to the modern LangGraph architecture.

## Benefits of LangGraph Architecture:
1. **Better Control Flow**: Graph-based state management
2. **Improved Debugging**: Clear node-based execution
3. **Native Streaming**: Built-in support for streaming responses
4. **Memory/Checkpointing**: Save and restore conversation state
5. **Unified Architecture**: All agents share the same base

## Migration Changes:

### Import Changes:
```python
# Old imports
from landuse.agents.base_agent import BaseLanduseAgent
from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
from landuse.agents.langgraph_map_agent import LangGraphMapAgent

# New imports
from landuse.agents.langgraph_base_agent import BaseLangGraphAgent
from landuse.agents.landuse_natural_language_agent_v2 import LanduseNaturalLanguageAgent
from landuse.agents.langgraph_map_agent_v2 import LangGraphMapAgent
```

### Class Hierarchy Changes:
```
Old:
BaseLanduseAgent (ABC)
├── LanduseNaturalLanguageAgent (LangChain REACT)
└── LangGraphMapAgent (Separate implementation, not inheriting from base)

New:
BaseLangGraphAgent (ABC)
├── LanduseNaturalLanguageAgent (LangGraph)
└── LangGraphMapAgent (extends LanduseNaturalLanguageAgent)
```

### Key API Changes:
1. **Configuration**: Still uses `LanduseConfig`, no changes needed
2. **Query method**: Same signature, but now uses LangGraph internally
3. **Tool creation**: Uses `@tool` decorator instead of Tool class
4. **State management**: Graph-based state instead of agent executor

## Files to Migrate:
"""
    
    for file in sorted(files):
        report += f"- `{file}`\n"
    
    report += f"\nTotal files to migrate: {len(files)}\n"
    
    report += """
## Migration Steps:

### 1. Update Imports (Automated):
Run: `python scripts/migrate_to_langgraph.py --update-imports`

### 2. Update Agent Creation:
No changes needed if using `LanduseConfig`

### 3. Test Thoroughly:
- Run existing tests
- Test Streamlit integration
- Verify map generation still works

### 4. Clean Up:
After successful migration:
- Remove old agent files
- Update documentation
- Update examples

## Backward Compatibility:
The new agents maintain the same public API, so most code should work without changes.
Only the internal implementation has changed to use LangGraph.
"""
    
    return report


def update_imports_in_file(file_path: Path) -> Tuple[bool, str]:
    """Update imports in a single file"""
    try:
        content = file_path.read_text()
        original_content = content
        
        # Define replacements
        replacements = [
            # Base agent imports
            (r"from\s+landuse\.agents\.base_agent\s+import\s+BaseLanduseAgent",
             "from landuse.agents.langgraph_base_agent import BaseLangGraphAgent"),
            (r"from\s+\.base_agent\s+import\s+BaseLanduseAgent",
             "from .langgraph_base_agent import BaseLangGraphAgent"),
            
            # Natural language agent imports
            (r"from\s+landuse\.agents\.landuse_natural_language_agent\s+import",
             "from landuse.agents.landuse_natural_language_agent_v2 import"),
            (r"from\s+\.landuse_natural_language_agent\s+import",
             "from .landuse_natural_language_agent_v2 import"),
            
            # Map agent imports
            (r"from\s+landuse\.agents\.langgraph_map_agent\s+import",
             "from landuse.agents.langgraph_map_agent_v2 import"),
            (r"from\s+\.langgraph_map_agent\s+import",
             "from .langgraph_map_agent_v2 import"),
            
            # Class name updates
            (r"\bBaseLanduseAgent\b", "BaseLangGraphAgent"),
        ]
        
        # Apply replacements
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # Write back if changed
        if content != original_content:
            file_path.write_text(content)
            return True, "Updated successfully"
        else:
            return False, "No changes needed"
            
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate to LangGraph architecture")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--update-imports", action="store_true", help="Actually update the import statements")
    parser.add_argument("--report-only", action="store_true", help="Generate migration report only")
    
    args = parser.parse_args()
    
    # Find project root
    project_root = Path(__file__).parent.parent
    
    print("🔍 Scanning for files to migrate...")
    files_to_migrate = find_files_with_old_imports(project_root)
    
    if args.report_only:
        report = create_migration_report(files_to_migrate)
        report_path = project_root / "LANGGRAPH_MIGRATION.md"
        report_path.write_text(report)
        print(f"✅ Migration report saved to: {report_path}")
        return
    
    if not files_to_migrate:
        print("✅ No files need migration!")
        return
    
    print(f"\n📋 Found {len(files_to_migrate)} files that may need updates:")
    for file in sorted(files_to_migrate):
        print(f"  - {file.relative_to(project_root)}")
    
    if args.dry_run:
        print("\n🔍 Dry run mode - no changes will be made")
        print("\nSuggested changes:")
        print("- Update base_agent imports to langgraph_base_agent")
        print("- Update agent class imports to _v2 versions")
        print("- Update BaseLanduseAgent to BaseLangGraphAgent")
        return
    
    if args.update_imports:
        print("\n🔄 Updating imports...")
        success_count = 0
        for file in files_to_migrate:
            success, message = update_imports_in_file(file)
            if success:
                success_count += 1
                print(f"  ✅ {file.relative_to(project_root)}: {message}")
            else:
                print(f"  ❌ {file.relative_to(project_root)}: {message}")
        
        print(f"\n✅ Successfully updated {success_count}/{len(files_to_migrate)} files")
        
        # Generate report
        report = create_migration_report(files_to_migrate)
        report_path = project_root / "LANGGRAPH_MIGRATION.md"
        report_path.write_text(report)
        print(f"\n📄 Migration report saved to: {report_path}")
    else:
        print("\n💡 To proceed with migration:")
        print("  1. Review files with: python scripts/migrate_to_langgraph.py --dry-run")
        print("  2. Update imports with: python scripts/migrate_to_langgraph.py --update-imports")
        print("  3. Generate report with: python scripts/migrate_to_langgraph.py --report-only")


if __name__ == "__main__":
    main()