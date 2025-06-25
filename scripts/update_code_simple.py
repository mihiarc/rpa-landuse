#!/usr/bin/env python3
"""
Update all code references from dim_geography_enhanced back to dim_geography
"""

import os
import re
from pathlib import Path

def update_file(file_path: Path, dry_run: bool = True):
    """Update references in a single file"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Simple replacement - change dim_geography_enhanced to dim_geography
    content = content.replace('dim_geography_enhanced', 'dim_geography')
    
    if content != original_content:
        if not dry_run:
            with open(file_path, 'w') as f:
                f.write(content)
        
        # Count changes
        changes = original_content.count('dim_geography_enhanced')
        return changes
    
    return 0

def update_all_references(base_path: Path, dry_run: bool = True):
    """Update all references in the codebase"""
    
    # Directories to search
    search_dirs = ['src', 'pages', 'scripts']
    
    print(f"{'DRY RUN' if dry_run else 'UPDATING'} CODE TO SIMPLE NOMENCLATURE\n")
    
    total_changes = 0
    files_changed = 0
    
    for dir_name in search_dirs:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            continue
            
        for file_path in dir_path.rglob('*.py'):
            # Skip this script and the rename script
            if file_path.name in ['update_code_simple.py', 'rename_geography_table.py']:
                continue
                
            changes = update_file(file_path, dry_run)
            
            if changes > 0:
                files_changed += 1
                print(f"📄 {file_path.relative_to(base_path)}: {changes} occurrences")
                total_changes += changes
    
    print(f"\n{'Would update' if dry_run else 'Updated'}: {total_changes} references in {files_changed} files")
    
    if dry_run and total_changes > 0:
        print("\nRun with --apply to make these changes")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update code to use simple dim_geography')
    parser.add_argument('--apply', action='store_true', help='Actually make the changes (default is dry run)')
    parser.add_argument('--path', default='.', help='Base path to search from')
    
    args = parser.parse_args()
    
    base_path = Path(args.path).resolve()
    update_all_references(base_path, dry_run=not args.apply)

if __name__ == "__main__":
    main()