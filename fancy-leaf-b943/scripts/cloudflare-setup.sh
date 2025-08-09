#!/bin/bash
# Complete Cloudflare setup script for Claude Code Gateway
# Run this to configure all necessary resources

set -e

echo "🚀 Cloudflare Setup for Claude Code Gateway"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo -e "${RED}❌ Wrangler CLI not found${NC}"
    echo "Please install it first:"
    echo "  npm install -g wrangler"
    exit 1
fi

# Check if logged in
echo "📋 Checking Cloudflare authentication..."
if ! wrangler whoami &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Cloudflare${NC}"
    echo "Running: wrangler login"
    wrangler login
fi

echo -e "${GREEN}✓ Authenticated${NC}"
ACCOUNT_ID=$(wrangler whoami --json | jq -r '.account_id')
echo "Account ID: $ACCOUNT_ID"
echo ""

# Step 1: Create D1 Database
echo "1️⃣ Creating D1 Database..."
DB_NAME="claude-code"
if wrangler d1 list | grep -q "$DB_NAME"; then
    echo -e "${YELLOW}⚠️  Database '$DB_NAME' already exists${NC}"
    DB_ID=$(wrangler d1 list --json | jq -r ".[] | select(.name==\"$DB_NAME\") | .uuid")
else
    DB_OUTPUT=$(wrangler d1 create "$DB_NAME" --json)
    DB_ID=$(echo "$DB_OUTPUT" | jq -r '.uuid')
    echo -e "${GREEN}✓ Created database: $DB_NAME${NC}"
fi
echo "   Database ID: $DB_ID"

# Apply migrations
echo "   Applying migrations..."
if [ -f "migrations/0001_create_tables.sql" ]; then
    wrangler d1 execute "$DB_NAME" --file=migrations/0001_create_tables.sql --local
    wrangler d1 execute "$DB_NAME" --file=migrations/0001_create_tables.sql --remote
    echo -e "${GREEN}✓ Migrations applied${NC}"
else
    echo -e "${YELLOW}⚠️  No migration file found${NC}"
fi
echo ""

# Step 2: Create KV Namespace
echo "2️⃣ Creating KV Namespace..."
KV_NAME="USER_PREFS"
KV_OUTPUT=$(wrangler kv namespace create "$KV_NAME" --preview false 2>&1 || true)
if echo "$KV_OUTPUT" | grep -q "already exists"; then
    echo -e "${YELLOW}⚠️  KV namespace '$KV_NAME' already exists${NC}"
    # Get existing ID
    KV_ID=$(wrangler kv namespace list --json | jq -r ".[] | select(.title==\"claude-code-gateway-$KV_NAME\") | .id")
else
    KV_ID=$(echo "$KV_OUTPUT" | grep -oP 'id = "\K[^"]+')
    echo -e "${GREEN}✓ Created KV namespace: $KV_NAME${NC}"
fi
echo "   KV Namespace ID: $KV_ID"
echo ""

# Step 3: Create R2 Bucket
echo "3️⃣ Creating R2 Bucket..."
R2_BUCKET="claude-code-files"
if wrangler r2 bucket list | grep -q "$R2_BUCKET"; then
    echo -e "${YELLOW}⚠️  R2 bucket '$R2_BUCKET' already exists${NC}"
else
    wrangler r2 bucket create "$R2_BUCKET"
    echo -e "${GREEN}✓ Created R2 bucket: $R2_BUCKET${NC}"
fi

# Set CORS policy for R2
echo "   Setting CORS policy..."
cat > /tmp/r2-cors.json << 'EOF'
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
wrangler r2 bucket cors put "$R2_BUCKET" --rules /tmp/r2-cors.json
rm /tmp/r2-cors.json
echo -e "${GREEN}✓ CORS policy set${NC}"
echo ""

# Step 4: Create Queue
echo "4️⃣ Creating Queue..."
QUEUE_NAME="claude-code-jobs"
if wrangler queues list | grep -q "$QUEUE_NAME"; then
    echo -e "${YELLOW}⚠️  Queue '$QUEUE_NAME' already exists${NC}"
else
    wrangler queues create "$QUEUE_NAME"
    echo -e "${GREEN}✓ Created queue: $QUEUE_NAME${NC}"
