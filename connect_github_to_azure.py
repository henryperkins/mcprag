#!/usr/bin/env python3
"""
Script to connect your GitHub repository to Azure Cognitive Search.
This script helps you index your current repository.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_prerequisites():
    """Check if all prerequisites are met."""
    print("🔍 Checking prerequisites...")
    
    issues = []
    
    # Check .env file
    if not Path(".env").exists():
        issues.append("❌ .env file not found. Create one with ACS_ENDPOINT and ACS_ADMIN_KEY")
    else:
        load_dotenv()
        if not os.getenv("ACS_ENDPOINT"):
            issues.append("❌ ACS_ENDPOINT not set in .env file")
        if not os.getenv("ACS_ADMIN_KEY"):
            issues.append("❌ ACS_ADMIN_KEY not set in .env file")
    
    # Check Node.js dependencies
    if not Path("node_modules").exists():
        issues.append("❌ Node.js dependencies not installed. Run: npm install")
    
    # Check Python dependencies
    try:
        import azure.search.documents
        print("✅ Azure Search Documents library available")
    except ImportError:
        issues.append("❌ Azure Search Documents not installed. Run: pip install -r requirements.txt")
    
    # Check parse script
    if not Path("parse_js.mjs").exists():
        issues.append("❌ parse_js.mjs not found")
    elif not os.access("parse_js.mjs", os.X_OK):
        issues.append("❌ parse_js.mjs not executable. Run: chmod +x parse_js.mjs")
    
    if issues:
        print("\n🚨 Issues found:")
        for issue in issues:
            print(f"  {issue}")
        return False
    
    print("✅ All prerequisites met!")
    return True

def show_repository_stats():
    """Show statistics about the current repository."""
    print("\n📊 Repository Analysis:")
    
    python_files = list(Path(".").rglob("*.py"))
    js_files = list(Path(".").rglob("*.js"))
    ts_files = list(Path(".").rglob("*.ts"))
    
    print(f"  📄 Python files: {len(python_files)}")
    print(f"  📄 JavaScript files: {len(js_files)}")
    print(f"  📄 TypeScript files: {len(ts_files)}")
    print(f"  📄 Total indexable files: {len(python_files) + len(js_files) + len(ts_files)}")
    
    if python_files:
        print(f"  🐍 Sample Python files: {', '.join(str(f) for f in python_files[:3])}")
    if js_files:
        print(f"  🟨 Sample JavaScript files: {', '.join(str(f) for f in js_files[:3])}")
    if ts_files:
        print(f"  🔷 Sample TypeScript files: {', '.join(str(f) for f in ts_files[:3])}")

def main():
    print("🚀 GitHub Repository → Azure Cognitive Search Connector")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Please fix the issues above before proceeding.")
        sys.exit(1)
    
    # Show repository stats
    show_repository_stats()
    
    # Get repository name
    repo_name = input(f"\n📝 Enter repository name (default: 'mcprag'): ").strip()
    if not repo_name:
        repo_name = "mcprag"
    
    print(f"\n🔄 Ready to index repository '{repo_name}'")
    print("This will:")
    print("  1. Parse all Python, JavaScript, and TypeScript files")
    print("  2. Extract semantic information (functions, imports, calls)")
    print("  3. Upload documents to Azure Cognitive Search")
    print("  4. Use merge-or-upload for efficient indexing")
    
    confirm = input("\n❓ Proceed with indexing? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Indexing cancelled.")
        sys.exit(0)
    
    # Run the indexer
    print(f"\n🚀 Starting indexing process...")
    
    try:
        from smart_indexer import CodeChunker
        chunker = CodeChunker()
        chunker.index_repository("./", repo_name)
        
        print(f"\n✅ Successfully indexed repository '{repo_name}'!")
        print("\n📋 Next steps:")
        print("  1. Test your MCP server: python mcp_server_sota.py")
        print("  2. Set up GitHub Actions for automatic re-indexing")
        print("  3. Configure your Claude Desktop to use the MCP server")
        
    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        print("\n🔧 Troubleshooting:")
        print("  1. Check your Azure credentials in .env file")
        print("  2. Verify your Azure Search service is running")
        print("  3. Ensure the search index exists (run create_index.py)")
        sys.exit(1)

if __name__ == "__main__":
    main()
