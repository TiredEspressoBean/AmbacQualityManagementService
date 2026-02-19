#!/usr/bin/env python3
"""
Analyze API field usage and cost across frontend codebase.

Two analysis modes:
1. USAGE: Finds fields returned by Django serializers that aren't used in React frontend
2. COST: Identifies expensive fields that trigger database queries (N+1 risks)

Usage:
    python scripts/find_unused_api_fields.py                    # Full analysis
    python scripts/find_unused_api_fields.py --serializer Parts # Filter to specific serializer
    python scripts/find_unused_api_fields.py --usage-only       # Only unused field analysis
    python scripts/find_unused_api_fields.py --cost-only        # Only cost analysis
    python scripts/find_unused_api_fields.py --verbose          # Show all details
"""

import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FieldUsage:
    """Track usage of a single field"""
    field_name: str
    serializer: str
    used_in_files: list = field(default_factory=list)

    @property
    def is_used(self) -> bool:
        return len(self.used_in_files) > 0


@dataclass
class FieldCost:
    """Cost analysis for a single field"""
    name: str
    field_type: str
    cost_level: str  # 'free', 'cheap', 'moderate', 'expensive'
    reasons: list = field(default_factory=list)
    db_calls: list = field(default_factory=list)
    nested_depth: int = 0


@dataclass
class SerializerAnalysis:
    """Combined analysis results for one serializer"""
    name: str
    file_path: str = ""

    # All fields
    fields: list = field(default_factory=list)

    # Usage analysis
    used_fields: set = field(default_factory=set)
    unused_fields: set = field(default_factory=set)
    usage_map: dict = field(default_factory=dict)  # field -> [files]

    # Cost analysis
    field_costs: list = field(default_factory=list)  # List of FieldCost
    expensive_fields: int = 0
    moderate_fields: int = 0
    has_n_plus_1_risk: bool = False

    def get_usage_count(self, field_name: str) -> int:
        """Get number of files using this field"""
        return len(self.usage_map.get(field_name, []))

    def get_usage_category(self, field_name: str) -> str:
        """Categorize field usage: unused, rare, moderate, heavy"""
        count = self.get_usage_count(field_name)
        if count == 0:
            return "unused"
        elif count <= 2:
            return "rare"
        elif count <= 5:
            return "moderate"
        else:
            return "heavy"

    def get_fields_by_usage(self) -> dict:
        """Group fields by usage category"""
        categories = {"unused": [], "rare": [], "moderate": [], "heavy": []}
        for f in self.fields:
            cat = self.get_usage_category(f)
            categories[cat].append((f, self.get_usage_count(f)))
        return categories

    def get_field_cost(self, field_name: str) -> str:
        """Get cost level for a field"""
        for fc in self.field_costs:
            if fc.name == field_name:
                return fc.cost_level
        return "cheap"

    def get_removal_priority(self, field_name: str) -> tuple:
        """
        Calculate removal priority score.
        Returns (score, usage_count, cost_level) for sorting.
        Higher score = better candidate for removal.

        Score = (inverse usage) * cost_multiplier
        """
        usage = self.get_usage_count(field_name)
        cost = self.get_field_cost(field_name)

        cost_multipliers = {"expensive": 10, "moderate": 5, "cheap": 1}
        cost_mult = cost_multipliers.get(cost, 1)

        # Inverse usage: unused=100, rare(1-2)=50, moderate(3-5)=10, heavy=1
        if usage == 0:
            usage_score = 100
        elif usage <= 2:
            usage_score = 50
        elif usage <= 5:
            usage_score = 10
        else:
            usage_score = 1

        score = usage_score * cost_mult
        return (score, usage, cost)

    def get_ranked_removal_candidates(self) -> list:
        """
        Get fields ranked by removal priority.
        Returns [(field_name, score, usage_count, cost_level), ...] sorted by score desc
        """
        candidates = []
        for f in self.fields:
            score, usage, cost = self.get_removal_priority(f)
            candidates.append((f, score, usage, cost))

        # Sort by score descending (best removal candidates first)
        return sorted(candidates, key=lambda x: -x[1])


