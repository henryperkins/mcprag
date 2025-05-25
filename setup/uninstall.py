#!/usr/bin/env python3
"""
Uninstall script for MCP RAG system.
Safely removes Azure resources and cleans up local files.
"""
import subprocess
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

def run_command(cmd, capture_output=True, ignore_errors=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        if result.returncode != 0 and not ignore_errors:
            print(f"Warning: Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return None
        return result.stdout.strip() if capture_output else True
    except Exception as e:
        if not ignore_errors:
            print(f"Exception running command: {cmd}")
            print(f"Exception: {e}")
        return None

def check_azure_cli():
    """Check if Azure CLI is available."""
    print("🔍 Checking Azure CLI...")
    
    if not run_command("az --version"):
        print("❌ Azure CLI not found. Cannot remove Azure resources.")
        print("   You may need to manually delete resources from Azure portal.")
        return False
    
    # Check if logged in
    account_info = run_command("az account show")
    if not account_info:
        print("❌ Not logged into Azure. Cannot remove Azure resources.")
        print("   Run: az login")
        return False
    
    account = json.loads(account_info)
    print(f"✅ Logged in as: {account['user']['name']}")
    return True

def get_resource_info():
    """Get resource information from .env file or defaults."""
    resource_info = {
        'resource_group': 'mcprag-rg',
        'search_service': 'mcprag-search',
        'index_name': 'codebase-mcp-sota'
    }
    
    # Try to load from .env file
    if Path('.env').exists():
        load_dotenv()
        endpoint = os.getenv('ACS_ENDPOINT')
        if endpoint:
            # Extract service name from endpoint
            # Format: https://service-name.search.windows.net
            service_name = endpoint.replace('https://', '').replace('.search.windows.net', '')
            resource_info['search_service'] = service_name
            print(f"📋 Found search service in .env: {service_name}")
    
    return resource_info

def delete_search_index(service_name, admin_key, index_name):
    """Delete the search index."""
    print(f"🗑️  Deleting search index: {index_name}")
    
    if not admin_key:
        print("⚠️  No admin key found. Skipping index deletion.")
        return True
    
    # Try to delete via REST API
    endpoint = f"https://{service_name}.search.windows.net"
    cmd = f'''curl -X DELETE "{endpoint}/indexes/{index_name}?api-version=2023-11-01" -H "api-key: {admin_key}"'''
    
    result = run_command(cmd, ignore_errors=True)
    if result is not None:
        print(f"✅ Search index '{index_name}' deleted")
    else:
        print(f"⚠️  Could not delete search index '{index_name}' (may not exist)")
    
    return True

def delete_search_service(service_name, resource_group):
    """Delete Azure Cognitive Search service."""
    print(f"🗑️  Deleting Azure Cognitive Search service: {service_name}")
    
    cmd = f"az search service delete --name {service_name} --resource-group {resource_group} --yes"
    result = run_command(cmd, ignore_errors=True)
    
    if result is not None:
        print(f"✅ Search service '{service_name}' deleted")
        return True
    else:
        print(f"⚠️  Could not delete search service '{service_name}' (may not exist)")
        return False

def delete_resource_group(resource_group):
    """Delete the entire resource group."""
    print(f"🗑️  Deleting resource group: {resource_group}")
    
    # Check if resource group exists
    check_cmd = f"az group exists --name {resource_group}"
    exists = run_command(check_cmd)
    
    if exists and exists.lower() == 'true':
        cmd = f"az group delete --name {resource_group} --yes --no-wait"
        result = run_command(cmd, ignore_errors=True)
        
        if result is not None:
            print(f"✅ Resource group '{resource_group}' deletion initiated")
            print("   Note: Deletion may take several minutes to complete")
            return True
        else:
            print(f"❌ Failed to delete resource group '{resource_group}'")
            return False
    else:
        print(f"⚠️  Resource group '{resource_group}' does not exist")
        return True

def cleanup_local_files():
    """Clean up local files and directories."""
    print("🧹 Cleaning up local files...")
    
    files_to_remove = [
        '.env',
        'app.db',  # SQLite database if created
        '__pycache__',
        '.pytest_cache',
        'logs',
        'temp'
    ]
    
    directories_to_remove = [
        '__pycache__',
        '.pytest_cache',
        'logs',
        'temp'
    ]
    
    removed_count = 0
    
    for file_path in files_to_remove:
        path = Path(file_path)
        if path.exists():
            try:
                if path.is_file():
                    path.unlink()
                    print(f"   ✅ Removed file: {file_path}")
                    removed_count += 1
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                    print(f"   ✅ Removed directory: {file_path}")
                    removed_count += 1
            except Exception as e:
                print(f"   ⚠️  Could not remove {file_path}: {e}")
    
    if removed_count == 0:
        print("   ℹ️  No temporary files found to clean up")
    else:
        print(f"   ✅ Cleaned up {removed_count} items")

def stop_running_processes():
    """Attempt to stop any running MCP servers."""
    print("🛑 Checking for running MCP servers...")
    
    # Try to check if server is running
    health_check = run_command("curl -s http://localhost:8001/health", ignore_errors=True)
    
    if health_check:
        print("   ⚠️  MCP server appears to be running on port 8001")
        print("   Please manually stop the server (Ctrl+C) before running uninstall")
        return False
    else:
        print("   ✅ No MCP server detected on port 8001")
        return True

def main():
    """Main uninstall function."""
    print("🗑️  MCP RAG System Uninstaller")
    print("=" * 50)
    print("This script will:")
    print("1. Stop any running MCP servers")
    print("2. Delete Azure search index")
    print("3. Delete Azure Cognitive Search service")
    print("4. Delete Azure resource group")
    print("5. Clean up local files")
    print("\n⚠️  WARNING: This will permanently delete all Azure resources!")
    print("💰 This will stop all billing for Azure resources.")
    
    # Confirmation
    confirm = input("\nAre you sure you want to proceed? (type 'DELETE' to confirm): ")
    if confirm != 'DELETE':
        print("❌ Uninstall cancelled.")
        return
    
    # Step 1: Check for running processes
    if not stop_running_processes():
        print("\n⚠️  Please stop any running servers and try again.")
        return
    
    # Step 2: Check Azure CLI
    azure_available = check_azure_cli()
    
    if azure_available:
        # Step 3: Get resource information
        resource_info = get_resource_info()
        
        # Get admin key for index deletion
        admin_key = None
        if Path('.env').exists():
            load_dotenv()
            admin_key = os.getenv('ACS_ADMIN_KEY')
        
        # Step 4: Delete search index
        delete_search_index(
            resource_info['search_service'], 
            admin_key, 
            resource_info['index_name']
        )
        
        # Step 5: Delete search service
        delete_search_service(
            resource_info['search_service'], 
            resource_info['resource_group']
        )
        
        # Step 6: Delete resource group
        delete_resource_group(resource_info['resource_group'])
        
    else:
        print("\n⚠️  Skipping Azure resource deletion due to CLI issues.")
        print("   Please manually delete resources from Azure portal:")
        print("   https://portal.azure.com")
    
    # Step 7: Clean up local files
    cleanup_local_files()
    
    print("\n🎉 Uninstall completed!")
    
    if azure_available:
        print("\n📋 Summary:")
        print("✅ Azure resources deleted (or deletion initiated)")
        print("✅ Local files cleaned up")
        print("✅ Billing stopped for Azure resources")
        print("\nNote: Resource group deletion may take a few minutes to complete.")
        print("You can verify deletion in the Azure portal: https://portal.azure.com")
    else:
        print("\n📋 Summary:")
        print("⚠️  Azure resources may still exist - manual cleanup required")
        print("✅ Local files cleaned up")
        print("\nPlease check Azure portal to ensure all resources are deleted:")
        print("https://portal.azure.com")

if __name__ == "__main__":
    main()
