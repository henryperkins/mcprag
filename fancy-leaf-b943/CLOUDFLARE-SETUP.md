# Cloudflare Configuration Guide

This guide covers all configurations needed in the Cloudflare portal and via Wrangler CLI.

## Quick Setup

Run the automated setup script:
```bash
./scripts/cloudflare-setup.sh
```

This will create all necessary resources and update your configuration files.

## Manual Configuration Steps

### 1. Prerequisites

#### Install Wrangler CLI
```bash
npm install -g wrangler
```

#### Authenticate with Cloudflare
```bash
wrangler login
```

### 2. Create D1 Database

```bash
# Create database
wrangler d1 create claude-code

# Note the database_id from output
# Example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Apply migrations
wrangler d1 execute claude-code --file=migrations/0001_create_tables.sql --local
wrangler d1 execute claude-code --file=migrations/0001_create_tables.sql --remote
```

### 3. Create KV Namespace

```bash
# Create KV namespace
wrangler kv namespace create USER_PREFS

# Note the id from output
# Example output: { binding = "USER_PREFS", id = "xxxxxxxxxxxx" }
```

### 4. Create R2 Bucket

```bash
# Create R2 bucket
wrangler r2 bucket create claude-code-files

# Set CORS policy
cat > r2-cors.json << 'EOF'
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
EOF

wrangler r2 bucket cors put claude-code-files --rules r2-cors.json
```

### 5. Create Queue

```bash
# Create queue
wrangler queues create claude-code-jobs
```

### 6. Update wrangler.toml

Replace the placeholder IDs in `wrangler.toml`:

```toml
account_id = "YOUR_ACTUAL_ACCOUNT_ID"

[[d1_databases]]
binding = "DB"
database_name = "claude-code"
database_id = "YOUR_D1_DATABASE_ID"  # From step 2

[[kv_namespaces]]
binding = "USER_PREFS"
id = "YOUR_KV_NAMESPACE_ID"  # From step 3
```

### 7. Deploy the Worker

```bash
# Build and deploy
npm run build
wrangler deploy

# Or deploy to production
wrangler deploy --env production
```

## Cloudflare Dashboard Configuration

### 1. DNS Records

Go to your domain in Cloudflare Dashboard → DNS:

#### For Worker (Custom Domain)
- **Type**: CNAME or Worker Route
- **Name**: `claude-api` (or your preferred subdomain)
- **Target**: `claude-code-gateway.workers.dev`
- **Proxy**: ✓ (Orange cloud ON)

#### For Bridge (via Tunnel)
- **Type**: CNAME
- **Name**: `bridge`
- **Target**: `<tunnel-id>.cfargotunnel.com`
- **Proxy**: ✓ (Orange cloud ON)

### 2. Worker Routes (Alternative to DNS)

Go to Workers & Pages → your worker → Triggers:

1. Add Custom Domain:
   - `claude-api.yourdomain.com`

2. Or Add Route:
   - Route: `claude-api.yourdomain.com/*`
   - Zone: `yourdomain.com`

### 3. Environment Variables

Go to Workers & Pages → your worker → Settings → Variables:

```
BRIDGE_URL = https://bridge.yourdomain.com/exec
ANTHROPIC_API_KEY = sk-ant-your-key-here  # (Encrypt this)
TURNSTILE_SECRET = your-turnstile-secret  # (Optional)
ACCESS_JWT_SECRET = your-access-secret    # (Optional)
```

### 4. Cloudflare Tunnel Setup

```bash
# Install cloudflared
# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Login and create tunnel
cloudflared tunnel login
cloudflared tunnel create claude-code-bridge

# Create config file (~/.cloudflared/config.yml)
tunnel: <tunnel-id>
credentials-file: /home/user/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: bridge.yourdomain.com
    service: http://localhost:8787
  - service: http_status:404

# Run tunnel
cloudflared tunnel run claude-code-bridge
```

### 5. Security Configuration (Optional)