# ============================================================================
# COST ANALYSIS PATTERNS
# ============================================================================

# Patterns that indicate database access in SerializerMethodField
# Grouped by fix type for better recommendations
DB_ACCESS_PATTERNS_ANNOTATE = [
    # These should be fixed with queryset annotations
    (r'\.count\(\)', 'count() - use annotate(Count())'),
    (r'\.exists\(\)', 'exists() - use annotate() or Exists()'),
]

DB_ACCESS_PATTERNS_PREFETCH = [
    # These need prefetch_related for reverse FKs / M2M
    (r'\.filter\(', 'filter() - use prefetch_related'),
    (r'\.exclude\(', 'exclude() - use prefetch_related'),
    (r'\.all\(\)', 'all() - use prefetch_related'),
]

DB_ACCESS_PATTERNS_OTHER = [
    # Other DB access
    (r'\.get\(', 'get()'),
    (r'\.first\(\)', 'first()'),
    (r'\.last\(\)', 'last()'),
    (r'\.values', 'values()'),
    (r'\.objects\.', 'Manager query'),
]

# Combined for detection
DB_ACCESS_PATTERNS = DB_ACCESS_PATTERNS_ANNOTATE + DB_ACCESS_PATTERNS_PREFETCH + DB_ACCESS_PATTERNS_OTHER

# Patterns indicating nested object access (potential N+1)
# These are fixed by select_related
NESTED_ACCESS_PATTERNS = [
    r'obj\.\w+\.\w+\.\w+',  # obj.order.customer.company - deep traversal (3 levels)
    r'obj\.\w+\.\w+',       # obj.order.customer - traversing FKs (2 levels)
]


# ============================================================================
# SERIALIZER EXTRACTION
# ============================================================================

def extract_method_body(content: str, method_name: str) -> Optional[str]:
    """Extract the body of a method from class content"""
    pattern = rf'def\s+{method_name}\s*\([^)]*\):[^\n]*\n((?:[ \t]+[^\n]*\n)*)'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None


