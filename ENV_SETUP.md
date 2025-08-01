# Environment Setup for Azure Code Search MCP

## Option 1: Create a .env file (Recommended)

1. Create a `.env` file in the mcprag directory:
```bash
cd /home/azureuser/mcprag
nano .env
```

2. Add your Azure Cognitive Search credentials:
```
ACS_ENDPOINT=https://your-search-service.search.windows.net
ACS_ADMIN_KEY=your-admin-key-here
```

3. Save and exit (Ctrl+X, Y, Enter)

4. Add the MCP server using the wrapper script:
```bash
claude mcp add azure-search bash /home/azureuser/mcprag/mcp_server_wrapper.sh
```

## Option 2: Pass Environment Variables Directly

If you have the variables already set in your shell:

1. First, export them:
```bash
export ACS_ENDPOINT="https://your-search-service.search.windows.net"
export ACS_ADMIN_KEY="your-admin-key-here"
```

2. Then add the server with literal values:
```bash
claude mcp add azure-search python /home/azureuser/mcprag/mcp_server_sota.py \
  -e ACS_ENDPOINT="https://your-search-service.search.windows.net" \
  -e ACS_ADMIN_KEY="your-admin-key-here"
```

## Option 3: Use Environment File

If you have a separate environment file:

1. Source your environment:
```bash
source ~/azure-env.sh  # or wherever your env file is
```

2. Add with the current values:
```bash
claude mcp add azure-search python /home/azureuser/mcprag/mcp_server_sota.py \
  -e ACS_ENDPOINT="$ACS_ENDPOINT" \
  -e ACS_ADMIN_KEY="$ACS_ADMIN_KEY"
```

## Verify Setup

After adding, verify the server is working:
```bash
claude mcp list
```

You should see:
```
azure-search: ... - ✓ Connected
```

## Troubleshooting

If you see "Failed to connect":
1. Check the server details: `claude mcp get azure-search`
2. Verify environment variables are not empty
3. Test the server manually: `ACS_ENDPOINT=xxx ACS_ADMIN_KEY=yyy python mcp_server_sota.py`
4. Check for Python errors in the output