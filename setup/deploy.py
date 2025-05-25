#!/usr/bin/env python3
"""
Complete deployment script for MCP RAG system.
Handles Azure setup, index creation, and initial data indexing.
"""
import subprocess
import sys
import time
import os
from pathlib import Path


def run_script(script_name, description):
    """Run a Python script and handle errors."""
    print(f"\n🚀 {description}")
    print("-" * 50)

    try:
        result = subprocess.run(
            [sys.executable, script_name], capture_output=False, text=True
        )
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            return False
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False


def check_prerequisites():
    """Check if all required files exist."""
    print("🔍 Checking prerequisites...")

    required_files = [
        "setup_azure.py",
        "create_index.py",
        "smart_indexer.py",
        "mcp_server_sota.py",
        "test_setup.py",
        "uninstall.py",
        "cleanup_local.py",
        "requirements.txt",
        "index_schema.json",
    ]

    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False

    print("✅ All required files present")
    return True


def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing Python dependencies...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=False,
            text=True,
        )
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False


def main():
    """Main deployment function."""
    print("🚀 MCP RAG System Deployment")
    print("=" * 50)
    print("This script will:")
    print("1. Check prerequisites")
    print("2. Install Python dependencies")
    print("3. Set up Azure resources")
    print("4. Create search index")
    print("5. Index example code")
    print("6. Run tests")
    print("7. Start MCP server")

    input("\nPress Enter to continue or Ctrl+C to cancel...")

    # Step 1: Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please ensure all files are present.")
        sys.exit(1)

    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n❌ Dependency installation failed.")
        sys.exit(1)

    # Step 3: Azure setup
    if not run_script("setup_azure.py", "Setting up Azure resources"):
        print("\n❌ Azure setup failed. Please check your Azure CLI configuration.")
        sys.exit(1)

    # Wait a moment for Azure resources to be ready
    print("\n⏳ Waiting for Azure resources to be ready...")
    time.sleep(10)

    # Step 4: Create index
    if not run_script("create_index.py", "Creating search index"):
        print("\n❌ Index creation failed. Please check your Azure configuration.")
        sys.exit(1)

    # Step 5: Index data
    if not run_script("smart_indexer.py", "Indexing example code with AST analysis"):
        print("\n❌ Data indexing failed.")
        sys.exit(1)

    # Step 6: Run tests
    print("\n🧪 Running system tests...")
    if not run_script("test_setup.py", "Running tests"):
        print("\n⚠️  Some tests failed, but continuing...")

    # Step 7: Final instructions
    print("\n🎉 Deployment completed!")
    print("\n📋 Next steps:")
    print("1. Start the SOTA MCP server:")
    print("   python mcp_server_sota.py")
    print("\n2. Test the API:")
    print("   curl http://localhost:8001/health")
    print("\n3. Register with Claude Code:")
    print("   claude-code mcp add --name azure-code-search \\")
    print("     --type http --url http://localhost:8001/mcp-query --method POST")
    print("\n4. Add your own repositories to smart_indexer.py and re-run it")

    print(f"\n💰 Estimated monthly cost: ~$250")
    print("🔗 Azure portal: https://portal.azure.com")

    # Ask if user wants to start the server
    start_server = input("\nStart MCP server now? (y/N): ").lower().strip()
    if start_server == "y":
        print("\n🚀 Starting MCP server...")
        print("Press Ctrl+C to stop the server")
        try:
            subprocess.run([sys.executable, "mcp_server_sota.py"])
        except KeyboardInterrupt:
            print("\n👋 Server stopped")


if __name__ == "__main__":
    main()
