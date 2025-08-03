#!/bin/bash
# Pre-commit hook to check for prohibited index creator files

echo "🔍 Checking for prohibited index creator files..."

prohibited_files=(
  "azure_search_enhanced.py"
  "index/create_index_3072.py"
  "scripts/create_index_with_skillset.py"
  "scripts/create_index_mcp_aligned.py"
  "scripts/create_index_from_json.py"
  "scripts/create_index_rest.py"
  "scripts/recreate_index_for_mcp.py"
)

found_prohibited=0
for file in "${prohibited_files[@]}"; do
  if [ -f "$file" ]; then
    echo "❌ Prohibited file found: $file"
    echo "   Please use index/create_enhanced_index.py instead"
    found_prohibited=1
  fi
done

if [ $found_prohibited -eq 1 ]; then
  echo ""
  echo "⚠️  Commit blocked: Prohibited index creator files found"
  echo "   Use the canonical path: python index/create_enhanced_index.py"
  exit 1
fi

echo "✅ No prohibited index creator files found"

# Optional: Run schema validation if credentials are available
if [ ! -z "$ACS_ENDPOINT" ] && [ ! -z "$ACS_ADMIN_KEY" ]; then
  echo "🔍 Validating index schema..."
  python scripts/validate_index_canonical.py
  if [ $? -ne 0 ]; then
    echo "⚠️  Index schema validation failed"
    echo "   Run: python index/create_enhanced_index.py"
    exit 1
  fi
fi

exit 0