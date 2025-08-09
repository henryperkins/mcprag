# Claude Code Cloudflare Deployment Guide

This guide covers the complete production deployment of Claude Code with Cloudflare Workers as the edge gateway.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│   CF Worker  │────▶│   Bridge    │
│  (React UI) │◀────│   (Gateway)  │◀────│  (Node.js)  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                      │
                    ┌──────┴──────┐      ┌───────┴────────┐
                    │ D1/KV/R2/DO │      │ Claude Code    │
                    │  (Storage)  │      │ SDK/CLI        │
                    └─────────────┘      └────────────────┘
```

## Prerequisites

- Cloudflare account with Workers enabled
- Node.js 18+ on your bridge server
- Domain configured in Cloudflare
- `@anthropic-ai/claude-code` installed globally

## Step 1: Set Up Cloudflare Resources

### 1.1 Create D1 Database

```bash
# Create the database
wrangler d1 create claude-code

# Note the database_id and update wrangler.toml
# Apply migrations
wrangler d1 migrations apply claude-code --local
wrangler d1 migrations apply claude-code --remote
```

### 1.2 Create KV Namespace

```bash
# Create KV namespace for preferences
wrangler kv namespace create USER_PREFS

# Note the namespace_id and update wrangler.toml
```

### 1.3 Create R2 Bucket

```bash
# Create R2 bucket for file attachments
wrangler r2 bucket create claude-code-files
```

### 1.4 Create Queue

```bash
# Create queue for background jobs
wrangler queues create claude-code-jobs
```

## Step 2: Deploy the Worker Gateway

### 2.1 Configure wrangler.toml

Update the IDs in `wrangler.toml`:

```toml
account_id = "your-account-id"

[[d1_databases]]
database_id = "your-d1-id"

[[kv_namespaces]]
id = "your-kv-id"
```

### 2.2 Deploy Worker

```bash
# Deploy to Cloudflare
npm run deploy

# Or deploy to specific environment
wrangler deploy --env production
```

## Step 3: Set Up the Bridge Server

### 3.1 Install Dependencies

On your VM or server:

```bash
# Install Claude Code globally
npm install -g @anthropic-ai/claude-code

# Install bridge dependencies
cd fancy-leaf-b943
npm install
```

### 3.2 Configure Environment

Create `.env.bridge`:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
BRIDGE_PORT=8787
NODE_ENV=production
```

### 3.3 Set Up Cloudflare Tunnel

Run the setup script:

```bash
./scripts/setup-tunnel.sh
```

Follow the prompts to:
1. Authenticate with Cloudflare
2. Create the tunnel
3. Configure DNS (add CNAME record)

### 3.4 Start the Bridge

```bash
# Build TypeScript
npm run build:server

# Start with PM2 (recommended)
pm2 start dist-server/bridge-server.js --name claude-bridge

# Or use systemd service
sudo systemctl start claude-bridge
```

## Step 4: Configure DNS

### 4.1 Worker Domain

Add DNS records for your Worker:

```
Type: CNAME
Name: claude-api
Target: claude-code-gateway.workers.dev
Proxied: Yes
```

### 4.2 Bridge Domain (via Tunnel)

The tunnel setup script will provide the CNAME:

```
Type: CNAME
Name: bridge
Target: <tunnel-id>.cfargotunnel.com
Proxied: Yes
```

## Step 5: Security Configuration

### 5.1 Cloudflare Access (Zero Trust)

1. Go to Cloudflare Zero Trust dashboard
2. Create Access Application:
   - Name: Claude Code API
   - Domain: claude-api.yourdomain.com
   - Policy: Configure SSO/Email/Service Token

### 5.2 Rate Limiting

Add rate limiting rules in Cloudflare:

```
Path: /api/claude/stream
Rate: 10 requests per minute per IP
Action: Block for 1 minute
```

### 5.3 Turnstile (Bot Protection)

1. Create Turnstile widget in Cloudflare
2. Add site key to React app
3. Add secret key to Worker environment

## Step 6: Update React Application

### 6.1 Environment Variables

Create `.env.production`:

```env
VITE_CLAUDE_GATEWAY_URL=https://claude-api.yourdomain.com
VITE_TURNSTILE_SITE_KEY=your-site-key
```

### 6.2 Build and Deploy UI

```bash
# Build the React app
npm run build

# Deploy to Cloudflare Pages
wrangler pages deploy dist/client --project-name claude-ui
```

## Step 7: Monitoring and Maintenance

### 7.1 Worker Analytics

Monitor in Cloudflare dashboard:
- Request count
- Error rate
- Response times
- Data usage

### 7.2 Logs

```bash
# Worker logs
wrangler tail

# Bridge logs
pm2 logs claude-bridge

# Tunnel logs
claude-tunnel logs
```

### 7.3 Database Maintenance

```bash
# Backup D1 database
wrangler d1 export claude-code --output backup.sql

# Clean old sessions (30 days)
wrangler d1 execute claude-code --command "DELETE FROM sessions WHERE created_at < datetime('now', '-30 days')"
```

## Production Checklist

- [ ] API keys configured and secured
- [ ] Cloudflare Tunnel running
- [ ] D1 database migrated
- [ ] KV namespace created
- [ ] R2 bucket configured
- [ ] Worker deployed
- [ ] DNS records added
- [ ] SSL certificates active
- [ ] Access policies configured
- [ ] Rate limiting enabled
- [ ] Monitoring set up
- [ ] Backup strategy in place

## Troubleshooting

### Worker Returns 524 Timeout

- Check keep-alive in SSE stream
- Verify tunnel is running
- Check bridge server health

### Database Connection Issues

```bash
# Test D1 connection
wrangler d1 execute claude-code --command "SELECT 1"
```

### Tunnel Connection Failed

```bash
# Check tunnel status
cloudflared tunnel info <tunnel-name>

# Restart tunnel
claude-tunnel restart
```

### High Latency

- Enable Argo Smart Routing
- Check worker location
- Consider regional D1 placement

## Cost Optimization

### Workers Free Tier
- 100,000 requests/day
- 10ms CPU time per request

### D1 Free Tier
- 5GB storage
- 5 million rows read/day
- 100,000 rows written/day

### R2 Free Tier
- 10GB storage
- 1 million Class A operations
- 10 million Class B operations

## Support

- [Cloudflare Workers Discord](https://discord.cloudflare.com)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [GitHub Issues](https://github.com/your-repo/issues)