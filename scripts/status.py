#!/usr/bin/env python3
"""
Status checker for MCP RAG system.
Shows current state of Azure resources, local files, and running services.
"""
import subprocess
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv


def run_command(cmd, capture_output=True, ignore_errors=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, text=True
        )
        if result.returncode != 0 and not ignore_errors:
            return None
        return result.stdout.strip() if capture_output else True
    except Exception:
        return None


def check_azure_status():
    """Check Azure CLI and account status."""
    print("🔍 Azure Status")
    print("-" * 20)

    # Check Azure CLI
    if not run_command("az --version"):
        print("❌ Azure CLI not installed")
        return False

    print("✅ Azure CLI installed")

    # Check login status
    account_info = run_command("az account show")
    if not account_info:
        print("❌ Not logged into Azure")
        return False

    account = json.loads(account_info)
    print(f"✅ Logged in as: {account['user']['name']}")
    print(f"✅ Subscription: {account['name']}")
    return True


def check_local_files():
    """Check status of local files."""
    print("\n📁 Local Files Status")
    print("-" * 25)

    # Core files
    core_files = {
        "index_schema.json": "Index schema",
        "create_index.py": "Index creator",
        "smart_indexer.py": "Smart indexer",
        "mcp_server_sota.py": "SOTA MCP server",
        "setup_azure.py": "Azure setup",
        "uninstall.py": "Uninstaller",
        "cleanup_local.py": "Local cleanup",
        "test_setup.py": "Test suite",
        "deploy.py": "Deployment script",
        "requirements.txt": "Dependencies",
    }

    # Configuration files
    config_files = {".env": "Environment config", ".env.backup": "Config backup"}

    # Check core files
    print("Core Files:")
    for file, description in core_files.items():
        if Path(file).exists():
            print(f"  ✅ {file} - {description}")
        else:
            print(f"  ❌ {file} - {description} (missing)")

    # Check config files
    print("\nConfiguration:")
    for file, description in config_files.items():
        if Path(file).exists():
            print(f"  ✅ {file} - {description}")
        else:
            print(f"  ⚪ {file} - {description} (not found)")

    # Check example repo
    if Path("example-repo").exists():
        example_files = list(Path("example-repo").glob("*.py"))
        print(f"  ✅ example-repo - {len(example_files)} Python files")
    else:
        print("  ⚪ example-repo - (not found)")


def check_azure_resources():
    """Check Azure resources status."""
    print("\n☁️  Azure Resources Status")
    print("-" * 30)

    # Load config
    if not Path(".env").exists():
        print("❌ No .env file found - cannot check Azure resources")
        return False

    load_dotenv()
    endpoint = os.getenv("ACS_ENDPOINT")
    admin_key = os.getenv("ACS_ADMIN_KEY")

    if not endpoint or not admin_key:
        print("❌ Missing Azure configuration in .env file")
        return False

    # Extract service name
    service_name = endpoint.replace("https://", "").replace(".search.windows.net", "")

    # Check search service
    print(f"Search Service: {service_name}")
    service_check = run_command(
        f"az search service show --name {service_name} --resource-group mcprag-rg"
    )
    if service_check:
        service_info = json.loads(service_check)
        print(f"  ✅ Status: {service_info.get('status', 'Unknown')}")
        print(f"  ✅ SKU: {service_info.get('sku', {}).get('name', 'Unknown')}")
        print(f"  ✅ Location: {service_info.get('location', 'Unknown')}")
    else:
        print("  ❌ Search service not found or inaccessible")
        return False

    # Check search index
    print(f"\nSearch Index: codebase-mcp-sota")
    try:
        response = requests.get(
            f"{endpoint}/indexes/codebase-mcp-sota?api-version=2023-11-01",
            headers={"api-key": admin_key},
            timeout=10,
        )
        if response.status_code == 200:
            index_info = response.json()
            field_count = len(index_info.get("fields", []))
            print(f"  ✅ Index exists with {field_count} fields")

            # Check document count
            stats_response = requests.get(
                f"{endpoint}/indexes/codebase-mcp-sota/stats?api-version=2023-11-01",
                headers={"api-key": admin_key},
                timeout=10,
            )
            if stats_response.status_code == 200:
                stats = stats_response.json()
                doc_count = stats.get("documentCount", 0)
                storage_size = stats.get("storageSize", 0)
                print(f"  ✅ Documents: {doc_count}")
                print(f"  ✅ Storage: {storage_size} bytes")
            else:
                print("  ⚪ Could not retrieve index statistics")
        else:
            print("  ❌ Index not found or inaccessible")
    except Exception as e:
        print(f"  ❌ Error checking index: {e}")

    return True


def check_mcp_server():
    """Check MCP server status."""
    print("\n🚀 MCP Server Status")
    print("-" * 22)

    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ MCP server is running")
            print(f"  Status: {health_data.get('status', 'Unknown')}")
            print(f"  Version: {health_data.get('version', 'Unknown')}")

            # Test search endpoint
            try:
                search_response = requests.post(
                    "http://localhost:8001/mcp-query",
                    json={"input": "test query"},
                    timeout=10,
                )
                if search_response.status_code == 200:
                    print("  ✅ Search endpoint responding")
                else:
                    print(f"  ⚠️  Search endpoint error: {search_response.status_code}")
            except Exception:
                print("  ⚠️  Search endpoint not responding")

        else:
            print(f"❌ MCP server error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ MCP server not running")
        print("  Start with: python mcp_server_sota.py")
    except Exception as e:
        print(f"❌ Error checking MCP server: {e}")


def estimate_costs():
    """Estimate current Azure costs."""
    print("\n💰 Cost Estimation")
    print("-" * 18)

    if Path(".env").exists():
        load_dotenv()
        if os.getenv("ACS_ENDPOINT"):
            print("Azure Cognitive Search (Basic): ~$75/month")
            print("API calls (estimated): ~$175/month")
            print("Total estimated: ~$250/month")
            print("\n💡 To stop billing: python uninstall.py")
        else:
            print("⚪ No Azure resources configured")
    else:
        print("⚪ No configuration found")


def main():
    """Main status function."""
    print("📊 MCP RAG System Status")
    print("=" * 30)

    # Check all components
    azure_cli_ok = check_azure_status()
    check_local_files()

    if azure_cli_ok:
        check_azure_resources()
    else:
        print("\n☁️  Azure Resources Status")
        print("-" * 30)
        print("❌ Cannot check Azure resources (Azure CLI issues)")

    check_mcp_server()
    estimate_costs()

    print("\n📋 Quick Actions:")
    print("• Deploy system: python deploy.py")
    print("• Test system: python test_setup.py")
    print("• Start server: python mcp_server_sota.py")
    print("• Clean local: python cleanup_local.py")
    print("• Full removal: python uninstall.py")
    print("• Azure portal: https://portal.azure.com")


if __name__ == "__main__":
    main()