def extract_serializers(serializer_dir: Path) -> dict[str, SerializerAnalysis]:
    """
    Extract field names and analyze cost from Django serializers.
    Returns: { 'PartsSerializer': SerializerAnalysis, ... }
    """
    serializers = {}

    for py_file in serializer_dir.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue

        content = py_file.read_text(encoding='utf-8', errors='ignore')

        # Find class definitions
        class_pattern = r'class\s+(\w+Serializer)\s*\([^)]*\):'

        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            class_start = match.end()

            # Find the next class or end of file
            next_class = re.search(r'\nclass\s+\w+', content[class_start:])
            class_end = class_start + next_class.start() if next_class else len(content)
            class_body = content[class_start:class_end]

            analysis = SerializerAnalysis(name=class_name, file_path=str(py_file))
            fields = set()
            field_costs = []

            # ---- EXTRACT FIELDS ----

            # Method 1: Extract from fields = (...) or fields = [...]
            fields_match = re.search(r'fields\s*=\s*[\(\[]([^\)\]]+)[\)\]]', class_body)
            if fields_match:
                fields_str = fields_match.group(1)
                field_names = re.findall(r"['\"](\w+)['\"]", fields_str)
                fields.update(field_names)

            # Method 2: Extract SerializerMethodField declarations
            method_fields = re.findall(r'(\w+)\s*=\s*serializers\.SerializerMethodField', class_body)
            fields.update(method_fields)

            # Method 3: Extract other field declarations
            other_fields = re.findall(r'(\w+)\s*=\s*serializers\.\w+Field', class_body)
            fields.update(other_fields)

            # ---- ANALYZE COST ----

            # Analyze SerializerMethodFields for DB access
            for field_name in method_fields:
                method_name = f'get_{field_name}'
                method_body = extract_method_body(class_body, method_name)

                field_cost = FieldCost(name=field_name, field_type='SerializerMethodField', cost_level='cheap')

                if method_body:
                    # Check for DB access patterns
                    for pattern, desc in DB_ACCESS_PATTERNS:
                        if re.search(pattern, method_body):
                            field_cost.db_calls.append(desc)
                            field_cost.cost_level = 'expensive'
                            field_cost.reasons.append(f'DB: {desc}')

                    # Check for nested access (N+1 risk)
                    for pattern in NESTED_ACCESS_PATTERNS:
                        matches = re.findall(pattern, method_body)
                        if matches:
                            if field_cost.cost_level != 'expensive':
                                field_cost.cost_level = 'moderate'
                            depth = max(m.count('.') for m in matches)
                            field_cost.reasons.append(f'FK traversal depth={depth}')
                            field_cost.nested_depth = depth
                            analysis.has_n_plus_1_risk = True

                field_costs.append(field_cost)

            # Analyze source= fields
            source_fields = re.findall(r"(\w+)\s*=.*source=['\"]([^'\"]+)['\"]", class_body)
            for field_name, source in source_fields:
                fields.add(field_name)
                depth = source.count('.')
                cost_level = 'cheap' if depth == 0 else ('moderate' if depth == 1 else 'expensive')

                field_cost = FieldCost(
                    name=field_name,
                    field_type='source_field',
                    cost_level=cost_level,
                    nested_depth=depth,
                    reasons=[f'source={source}'] if depth > 0 else []
                )
                if depth > 0:
                    analysis.has_n_plus_1_risk = True
                field_costs.append(field_cost)

            # Analyze nested serializers
            nested_serializers = re.findall(r'(\w+)\s*=\s*(\w+Serializer)\s*\(', class_body)
            for field_name, serializer_type in nested_serializers:
                fields.add(field_name)
                field_cost = FieldCost(
                    name=field_name,
                    field_type='nested_serializer',
                    cost_level='expensive',
                    reasons=[f'Nested {serializer_type}']
                )
                field_costs.append(field_cost)
                analysis.has_n_plus_1_risk = True

            # Store results
            analysis.fields = sorted(fields)
            analysis.field_costs = field_costs
            analysis.expensive_fields = sum(1 for f in field_costs if f.cost_level == 'expensive')
            analysis.moderate_fields = sum(1 for f in field_costs if f.cost_level == 'moderate')

            if fields:
                serializers[class_name] = analysis

    return serializers


# ============================================================================
# FRONTEND USAGE ANALYSIS
# ============================================================================

def extract_generated_types(generated_ts: Path) -> dict[str, list[str]]:
    """Extract field names from generated TypeScript types."""
    types = {}

    if not generated_ts.exists():
        return types

    content = generated_ts.read_text(encoding='utf-8')

    # Find schema definitions
    schema_pattern = r'(\w+):\s*z\.object\(\{([^}]+)\}\)'
    for match in re.finditer(schema_pattern, content, re.DOTALL):
        type_name = match.group(1)
        fields_block = match.group(2)
        field_names = re.findall(r'(\w+):\s*z\.', fields_block)
        if field_names:
            types[type_name] = field_names

    return types


