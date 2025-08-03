#!/usr/bin/env python3
"""
Configuration validation script for Enhanced RAG implementation
Checks environment variables, configuration, and dependencies
"""

import os
import sys
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def check_mark(status: bool) -> str:
    return f"{Colors.GREEN}✓{Colors.ENDC}" if status else f"{Colors.RED}✗{Colors.ENDC}"

def print_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== {title} ==={Colors.ENDC}")

def print_status(item: str, status: bool, message: str = ""):
    mark = check_mark(status)
    color = Colors.GREEN if status else Colors.RED
    print(f"{mark} {item}: {color}{message or ('OK' if status else 'MISSING')}{Colors.ENDC}")

def check_env_variables() -> Tuple[Dict[str, bool], List[str]]:
    """Check required and optional environment variables"""
    print_section("Environment Variables")
    
    required_vars = {
        "ACS_ENDPOINT": "Azure Cognitive Search endpoint",
        "ACS_ADMIN_KEY": "Azure Cognitive Search admin key"
    }
    
    optional_vars = {
        "AZURE_OPENAI_ENDPOINT": "Azure OpenAI endpoint (for embeddings)",
        "AZURE_OPENAI_KEY": "Azure OpenAI API key",
        "AZURE_OPENAI_API_KEY": "Alternative Azure OpenAI API key",
        "DEBUG": "Debug mode flag",
        "LOG_LEVEL": "Logging level"
    }
    
    results = {}
    missing_required = []
    
    # Check required variables
    print("\nRequired:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        exists = bool(value)
        results[var] = exists
        if not exists:
            missing_required.append(var)
        
        # Mask sensitive values
        if exists and "KEY" in var:
            display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        elif exists:
            display_value = value
        else:
            display_value = "NOT SET"
            
        print_status(f"{var} ({desc})", exists, display_value)
    
    # Check optional variables
    print("\nOptional:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        exists = bool(value)
        results[var] = exists
        
        # Mask sensitive values
        if exists and "KEY" in var:
            display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
        elif exists:
            display_value = value
        else:
            display_value = "NOT SET"
            
        print_status(f"{var} ({desc})", exists or True, display_value)
    
    return results, missing_required

def check_python_dependencies() -> Dict[str, bool]:
    """Check if required Python packages are installed"""
    print_section("Python Dependencies")
    
    dependencies = {
        "azure.search.documents": "Azure Cognitive Search SDK",
        "pydantic": "Data validation",
        "aiohttp": "Async HTTP client",
        "dotenv": "Environment variable loading"
    }
    
    optional_deps = {
        "openai": "OpenAI SDK (for embeddings)",
        "fastapi": "API server",
        "uvicorn": "ASGI server",
        "mcp.server": "MCP SDK"
    }
    
    results = {}
    
    print("\nRequired:")
    for module, desc in dependencies.items():
        try:
            __import__(module.split('.')[0])
            installed = True
        except ImportError:
            installed = False
        results[module] = installed
        print_status(f"{module} ({desc})", installed)
    
    print("\nOptional:")
    for module, desc in optional_deps.items():
        try:
            __import__(module.split('.')[0])
            installed = True
        except ImportError:
            installed = False
        results[module] = installed
        print_status(f"{module} ({desc})", installed or True, "OK" if installed else "NOT INSTALLED")
    
    return results

def check_configuration_files() -> Dict[str, bool]:
    """Check if configuration files exist"""
    print_section("Configuration Files")
    
    files = {
        ".env": "Environment variables file",
        "enhanced_rag/core/config.py": "Core configuration module",
        "enhanced_rag/CANONICAL_SCHEMA.md": "Schema documentation",
        "CLAUDE.md": "Claude Code instructions"
    }
    
    results = {}
    for file, desc in files.items():
        exists = os.path.exists(file)
        results[file] = exists
        print_status(f"{file} ({desc})", exists)
    
    return results

def check_azure_connectivity():
    """Test Azure Search connectivity"""
    print_section("Azure Connectivity")
    
    endpoint = os.getenv("ACS_ENDPOINT")
    api_key = os.getenv("ACS_ADMIN_KEY")
    
    if not endpoint or not api_key:
        print_status("Azure Search connection", False, "Missing credentials")
        return False
    
    try:
        from azure.search.documents import SearchClient
        from azure.core.credentials import AzureKeyCredential
        
        # Try to create a client
        client = SearchClient(
            endpoint=endpoint,
            index_name="test-connection",
            credential=AzureKeyCredential(api_key)
        )
        print_status("Azure Search connection", True, f"Connected to {endpoint}")
        return True
    except Exception as e:
        print_status("Azure Search connection", False, str(e)[:100])
        return False

def generate_env_template():
    """Generate a .env.template file"""
    template = """# Azure Cognitive Search Configuration
ACS_ENDPOINT=https://your-search-service.search.windows.net
ACS_ADMIN_KEY=your-admin-key-here

# Azure OpenAI Configuration (Optional, for embeddings)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_KEY=your-openai-key-here

# Optional Settings
DEBUG=false
LOG_LEVEL=INFO
"""
    
    if not os.path.exists(".env.template"):
        with open(".env.template", "w") as f:
            f.write(template)
        print(f"\n{Colors.GREEN}Created .env.template - copy to .env and fill in your values{Colors.ENDC}")

def main():
    """Run all validation checks"""
    print(f"{Colors.BOLD}Enhanced RAG Configuration Validator{Colors.ENDC}")
    print("=" * 50)
    
    # Check environment variables
    env_results, missing_required = check_env_variables()
    
    # Check Python dependencies
    dep_results = check_python_dependencies()
    
    # Check configuration files
    file_results = check_configuration_files()
    
    # Test Azure connectivity
    if not missing_required:
        azure_connected = check_azure_connectivity()
    else:
        print_section("Azure Connectivity")
        print_status("Azure Search connection", False, "Skipped - missing required environment variables")
        azure_connected = False
    
    # Summary
    print_section("Summary")
    
    all_good = True
    
    if missing_required:
        print(f"\n{Colors.RED}Missing required environment variables:{Colors.ENDC}")
        for var in missing_required:
            print(f"  - {var}")
        all_good = False
    
    missing_deps = [dep for dep, installed in dep_results.items() if not installed and dep in ["azure.search.documents", "pydantic", "aiohttp", "dotenv"]]
    if missing_deps:
        print(f"\n{Colors.RED}Missing required Python packages:{Colors.ENDC}")
        for dep in missing_deps:
            print(f"  - {dep}")
        print(f"\n{Colors.YELLOW}Install with: pip install -r requirements.txt{Colors.ENDC}")
        all_good = False
    
    if not file_results.get(".env", False):
        generate_env_template()
    
    if all_good and azure_connected:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All checks passed! Your environment is ready.{Colors.ENDC}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some issues need to be resolved. See above for details.{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()