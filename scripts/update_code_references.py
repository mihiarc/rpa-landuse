#!/usr/bin/env python3
"""
Update all code references from dim_geography to dim_geography
"""

import os
import re
from pathlib import Path


def update_file(file_path: Path, dry_run: bool = True):
    """Update references in a single file"""

    with open(file_path) as f:
        content = f.read()

    original_content = content

    # Pattern to match dim_geography but not dim_geography
    # Uses negative lookahead to avoid double replacement
    patterns = [
        (r'\bdim_geography\b(?!_enhanced)', 'dim_geography'),
    ]

    changes = []
    for pattern, replacement in patterns:
        matches = list(re.finditer(pattern, content))
        if matches:
            for match in reversed(matches):  # Process in reverse to maintain positions
                start, end = match.span()
                line_num = content[:start].count('\n') + 1
                line_start = content.rfind('\n', 0, start) + 1
                line_end = content.find('\n', end)
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end]

                changes.append({
                    'line': line_num,
                    'text': line.strip(),
                    'match': match.group()
                })

            content = re.sub(pattern, replacement, content)

    if changes and content != original_content:
        if not dry_run:
            with open(file_path, 'w') as f:
                f.write(content)
        return changes

    return None

def update_all_references(base_path: Path, dry_run: bool = True):
    """Update all references in the codebase"""

    # Directories to search
    search_dirs = ['src', 'pages', 'scripts']

    print(f"{'DRY RUN' if dry_run else 'UPDATING'} CODE REFERENCES\n")

    total_changes = 0
    files_changed = 0

    for dir_name in search_dirs:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob('*.py'):
            # Skip this script and migration scripts
            if file_path.name in ['update_code_references.py', 'migrate_to_enhanced_geography.py',
                                 'simplify_geography_table.py', 'simplify_database_complete.py']:
                continue

            changes = update_file(file_path, dry_run)

            if changes:
                files_changed += 1
                print(f"\n📄 {file_path.relative_to(base_path)}:")
                for change in changes:
                    print(f"   Line {change['line']}: {change['match']} → dim_geography")
                    print(f"   Context: {change['text'][:80]}...")
                total_changes += len(changes)

    print(f"\n{'Would update' if dry_run else 'Updated'}: {total_changes} references in {files_changed} files")

    if dry_run and total_changes > 0:
        print("\nRun with --apply to make these changes")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Update code references to use dim_geography')
    parser.add_argument('--apply', action='store_true', help='Actually make the changes (default is dry run)')
    parser.add_argument('--path', default='.', help='Base path to search from')

    args = parser.parse_args()

    base_path = Path(args.path).resolve()
    update_all_references(base_path, dry_run=not args.apply)

if __name__ == "__main__":
    main()
