# MCPRAG Remote Server Deployment Guide

## Overview
This guide covers deploying the mcprag MCP server for remote access with authentication and load balancing.

## Prerequisites

- Docker and Docker Compose installed
- Azure Search service configured
- Stytch account (optional, for authentication)
- Domain name with SSL certificates (for production)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/mcprag.git
cd mcprag

# Copy environment configuration
cp .env.remote.example .env.remote

# Edit configuration
nano .env.remote
```

### 2. Install Dependencies

```bash
# Install base requirements
pip install -r requirements.txt

# Install remote server requirements
pip install -r requirements-remote.txt
```

### 3. Local Testing

```bash
# Run the remote server locally
python -m mcprag.remote_server

# In another terminal, test the health endpoint
curl http://localhost:8001/health
```

### 4. Docker Deployment

```bash
# Build and start services
docker-compose -f docker-compose.remote.yml up -d

# Check logs
docker-compose -f docker-compose.remote.yml logs -f

# Scale read replicas
docker-compose -f docker-compose.remote.yml up -d --scale mcprag-remote=3
```

## Configuration

### Environment Variables

Key environment variables for remote deployment:

| Variable | Description | Required |
|----------|-------------|----------|
| `ACS_ENDPOINT` | Azure Search endpoint | Yes |
| `ACS_QUERY_KEY` | Read-only key for search | Yes |
| `ACS_ADMIN_KEY` | Admin key for write ops | Yes (admin server) |
| `STYTCH_PROJECT_ID` | Stytch project ID | No (auth disabled if missing) |
| `STYTCH_SECRET` | Stytch secret key | No |
| `REDIS_URL` | Redis connection URL | No (in-memory fallback) |
| `MCP_BASE_URL` | Public server URL | Yes |
| `MCP_ADMIN_EMAILS` | Admin user emails | No |
| `MCP_DEVELOPER_DOMAINS` | Developer email domains | No |

### Security Tiers

Tools are classified into security tiers:

1. **Public** (no auth required in dev mode):
   - `search_code`, `search_code_raw`, `search_microsoft_docs`
   - `explain_ranking`, `preview_query_processing`
   - `health_check`, `index_status`, `cache_stats`

2. **Developer** (requires authentication):
   - `generate_code`, `analyze_context`
   - `submit_feedback`, `track_search_click`, `track_search_outcome`

3. **Admin** (requires auth + MFA):
   - All index management tools
   - All document management tools
   - Cache clearing operations

## Authentication

### Magic Link Flow

1. User requests authentication:
```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

2. User receives email with magic link
3. User clicks link or extracts token
4. Complete authentication:
```bash
curl "http://localhost:8001/auth/callback?token=TOKEN_FROM_EMAIL"
```

### Using the CLI Client

```bash
# Authenticate
./bin/mcprag-remote auth user@example.com

# Search code
./bin/mcprag-remote search "authentication middleware"

# List available tools
./bin/mcprag-remote list

# Execute any tool
./bin/mcprag-remote tool generate_code '{"description":"REST API client"}'
```

### Using the Python Client

```python
import asyncio
from mcprag_client import MCPRAGClient

async def main():
    async with MCPRAGClient() as client:
        # Authenticate
        await client.authenticate("user@example.com")
        # Complete with token from email
        await client.complete_auth("token_from_email")
        
        # Search code
        results = await client.search_code("authentication")
        print(results)

asyncio.run(main())
```

## Production Deployment

### 1. SSL/TLS Setup

Add SSL certificates to `nginx/certs/`:
```bash
mkdir -p nginx/certs
cp /path/to/cert.pem nginx/certs/
cp /path/to/key.pem nginx/certs/
```

Update nginx.conf to enable HTTPS:
```nginx
server {
    listen 443 ssl http2;
    server_name mcp.yourcompany.com;
    
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    # ... rest of config
}
```

### 2. Scaling Considerations

- **Read Replicas**: Scale `mcprag-remote` service for read operations
- **Single Admin**: Keep `mcprag-admin` as single instance for consistency
- **Redis**: Consider Redis Cluster for high availability
- **Load Balancer**: Nginx handles load balancing automatically

### 3. Monitoring

The server exposes metrics at `/health`:
```bash
curl https://mcp.yourcompany.com/health
```

Monitor key metrics:
- Response times per tool
- Authentication success/failure rates
- Active sessions by tier
- Tool execution errors

### 4. Backup and Recovery

Regular backups recommended for:
- Redis session data
- Configuration files
- Audit logs

## Troubleshooting

### Common Issues

1. **Authentication not working**
   - Check Stytch credentials in environment
   - Verify Redis is running and accessible
   - Check email delivery for magic links

2. **Tools returning 403 Forbidden**
   - Verify user tier matches tool requirements
   - Check if MFA is required for admin tools
   - Ensure session hasn't expired

3. **Performance issues**
   - Scale read replicas: `docker-compose up -d --scale mcprag-remote=5`
   - Check Redis memory usage
   - Review nginx rate limiting settings

4. **Docker networking issues**
   - Ensure all services are on same network
   - Check service names in nginx upstream config
   - Verify port mappings

### Debug Mode

Enable debug logging:
```bash
export MCP_LOG_LEVEL=DEBUG
export MCP_DEBUG_TIMINGS=true
```

### Development Mode

For local development without Stytch:
```bash
export MCP_DEV_MODE=true
export STYTCH_PROJECT_ID=""
export STYTCH_SECRET=""
```

Verify the session helper endpoints while in dev mode:
```bash
curl -s http://localhost:8001/auth/me -H 'Authorization: Bearer dev' | jq
curl -s -X POST http://localhost:8001/auth/logout -H 'Authorization: Bearer dev'
```

Auth endpoints available:
- POST `/auth/login` — request magic link
- GET `/auth/callback?token=...` — complete login and create session
- GET `/auth/me` — inspect current session (requires `Authorization`)
- POST `/auth/logout` — invalidate current session (requires `Authorization`)
- POST `/auth/verify-mfa` — verify TOTP for admin tier
- POST `/auth/m2m/token` — service token (Stytch or dev-mode mock)

## Security Best Practices

1. **Use environment-specific keys**
   - Never use admin keys in read-only servers
   - Rotate keys regularly

2. **Enable MFA for admin users**
   - Set `MCP_REQUIRE_MFA=true`
   - Configure TOTP in Stytch dashboard

3. **Configure rate limiting**
   - Adjust nginx rate limits based on usage
   - Monitor for abuse patterns

4. **Audit logging**
   - Review audit logs regularly
   - Set up alerts for suspicious activity

5. **Network security**
   - Use private networks for internal services
   - Expose only nginx to public internet
   - Configure firewall rules

## Rollback Procedure

If issues occur, rollback quickly:

```bash
# Stop remote services
docker-compose -f docker-compose.remote.yml down

# Restore previous version
git checkout previous-version

# Restart services
docker-compose -f docker-compose.remote.yml up -d
```

## Support

- GitHub Issues: https://github.com/yourusername/mcprag/issues
- Documentation: https://github.com/yourusername/mcprag/docs
- Email: support@yourcompany.com
