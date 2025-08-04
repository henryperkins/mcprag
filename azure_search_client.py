#!/usr/bin/env python3
"""
Azure Cognitive Search REST API client for deploying search components
"""

import json
import requests
from typing import Dict, Any
from enhanced_rag.core.config import get_config


class AzureSearchClient:
    """REST API client for Azure Cognitive Search"""
    
    def __init__(self):
        config = get_config()
        self.endpoint = config.azure.endpoint
        self.admin_key = config.azure.admin_key
        self.api_version = "2025-05-01-preview"
        
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.admin_key
        }
    
    def create_data_source(self, config_file: str = "datasource-config.json") -> bool:
        """Create data source from config file"""
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            url = f"{self.endpoint}/datasources?api-version={self.api_version}"
            response = requests.post(url, headers=self.headers, json=config)
            
            if response.status_code in [200, 201]:
                print(f"✅ Data source '{config['name']}' created successfully")
                return True
            else:
                print(f"❌ Failed to create data source: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating data source: {e}")
            return False
    
    def create_skillset(self, config_file: str = "skillset-config.json") -> bool:
        """Create skillset from config file"""
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            url = f"{self.endpoint}/skillsets?api-version={self.api_version}"
            response = requests.post(url, headers=self.headers, json=config)
            
            if response.status_code in [200, 201]:
                print(f"✅ Skillset '{config['name']}' created successfully")
                return True
            else:
                print(f"❌ Failed to create skillset: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating skillset: {e}")
            return False
    
    def create_indexer(self, config_file: str = "indexer-config.json") -> bool:
        """Create indexer from config file"""
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            url = f"{self.endpoint}/indexers?api-version={self.api_version}"
            response = requests.post(url, headers=self.headers, json=config)
            
            if response.status_code in [200, 201]:
                print(f"✅ Indexer '{config['name']}' created successfully")
                return True
            else:
                print(f"❌ Failed to create indexer: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating indexer: {e}")
            return False
    
    def get_indexer_status(self, indexer_name: str) -> Dict[str, Any]:
        """Get indexer execution status"""
        try:
            url = f"{self.endpoint}/indexers/{indexer_name}/status?api-version={self.api_version}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def run_indexer(self, indexer_name: str) -> bool:
        """Manually trigger indexer execution"""
        try:
            url = f"{self.endpoint}/indexers/{indexer_name}/run?api-version={self.api_version}"
            response = requests.post(url, headers=self.headers)
            
            if response.status_code == 202:
                print(f"✅ Indexer '{indexer_name}' execution started")
                return True
            else:
                print(f"❌ Failed to run indexer: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error running indexer: {e}")
            return False


def deploy_all_components():
    """Deploy all search components in correct order"""
    client = AzureSearchClient()
    
    print("🚀 Deploying Azure Cognitive Search components...")
    print("=" * 50)
    
    # Step 1: Create data source
    print("\n📁 Creating data source...")
    if not client.create_data_source():
        print("❌ Data source creation failed. Stopping deployment.")
        return False
    
    # Step 2: Create skillset
    print("\n🧠 Creating skillset...")
    if not client.create_skillset():
        print("❌ Skillset creation failed. Stopping deployment.")
        return False
    
    # Step 3: Create indexer
    print("\n⚙️  Creating indexer...")
    if not client.create_indexer():
        print("❌ Indexer creation failed. Stopping deployment.")
        return False
    
    print("\n🎉 All components deployed successfully!")
    
    # Step 4: Run indexer
    print("\n▶️  Starting indexer execution...")
    if client.run_indexer("codebase-indexer"):
        print("✅ Indexer started. Check status for progress.")
    
    return True


def check_indexer_status():
    """Check the status of the codebase indexer"""
    client = AzureSearchClient()
    
    print("🔍 Checking indexer status...")
    status = client.get_indexer_status("codebase-indexer")
    
    if "error" in status:
        print(f"❌ Error getting status: {status['error']}")
        return
    
    print(f"📊 Indexer Status: {status.get('status', 'Unknown')}")
    
    # Show execution history
    executions = status.get('executionHistory', [])
    if executions:
        latest = executions[0]
        print(f"   Last execution: {latest.get('status', 'Unknown')}")
        print(f"   Start time: {latest.get('startTime', 'N/A')}")
        print(f"   End time: {latest.get('endTime', 'N/A')}")
        
        if latest.get('itemsProcessed'):
            print(f"   Items processed: {latest['itemsProcessed']}")
        if latest.get('itemsFailed'):
            print(f"   Items failed: {latest['itemsFailed']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_indexer_status()
    else:
        deploy_all_components()