fi
echo ""

# Step 5: Update wrangler.toml with IDs
echo "5️⃣ Updating wrangler.toml..."
WRANGLER_FILE="wrangler.toml"

# Backup original
cp "$WRANGLER_FILE" "$WRANGLER_FILE.backup"

# Update with actual IDs using sed
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" "$WRANGLER_FILE"
    sed -i '' "s/YOUR_D1_DATABASE_ID/$DB_ID/g" "$WRANGLER_FILE"
    sed -i '' "s/YOUR_KV_NAMESPACE_ID/$KV_ID/g" "$WRANGLER_FILE"
else
    # Linux
    sed -i "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" "$WRANGLER_FILE"
    sed -i "s/YOUR_D1_DATABASE_ID/$DB_ID/g" "$WRANGLER_FILE"
    sed -i "s/YOUR_KV_NAMESPACE_ID/$KV_ID/g" "$WRANGLER_FILE"
fi

echo -e "${GREEN}✓ Updated wrangler.toml with resource IDs${NC}"
echo ""

# Step 6: Deploy Worker
echo "6️⃣ Deploying Worker..."
echo "Building and deploying..."
npm run build
wrangler deploy

WORKER_URL=$(wrangler deployments list --json | jq -r '.[0].url' 2>/dev/null || echo "https://claude-code-gateway.workers.dev")
echo -e "${GREEN}✓ Worker deployed${NC}"
echo "   URL: $WORKER_URL"
echo ""

# Step 7: Create environment variables file
echo "7️⃣ Creating environment configuration..."
cat > .env.production << EOF
# Cloudflare Configuration (auto-generated)
ACCOUNT_ID=$ACCOUNT_ID
D1_DATABASE_ID=$DB_ID
KV_NAMESPACE_ID=$KV_ID
R2_BUCKET_NAME=$R2_BUCKET
QUEUE_NAME=$QUEUE_NAME
WORKER_URL=$WORKER_URL

# Bridge Configuration (update these)
BRIDGE_URL=https://bridge.yourdomain.com/exec
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional Security
TURNSTILE_SECRET=
ACCESS_JWT_SECRET=
EOF

echo -e "${GREEN}✓ Created .env.production${NC}"
echo ""

# Step 8: Display DNS instructions
echo "8️⃣ DNS Configuration Required"
echo "=============================="
echo ""
echo "Add these DNS records in Cloudflare Dashboard:"
echo ""
echo "1. For Worker (if using custom domain):"
echo "   Type: CNAME"
echo "   Name: claude-api"
echo "   Target: $WORKER_URL"
echo "   Proxy: ✓ (Orange cloud ON)"
echo ""
echo "2. For Bridge (via Cloudflare Tunnel):"
echo "   Type: CNAME"
echo "   Name: bridge"
echo "   Target: <tunnel-id>.cfargotunnel.com"
echo "   Proxy: ✓ (Orange cloud ON)"
echo ""

# Step 9: Summary
echo "📊 Setup Summary"
echo "==============="
echo ""
echo -e "${GREEN}✅ Resources Created:${NC}"
echo "   • D1 Database: $DB_NAME ($DB_ID)"
echo "   • KV Namespace: $KV_NAME ($KV_ID)"
echo "   • R2 Bucket: $R2_BUCKET"
echo "   • Queue: $QUEUE_NAME"
echo "   • Worker: Deployed to $WORKER_URL"
echo ""
echo -e "${YELLOW}⚠️  Next Steps:${NC}"
echo "1. Update BRIDGE_URL in .env.production"
echo "2. Add your ANTHROPIC_API_KEY"
echo "3. Configure DNS records (see above)"
echo "4. Set up Cloudflare Tunnel: ./scripts/setup-tunnel.sh"
echo "5. Start bridge server: npm run dev:server"
echo ""
echo -e "${GREEN}🎉 Cloudflare setup complete!${NC}"

# Optional: Test the deployment
echo ""
read -p "Would you like to test the Worker deployment? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Testing Worker health endpoint..."
    curl -s "$WORKER_URL/api/health" | jq . || echo "Health check failed - this is normal if CORS is blocking the request"
fi