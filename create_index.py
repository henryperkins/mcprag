# create_index.py
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("ACS_ENDPOINT")
admin_key = os.getenv("ACS_ADMIN_KEY")
api_version = "2025-05-01-preview"

url = f"{endpoint}/indexes/codebase-mcp-sota?api-version={api_version}"
headers = {"Content-Type": "application/json", "api-key": admin_key}

with open("index_schema.json") as f:
    index_def = json.load(f)

response = requests.put(url, headers=headers, json=index_def)
print(
    "✅ Index created"
    if response.status_code in [200, 201]
    else f"❌ Error: {response.text}"
)