def find_field_usage_in_frontend(frontend_dir: Path, serializers: dict[str, SerializerAnalysis]) -> None:
    """Scan frontend code for usage of API fields. Modifies serializers in place."""

    # Build a flat map of all fields we're looking for
    all_fields = set()
    field_to_serializers = defaultdict(list)

    for name, analysis in serializers.items():
        for f in analysis.fields:
            all_fields.add(f)
            field_to_serializers[f].append(name)

    # Access patterns for React/TypeScript
    access_patterns = [
        r'\.({field})\b',
        r'\[[\'"]{field}[\'"]\]',
        r'{{\s*{field}\s*}}',
        r':\s*{field}\b',
        r'{field}\s*:',
        r'{field}\s*,',
    ]

    # Files to skip (auto-generated, don't reflect actual usage)
    skip_patterns = [
        'node_modules',
        '.next',
        'generated.ts',      # OpenAPI generated - has everything
        'generated.d.ts',
        '.generated.',
        'schema.ts',
    ]

    extensions = {'.tsx', '.ts', '.jsx', '.js'}

    for file_path in frontend_dir.rglob('*'):
        if file_path.suffix not in extensions:
            continue

        # Skip auto-generated files
        path_str = str(file_path)
        if any(skip in path_str for skip in skip_patterns):
            continue

        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            continue

        relative_path = file_path.relative_to(frontend_dir)

        for field_name in all_fields:
            # Skip generic names - require specific patterns
            if field_name in {'id', 'name', 'type', 'data', 'value', 'label', 'status', 'key'}:
                patterns = [rf'\.{field_name}\b', rf'\[[\'"]{field_name}[\'"]\]']
            else:
                patterns = [p.format(field=field_name) for p in access_patterns]

            for pattern in patterns:
                if re.search(pattern, content):
                    for serializer in field_to_serializers[field_name]:
                        if field_name not in serializers[serializer].usage_map:
                            serializers[serializer].usage_map[field_name] = []
                        if str(relative_path) not in serializers[serializer].usage_map[field_name]:
                            serializers[serializer].usage_map[field_name].append(str(relative_path))
                    break

    # Calculate used/unused
    for analysis in serializers.values():
        analysis.used_fields = set(analysis.usage_map.keys())
        analysis.unused_fields = set(analysis.fields) - analysis.used_fields


# ============================================================================
# REPORTING
# ============================================================================

