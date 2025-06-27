#!/usr/bin/env python3
"""
Script to update imports after agent consolidation.
This updates all references to old agent classes to use the new unified LanduseAgent.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Define import replacements
IMPORT_REPLACEMENTS = [
    # Direct imports
    (r'from landuse\.agents\.base_agent import BaseLanduseAgent',
     'from landuse.agents import LanduseAgent'),
    
    (r'from landuse\.agents\.landuse_natural_language_agent import LanduseNaturalLanguageAgent',
     'from landuse.agents import LanduseAgent'),
    
    (r'from landuse\.agents\.langgraph_agent import LangGraphMapAgent',
     'from landuse.agents import LanduseAgent'),
    
    # Relative imports in same package
    (r'from \.base_agent import BaseLanduseAgent',
     'from .agent import LanduseAgent'),
    
    (r'from \.landuse_natural_language_agent import LanduseNaturalLanguageAgent',
     'from .agent import LanduseAgent'),
    
    # Class instantiations
    (r'\bBaseLanduseAgent\s*\(',
     'LanduseAgent('),
    
    (r'\bLanduseNaturalLanguageAgent\s*\(',
     'LanduseAgent('),
    
    (r'\bLangGraphMapAgent\s*\(',
     'LanduseAgent(enable_maps=True, '),
]

# Files to exclude from migration
EXCLUDE_PATTERNS = [
    '*.pyc',
    '__pycache__',
    '.git',
    'node_modules',
    'venv',
    '.venv',
    'migrations',
    'compat.py',  # Don't update the compatibility file
    'consolidate_agents.py',  # Don't update this script
]


def should_process_file(file_path: Path) -> bool:
    """Check if file should be processed"""
    # Check exclusion patterns
    for pattern in EXCLUDE_PATTERNS:
        if pattern in str(file_path):
            return False
    
    # Only process Python files
    return file_path.suffix == '.py'


def update_file(file_path: Path, dry_run: bool = True) -> List[Tuple[str, str]]:
    """Update imports in a single file"""
    changes = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Apply replacements
        for old_pattern, new_pattern in IMPORT_REPLACEMENTS:
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_pattern, content)
                changes.append((old_pattern, new_pattern))
        
        # Only write if changes were made
        if content != original_content and not dry_run:
            with open(file_path, 'w') as f:
                f.write(content)
        
        return changes
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def find_files_to_update(root_dir: Path) -> List[Path]:
    """Find all Python files that might need updating"""
    files = []
    
    for path in root_dir.rglob('*.py'):
        if should_process_file(path):
            files.append(path)
    
    return files


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update imports after agent consolidation")
    parser.add_argument('--dry-run', action='store_true', 
                       help="Show what would be changed without modifying files")
    parser.add_argument('--root', default='.', 
                       help="Root directory to search (default: current directory)")
    
    args = parser.parse_args()
    
    root_path = Path(args.root).resolve()
    print(f"🔍 Searching for files to update in: {root_path}")
    
    files = find_files_to_update(root_path)
    print(f"📁 Found {len(files)} Python files to check")
    
    files_changed = 0
    total_changes = 0
    
    for file_path in files:
        changes = update_file(file_path, dry_run=args.dry_run)
        
        if changes:
            files_changed += 1
            total_changes += len(changes)
            
            print(f"\n✏️  {file_path.relative_to(root_path)}")
            for old, new in changes:
                print(f"   {old} → {new}")
    
    if args.dry_run:
        print(f"\n🔍 Dry run complete: Would update {files_changed} files with {total_changes} changes")
        print("Run without --dry-run to apply changes")
    else:
        print(f"\n✅ Updated {files_changed} files with {total_changes} changes")
        
        # Additional instructions
        if files_changed > 0:
            print("\n📋 Next steps:")
            print("1. Review the changes")
            print("2. Run tests to ensure everything works")
            print("3. Update any documentation that references old class names")
            print("4. Consider removing old agent files after verification")


if __name__ == "__main__":
    main()