#### Cloudflare Access (Zero Trust)

1. Go to Zero Trust → Access → Applications
2. Create Application:
   - **Name**: Claude Code API
   - **Domain**: `claude-api.yourdomain.com`
   - **Path**: `/api/*`

3. Create Policy:
   - **Name**: Authorized Users
   - **Action**: Allow
   - **Include**: Email ends with `@yourdomain.com`

#### Rate Limiting

1. Go to Security → WAF → Rate limiting rules
2. Create Rule:
   - **Name**: API Rate Limit
   - **If**: URI Path contains `/api/claude/stream`
   - **Then**: Block for 1 minute
   - **Rate**: 10 requests per 1 minute per IP

#### Turnstile (Bot Protection)

1. Go to Turnstile
2. Add Site:
   - **Site name**: Claude Code
   - **Domain**: `claude-api.yourdomain.com`
3. Note the Site Key and Secret Key
4. Add to Worker environment variables

## Testing Your Setup

### 1. Test Worker Health
```bash
curl https://claude-code-gateway.workers.dev/api/health
# or
curl https://claude-api.yourdomain.com/api/health
```

### 2. Test D1 Database
```bash
wrangler d1 execute claude-code --command "SELECT 1"
```

### 3. Test KV Namespace
```bash
wrangler kv key put --binding=USER_PREFS test-key "test-value"
wrangler kv key get --binding=USER_PREFS test-key
```

### 4. Test R2 Bucket
```bash
echo "test" | wrangler r2 object put claude-code-files/test.txt --pipe
wrangler r2 object get claude-code-files/test.txt
```

### 5. Test Complete Flow
```bash
# Start bridge server locally
npm run dev:server

# Start tunnel
cloudflared tunnel run claude-code-bridge

# Test via Worker
curl -X POST https://claude-api.yourdomain.com/api/claude/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Claude", "opts": {}}'
```

## Monitoring

### Worker Analytics
- Go to Workers & Pages → your worker → Analytics
- Monitor: Requests, Errors, CPU time, Duration

### D1 Metrics
```bash
# Check database size
wrangler d1 info claude-code

# Query metrics
wrangler d1 execute claude-code --command "SELECT COUNT(*) FROM sessions"
```

### Logs
```bash
# Real-time logs
wrangler tail

# With filters
wrangler tail --format pretty --status error
```

## Troubleshooting

### Common Issues

#### Worker Not Responding
- Check deployment: `wrangler deployments list`
- Check logs: `wrangler tail`
- Verify routes in dashboard

#### D1 Connection Failed
- Verify database ID in wrangler.toml
- Check migrations: `wrangler d1 migrations list claude-code`

#### Tunnel Not Connecting
- Check tunnel status: `cloudflared tunnel info <tunnel-name>`
- Verify DNS record points to tunnel
- Check tunnel logs: `cloudflared tunnel run --loglevel debug`

#### CORS Errors
- Add your domain to Worker CORS headers
- Check R2 bucket CORS policy
- Verify Cloudflare proxy is enabled (orange cloud)

## Cost Considerations

### Free Tier Limits
- **Workers**: 100,000 requests/day, 10ms CPU/invocation
- **D1**: 5GB storage, 5M rows read/day, 100K rows written/day
- **KV**: 100,000 reads/day, 1,000 writes/day
- **R2**: 10GB storage, 1M Class A operations/month
- **Queues**: 1M messages/month

### Optimization Tips
1. Enable KV caching for user preferences
2. Use D1 batch operations
3. Implement request coalescing
4. Set appropriate cache headers
5. Use Cloudflare's edge cache

## Next Steps

1. ✅ Run `./scripts/cloudflare-setup.sh`
2. ✅ Update environment variables
3. ✅ Configure DNS records
4. ✅ Set up Cloudflare Tunnel
5. ✅ Deploy and test
6. 🔒 Configure security (Access, Rate Limiting)
7. 📊 Set up monitoring alerts
8. 🚀 Go live!