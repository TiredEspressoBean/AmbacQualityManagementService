#!/usr/bin/env python
"""
Script to remove redundant .for_user(self.request.user) calls from viewsets.

Since TenantScopedMixin.get_queryset() now calls for_user() automatically,
viewsets that call super().get_queryset() don't need to call it again.

This script removes .for_user(self.request.user) from lines where:
- The call is on a variable (qs, queryset) not on Model.objects
- Preserves any chained methods like .select_related(), .filter(), etc.

Run with --dry-run to preview changes without modifying files.
"""

import re
import sys
from pathlib import Path

# Pattern to match .for_user(self.request.user) that should be removed
# This matches when for_user is called on a variable (qs, queryset, etc.)
# but NOT when called on Model.objects.for_user()
PATTERN = re.compile(
    r'(\b(?:qs|queryset)\b)'  # Variable name (qs or queryset)
    r'\.for_user\(self\.request\.user\)'  # .for_user(self.request.user)
)

# Also handle the multiline case where .for_user is on its own line
MULTILINE_PATTERN = re.compile(
    r'(\s+)\.for_user\(self\.request\.user\)(\s*\n)'
)

def process_file(filepath, dry_run=True):
    """Process a single file, removing redundant for_user calls."""
    content = filepath.read_text()
    original = content
    changes = []

    # Pattern 1: qs.for_user(self.request.user) - replace with just the variable
    def replace_inline(match):
        var_name = match.group(1)
        changes.append(f"  Removed .for_user() from {var_name}")
        return var_name

    content = PATTERN.sub(replace_inline, content)

    # Pattern 2: Standalone line with just .for_user(self.request.user)
    # This handles cases like:
    #     queryset = queryset.for_user(self.request.user)
    # After pattern 1, this becomes:
    #     queryset = queryset
    # Which we should simplify or the line was already:
    #     .for_user(self.request.user)
    # on its own line (multiline chaining)

    # Remove lines that are just "queryset = queryset" or "qs = qs"
    content = re.sub(r'\n(\s+)(qs|queryset) = \2\n', r'\n', content)

    # Remove standalone .for_user lines in multiline chains
    content = re.sub(
        r'\n(\s+)\.for_user\(self\.request\.user\)(?=\s*\n)',
        '',
        content
    )

    if content != original:
        if dry_run:
            print(f"\n{filepath}:")
            for change in changes:
                print(change)
            # Show diff
            import difflib
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=str(filepath),
                tofile=str(filepath),
                lineterm=''
            )
            print(''.join(list(diff)[:50]))  # Show first 50 lines of diff
        else:
            filepath.write_text(content)
            print(f"Updated {filepath}")
        return True
    return False


def main():
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    viewsets_dir = Path(__file__).parent / 'Tracker' / 'viewsets'

    files_changed = 0
    for filepath in viewsets_dir.glob('*.py'):
        if filepath.name == '__init__.py':
            continue
        if process_file(filepath, dry_run=dry_run):
            files_changed += 1

    print(f"\n{'Would update' if dry_run else 'Updated'} {files_changed} files")

    if dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == '__main__':
    main()