def print_report(
    serializers: dict[str, SerializerAnalysis],
    show_usage: bool = True,
    show_cost: bool = True,
    verbose: bool = False,
    min_unused: int = 3
):
    """Print combined analysis report"""

    print("=" * 70)
    print("API FIELD ANALYSIS REPORT")
    print("=" * 70)
    print()

    # ---- SUMMARY STATS ----
    total_fields = sum(len(a.fields) for a in serializers.values())
    total_unused = sum(len(a.unused_fields) for a in serializers.values())
    total_expensive = sum(a.expensive_fields for a in serializers.values())
    total_moderate = sum(a.moderate_fields for a in serializers.values())
    n_plus_1_count = sum(1 for a in serializers.values() if a.has_n_plus_1_risk)

    print(f"Serializers analyzed: {len(serializers)}")
    print(f"Total fields: {total_fields}")
    print()

    if show_usage:
        print(f"USAGE: Potentially unused fields: {total_unused} ({total_unused/total_fields*100:.1f}%)")

    if show_cost:
        print(f"COST: Expensive fields: {total_expensive}, Moderate: {total_moderate}")
        print(f"N+1 RISK: {n_plus_1_count} serializers")

    print()

    # ---- COST ANALYSIS ----
    if show_cost:
        print("-" * 70)
        print("EXPENSIVE SERIALIZERS (by query cost)")
        print("-" * 70)
        print()

        # Sort by expensive fields
        by_cost = sorted(serializers.values(), key=lambda x: (x.expensive_fields, x.moderate_fields), reverse=True)

        for analysis in by_cost[:10]:
            if analysis.expensive_fields == 0 and analysis.moderate_fields == 0:
                continue

            risk = " [N+1 RISK]" if analysis.has_n_plus_1_risk else ""
            print(f"### {analysis.name}{risk}")
            print(f"    Expensive: {analysis.expensive_fields} | Moderate: {analysis.moderate_fields}")

            expensive = [f for f in analysis.field_costs if f.cost_level == 'expensive']
            if expensive:
                print("    [!] EXPENSIVE (need prefetch_related or annotate):")
                for f in expensive[:5]:
                    reasons = ', '.join(f.reasons[:2]) if f.reasons else f.field_type
                    print(f"        {f.name}: {reasons}")
                if len(expensive) > 5:
                    print(f"        ... and {len(expensive)-5} more")

            if verbose:
                moderate = [f for f in analysis.field_costs if f.cost_level == 'moderate']
                if moderate:
                    print("    [~] MODERATE (fixed by select_related):")
                    for f in moderate:
                        reasons = ', '.join(f.reasons) if f.reasons else f.field_type
                        print(f"        {f.name}: {reasons}")

            print()

    # ---- USAGE ANALYSIS ----
    if show_usage:
        print("-" * 70)
        print("FIELD USAGE BY COUNT")
        print("-" * 70)
        print()

        # Global stats by category
        all_unused = sum(len(a.get_fields_by_usage()["unused"]) for a in serializers.values())
        all_rare = sum(len(a.get_fields_by_usage()["rare"]) for a in serializers.values())
        all_moderate = sum(len(a.get_fields_by_usage()["moderate"]) for a in serializers.values())
        all_heavy = sum(len(a.get_fields_by_usage()["heavy"]) for a in serializers.values())

        print(f"Usage distribution across all serializers:")
        print(f"  [0 uses]   Unused:   {all_unused:4d} fields - SAFE TO REMOVE")
        print(f"  [1-2 uses] Rare:     {all_rare:4d} fields - review if needed")
        print(f"  [3-5 uses] Moderate: {all_moderate:4d} fields - likely needed")
        print(f"  [6+ uses]  Heavy:    {all_heavy:4d} fields - definitely keep")
        print()

        print("-" * 70)
        print("DETAILED USAGE BY SERIALIZER")
        print("-" * 70)
        print()

        by_unused = sorted(serializers.values(), key=lambda x: len(x.unused_fields), reverse=True)

        for analysis in by_unused:
            usage = analysis.get_fields_by_usage()
            unused_count = len(usage["unused"])
            rare_count = len(usage["rare"])

            # Skip if not enough low-usage fields to report
            if unused_count + rare_count < min_unused:
                continue

            pct = unused_count / len(analysis.fields) * 100 if analysis.fields else 0
            print(f"### {analysis.name}")
            print(f"    Total: {len(analysis.fields)} | Unused: {unused_count} | Rare(1-2): {rare_count}")
            print()

            # Show unused fields
            if usage["unused"]:
                print("    [0 uses] UNUSED - safe to remove:")
                for field_name, count in sorted(usage["unused"])[:6]:
                    print(f"      - {field_name}")
                if len(usage["unused"]) > 6:
                    print(f"      ... and {len(usage['unused'])-6} more")
                print()

            # Show rarely used fields
            if usage["rare"] and verbose:
                print("    [1-2 uses] RARE - review these:")
                for field_name, count in sorted(usage["rare"], key=lambda x: x[1]):
                    files = analysis.usage_map.get(field_name, [])
                    files_str = ", ".join(files[:2])
                    if len(files) > 2:
                        files_str += f" +{len(files)-2} more"
                    print(f"      - {field_name} ({count}): {files_str}")
                print()

            # Show heavily used in verbose mode
            if verbose and usage["heavy"]:
                print("    [6+ uses] HEAVY - definitely keep:")
                for field_name, count in sorted(usage["heavy"], key=lambda x: -x[1])[:5]:
                    print(f"      - {field_name} ({count} files)")
                print()

            print()

        # ---- TOP REMOVAL CANDIDATES ----
        print("-" * 70)
        print("TOP REMOVAL CANDIDATES (ranked by: unused + expensive)")
        print("-" * 70)
        print()
        print("Score = usage_score * cost_multiplier")
        print("  usage_score: unused=100, rare(1-2)=50, moderate(3-5)=10, heavy=1")
        print("  cost_mult:   expensive=10, moderate=5, cheap=1")
        print()

        # Collect all fields across serializers with their removal priority
        all_candidates = []
        for analysis in serializers.values():
            for field_name, score, usage, cost in analysis.get_ranked_removal_candidates():
                if score >= 100:  # Only show high-priority candidates
                    all_candidates.append((analysis.name, field_name, score, usage, cost))

        # Sort by score
        all_candidates.sort(key=lambda x: -x[2])

        if all_candidates:
            print(f"{'Serializer':<35} {'Field':<25} {'Score':>6} {'Uses':>5} {'Cost':<10}")
            print("-" * 85)

            for serializer, field_name, score, usage, cost in all_candidates[:25]:
                cost_indicator = {"expensive": "[!!!]", "moderate": "[!!]", "cheap": ""}.get(cost, "")
                print(f"{serializer:<35} {field_name:<25} {score:>6} {usage:>5} {cost:<10} {cost_indicator}")

            if len(all_candidates) > 25:
                print(f"... and {len(all_candidates) - 25} more candidates")
        else:
            print("No high-priority removal candidates found.")

        print()

    # ---- RECOMMENDATIONS ----
    print("-" * 70)
    print("RECOMMENDATIONS")
    print("-" * 70)
    print()

    high_cost = [a for a in serializers.values() if a.expensive_fields >= 3]
    high_unused = [a for a in serializers.values() if len(a.unused_fields) >= 5]
    n_plus_1 = [a for a in serializers.values() if a.has_n_plus_1_risk]

    if high_cost:
        print("Candidates for drf-flex-fields ?expand= pattern:")
        for a in high_cost[:5]:
            print(f"  - {a.name} ({a.expensive_fields} expensive fields)")
        print()

    if high_unused:
        print("Candidates for DynamicFieldsMixin ?fields= param:")
        for a in high_unused[:5]:
            print(f"  - {a.name} ({len(a.unused_fields)} unused fields)")
        print()

    if n_plus_1:
        print("Need select_related/prefetch_related in ViewSet:")
        for a in n_plus_1[:5]:
            print(f"  - {a.name}")
        print()

    print("Quick wins:")
    print("  1. Add DynamicFieldsMixin to high-unused serializers")
    print("  2. Use ?fields= from frontend for list views")
    print("  3. Add select_related() to ViewSet.get_queryset()")
    print("  4. Consider drf-flex-fields for ?expand= pattern")
    print()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Analyze API field usage and cost')
    parser.add_argument('--serializer', '-s', help='Filter to specific serializer')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show all details')
    parser.add_argument('--min-unused', '-m', type=int, default=3, help='Min unused fields to report')
    parser.add_argument('--usage-only', action='store_true', help='Only show usage analysis')
    parser.add_argument('--cost-only', action='store_true', help='Only show cost analysis')
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    serializer_dir = project_root / 'PartsTracker' / 'Tracker' / 'serializers'
    frontend_dir = project_root / 'ambac-tracker-ui' / 'src'

    print(f"Scanning: {serializer_dir}")
    print(f"Frontend: {frontend_dir}")
    print()

    # Extract and analyze serializers
    serializers = extract_serializers(serializer_dir)
    print(f"Found {len(serializers)} serializers")

    # Filter if requested
    if args.serializer:
        serializers = {k: v for k, v in serializers.items() if args.serializer.lower() in k.lower()}
        print(f"Filtered to {len(serializers)} matching '{args.serializer}'")

    # Find frontend usage
    if not args.cost_only:
        find_field_usage_in_frontend(frontend_dir, serializers)

    print()

    # Report
    show_usage = not args.cost_only
    show_cost = not args.usage_only

    print_report(
        serializers,
        show_usage=show_usage,
        show_cost=show_cost,
        verbose=args.verbose,
        min_unused=args.min_unused
    )


if __name__ == '__main__':
    main()
