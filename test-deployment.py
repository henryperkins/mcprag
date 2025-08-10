#!/usr/bin/env python3
"""
Test script to verify your FastAPI deployment is working correctly
Checks all critical endpoints for GPT Actions integration
"""

import sys
import json
import time
import requests
from typing import Dict, Any

def test_endpoint(url: str, endpoint: str, method: str = "GET", 
                  json_data: Dict[str, Any] = None, expected_status: int = 200) -> bool:
    """Test a single endpoint"""
    full_url = f"{url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    try:
        print(f"Testing {method} {endpoint}...", end=" ")
        
        if method == "GET":
            response = requests.get(full_url, timeout=10)
        elif method == "POST":
            response = requests.post(full_url, json=json_data, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                print(f"   Response: {json.dumps(response.json(), indent=2)[:200]}...")
            return True
        else:
            print(f"❌ Status: {response.status_code} (expected {expected_status})")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout after 10 seconds")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Run all deployment tests"""
    
    if len(sys.argv) < 2:
        print("Usage: python test-deployment.py <app-url>")
        print("Example: python test-deployment.py https://starguide-api.azurecontainerapps.io")
        sys.exit(1)
    
    base_url = sys.argv[1]
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    
    print(f"\n🔍 Testing FastAPI deployment at: {base_url}")
    print("=" * 60)
    
    # Essential endpoints for GPT Actions
    tests = [
        # Health check
        ("health", "GET", None, 200),
        
        # OpenAPI spec (critical for GPT Actions)
        ("openapi.json", "GET", None, 200),
        
        # Interactive docs
        ("docs", "GET", None, 200),
        
        # Root endpoint
        ("", "GET", None, 200),
    ]
    
    # Add your custom endpoints here
    # Example for StarGuide API:
    # tests.append(("planets/current", "GET", None, 200))
    # tests.append(("transits", "POST", {"lat": 40.7128, "lon": -74.0060}, 200))
    
    results = []
    for test in tests:
        endpoint, method, data, expected = test
        success = test_endpoint(base_url, endpoint, method, data, expected)
        results.append((endpoint, success))
        time.sleep(0.5)  # Be nice to the server
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for endpoint, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {endpoint}")
    
    print(f"\nPassed: {passed}/{total} tests")
    
    if passed == total:
        print("\n🎉 All tests passed! Your API is ready for GPT Actions.")
        print(f"\n📝 Add this to your GPT's OpenAPI servers:")
        print(f'  servers:\n    - url: {base_url}\n      description: Production API')
    else:
        print("\n⚠️  Some tests failed. Please check your deployment.")
        sys.exit(1)

if __name__ == "__main__":
    main()