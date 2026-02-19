#!/bin/bash
# Query Key Audit Script
# Checks consistency between hooks and prefetch functions

echo "=========================================="
echo "QUERY KEY AUDIT"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Query Keys in Hooks (src/hooks/) ===${NC}"
echo ""
grep -rn "queryKey:" src/hooks/*.ts 2>/dev/null | while read line; do
    file=$(echo "$line" | cut -d: -f1 | xargs basename)
    linenum=$(echo "$line" | cut -d: -f2)
    key=$(echo "$line" | sed 's/.*queryKey:\s*//' | tr -d ',' )
    echo -e "${GREEN}$file:$linenum${NC}"
    echo "  $key"
    echo ""
done

echo ""
echo -e "${BLUE}=== Query Keys in Prefetch Functions (src/pages/editors/) ===${NC}"
echo ""
grep -rn "queryKey:" src/pages/editors/*EditorPage.tsx 2>/dev/null | while read line; do
    file=$(echo "$line" | cut -d: -f1 | xargs basename)
    linenum=$(echo "$line" | cut -d: -f2)
    key=$(echo "$line" | sed 's/.*queryKey:\s*//' | tr -d ',')
    echo -e "${GREEN}$file:$linenum${NC}"
    echo "  $key"
    echo ""
done

echo ""
echo -e "${BLUE}=== Query Keys in Quality Pages ===${NC}"
echo ""
grep -rn "queryKey:" src/pages/quality/*.tsx 2>/dev/null | while read line; do
    file=$(echo "$line" | cut -d: -f1 | xargs basename)
    linenum=$(echo "$line" | cut -d: -f2)
    key=$(echo "$line" | sed 's/.*queryKey:\s*//' | tr -d ',')
    echo -e "${GREEN}$file:$linenum${NC}"
    echo "  $key"
    echo ""
done

echo ""
echo "=========================================="
echo -e "${YELLOW}SUMMARY: Unique Query Key Prefixes${NC}"
echo "=========================================="
echo ""

echo "Hook query keys (first element):"
grep -roh 'queryKey: \["\([^"]*\)"' src/hooks/*.ts 2>/dev/null | \
    sed 's/queryKey: \["//' | sed 's/"//' | sort | uniq -c | sort -rn

echo ""
echo "Prefetch query keys (first element):"
grep -roh 'queryKey: \["\([^"]*\)"' src/pages/editors/*EditorPage.tsx src/pages/quality/*.tsx 2>/dev/null | \
    sed 's/queryKey: \["//' | sed 's/"//' | sort | uniq -c | sort -rn

echo ""
echo "=========================================="
echo -e "${YELLOW}POTENTIAL MISMATCHES${NC}"
echo "=========================================="
echo ""
echo "Checking if prefetch keys match hook keys..."
echo ""

# Extract hook keys
hook_keys=$(grep -roh 'queryKey: \["\([^"]*\)"' src/hooks/*.ts 2>/dev/null | \
    sed 's/queryKey: \["//' | sed 's/"//' | sort | uniq)

# Extract prefetch keys
prefetch_keys=$(grep -roh 'queryKey: \["\([^"]*\)"' src/pages/editors/*EditorPage.tsx src/pages/quality/*.tsx 2>/dev/null | \
    sed 's/queryKey: \["//' | sed 's/"//' | sort | uniq)

# Find prefetch keys not in hooks
echo -e "${RED}Prefetch keys without matching hooks:${NC}"
for key in $prefetch_keys; do
    if ! echo "$hook_keys" | grep -q "^${key}$"; then
        echo "  - $key"
    fi
done

echo ""
echo -e "${RED}Hook keys without prefetch:${NC}"
for key in $hook_keys; do
    if ! echo "$prefetch_keys" | grep -q "^${key}$"; then
        echo "  - $key (may not need prefetch)"
    fi
done

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="
