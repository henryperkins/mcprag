# Quick Deployment Guide - Make MCPRAG Accessible Now

## Option 1: Quick Local Test (5 minutes)

### Step 1: Create `.env.remote` file
```bash
# Create environment file
cat > .env.remote << 'EOF'
# Azure Search (REQUIRED - you already have these)
ACS_ENDPOINT=https://your-search.search.windows.net
ACS_ADMIN_KEY=your-admin-key-here
ACS_INDEX_NAME=codebase-mcp-sota

# Authentication (OPTIONAL - leave empty for dev mode)
STYTCH_PROJECT_ID=
STYTCH_SECRET=
MCP_DEV_MODE=true

# Server Config
MCP_BASE_URL=http://localhost:8001
MCP_ALLOWED_ORIGINS=*
MCP_LOG_LEVEL=INFO

# Session
SESSION_DURATION_MINUTES=480
EOF
```

### Step 2: Install and Run
```bash
# Install remote dependencies
pip install fastapi uvicorn sse-starlette redis

# Run the server
python -m mcprag.remote_server
```

### Step 3: Test Access
```bash
# Check it's working
curl http://localhost:8001/health

# Try a search (no auth needed in dev mode)
curl -X POST http://localhost:8001/mcp/tool/search_code \
  -H "Content-Type: application/json" \
  -d '{"query":"server","max_results":3}'
```

**✅ Server is now accessible at http://localhost:8001**

---

## Option 2: Docker Deployment (10 minutes)

### Step 1: Create `.env` file
```bash
# Copy your existing Azure Search credentials
cp .env .env.backup
echo "ACS_ENDPOINT=${ACS_ENDPOINT}" >> .env.remote
echo "ACS_ADMIN_KEY=${ACS_ADMIN_KEY}" >> .env.remote
echo "MCP_DEV_MODE=true" >> .env.remote
```

### Step 2: Deploy with Docker
```bash
# Start all services
docker-compose -f docker-compose.remote.yml up -d

# Check logs
docker-compose -f docker-compose.remote.yml logs -f
```

### Step 3: Access Points
- **API**: http://localhost:8001
- **Admin**: http://localhost:8002 
- **Health**: http://localhost:8001/health

---

## Option 3: Public Internet Access (30 minutes)

### Step 1: Use ngrok for Quick Public Access
```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Start your server
python -m mcprag.remote_server

# In another terminal, expose it
ngrok http 8001

# You'll get a public URL like:
# https://abc123.ngrok.io -> http://localhost:8001
```

### Step 2: Share the URL
Your MCP server is now accessible at the ngrok URL!

---

## Option 4: Production Deployment (2 hours)

### Prerequisites
- Domain name (e.g., mcp.yourcompany.com)
- SSL certificate
- Linux server with Docker

### Step 1: Server Setup
```bash
# On your server
git clone https://github.com/yourusername/mcprag.git
cd mcprag

# Configure environment
cp .env.remote.example .env.remote
nano .env.remote  # Add your credentials
```

### Step 2: SSL Setup
```bash
# Add certificates
mkdir -p nginx/certs
cp /path/to/cert.pem nginx/certs/
cp /path/to/key.pem nginx/certs/
```

### Step 3: Deploy
```bash
# Start services
docker-compose -f docker-compose.remote.yml up -d

# Enable firewall
ufw allow 443/tcp
ufw allow 80/tcp
```

### Step 4: DNS Configuration
Point your domain to the server IP:
```
mcp.yourcompany.com -> YOUR_SERVER_IP
```

**✅ Server accessible at https://mcp.yourcompany.com**

---

## Quick Test Commands

### Without Authentication (Dev Mode)
```bash
# Search code
curl -X POST http://localhost:8001/mcp/tool/search_code \
  -H "Content-Type: application/json" \
  -d '{"query":"authentication","max_results":5}'

# List available tools
curl http://localhost:8001/mcp/tools

# Check health
curl http://localhost:8001/health
```

### With Authentication (Production)
```bash
# 1. Request magic link
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com"}'

# 2. Get token from email, then:
TOKEN="your-token-here"

# 3. Use authenticated endpoints
curl -X POST http://localhost:8001/mcp/tool/search_code \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","max_results":5}'
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process using port 8001
lsof -i :8001
kill -9 <PID>
```

### Module Not Found
```bash
pip install -r requirements-remote.txt
```

### Docker Issues
```bash
# Reset everything
docker-compose -f docker-compose.remote.yml down -v
docker-compose -f docker-compose.remote.yml up --build
```

### Can't Connect Remotely
1. Check firewall: `ufw status`
2. Check server is listening: `netstat -tlnp | grep 8001`
3. Test locally first: `curl localhost:8001/health`

---

## What You Get

Once deployed, you can:
- Access all 30+ MCP tools via REST API
- Use from any programming language
- Share with team members
- Integrate with Claude, VS Code, or any MCP client
- Stream responses via SSE
- Control access with authentication (optional)

**Need help?** The server is designed to work with minimal configuration. Just set your Azure Search credentials and run!