#!/bin/bash
# Manual Cloudflare setup with step-by-step instructions
# Use this if the automated script has issues

set -e

echo "🔧 Manual Cloudflare Setup for Claude Code Gateway"
echo "=================================================="
echo ""
echo "This script will guide you through the manual setup process."
echo "You'll need to run commands and copy IDs as we go."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check wrangler
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not found. Please install it first:"
    echo "   npm install -g wrangler"
    exit 1
fi

echo -e "${GREEN}✓ Wrangler CLI found${NC}"
echo ""

# Step 1: Login
echo -e "${BLUE}Step 1: Cloudflare Authentication${NC}"
echo "------------------------------------"
echo "Run this command to login (if not already logged in):"
echo ""
echo "  wrangler login"
echo ""
read -p "Press Enter when you're logged in..."
echo ""

# Step 2: Get Account ID
echo -e "${BLUE}Step 2: Get Your Account ID${NC}"
echo "-----------------------------"
echo "Run this command:"
echo ""
echo "  wrangler whoami"
echo ""
echo "Look for your Account ID in the output."
echo ""
read -p "Enter your Account ID: " ACCOUNT_ID
echo ""

# Step 3: Create D1 Database
echo -e "${BLUE}Step 3: Create D1 Database${NC}"
echo "---------------------------"
echo "Run this command:"
echo ""
echo "  wrangler d1 create claude-code"
echo ""
echo "Copy the database_id from the output."
echo "It will look like: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
echo ""
read -p "Enter the Database ID: " DB_ID
echo ""

# Apply migrations
echo "Now let's apply the database migrations..."
echo "Run these commands:"
echo ""
echo "  wrangler d1 execute claude-code --file=migrations/0001_create_tables.sql --local"
echo "  wrangler d1 execute claude-code --file=migrations/0001_create_tables.sql --remote"
echo ""
read -p "Press Enter after running the migrations..."
echo ""

# Step 4: Create KV Namespace
echo -e "${BLUE}Step 4: Create KV Namespace${NC}"
echo "----------------------------"
echo "Run this command:"
echo ""
echo "  wrangler kv namespace create USER_PREFS"
echo ""
echo "Copy the 'id' value from the output."
echo ""
read -p "Enter the KV Namespace ID: " KV_ID
echo ""

# Step 5: Create R2 Bucket
echo -e "${BLUE}Step 5: Create R2 Bucket${NC}"
echo "-------------------------"
echo "Run this command:"
echo ""
echo "  wrangler r2 bucket create claude-code-files"
echo ""
read -p "Press Enter after creating the bucket..."
echo ""

# Set CORS
echo "Now let's set CORS for the R2 bucket..."
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
echo "Run this command:"
echo ""
echo "  wrangler r2 bucket cors put claude-code-files --rules /tmp/r2-cors.json"
echo ""
read -p "Press Enter after setting CORS..."
rm /tmp/r2-cors.json
echo ""

# Step 6: Create Queue
echo -e "${BLUE}Step 6: Create Queue${NC}"
echo "---------------------"
echo "Run this command:"
echo ""
echo "  wrangler queues create claude-code-jobs"
echo ""
read -p "Press Enter after creating the queue..."
echo ""

# Step 7: Update wrangler.toml
echo -e "${BLUE}Step 7: Updating wrangler.toml${NC}"
echo "--------------------------------"

# Backup
cp wrangler.toml wrangler.toml.backup

# Update with sed
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" wrangler.toml
    sed -i '' "s/YOUR_D1_DATABASE_ID/$DB_ID/g" wrangler.toml
    sed -i '' "s/YOUR_KV_NAMESPACE_ID/$KV_ID/g" wrangler.toml
else
    # Linux
    sed -i "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" wrangler.toml
    sed -i "s/YOUR_D1_DATABASE_ID/$DB_ID/g" wrangler.toml
    sed -i "s/YOUR_KV_NAMESPACE_ID/$KV_ID/g" wrangler.toml
fi

echo -e "${GREEN}✓ Updated wrangler.toml${NC}"
echo ""

# Step 8: Create .env.production
echo -e "${BLUE}Step 8: Creating Environment File${NC}"
echo "-----------------------------------"

cat > .env.production << EOF
# Cloudflare Configuration
ACCOUNT_ID=$ACCOUNT_ID
D1_DATABASE_ID=$DB_ID
KV_NAMESPACE_ID=$KV_ID
R2_BUCKET_NAME=claude-code-files
QUEUE_NAME=claude-code-jobs

# Update these values:
BRIDGE_URL=https://bridge.yourdomain.com/exec
ANTHROPIC_API_KEY=sk-ant-your-key-here
WORKER_URL=https://claude-code-gateway.workers.dev

# Optional
TURNSTILE_SECRET=
ACCESS_JWT_SECRET=
EOF

echo -e "${GREEN}✓ Created .env.production${NC}"
echo ""

# Step 9: Deploy
echo -e "${BLUE}Step 9: Deploy the Worker${NC}"
echo "--------------------------"
echo "Run these commands to deploy:"
echo ""
echo "  npm run build"
echo "  wrangler deploy"
echo ""
read -p "Press Enter after deploying..."
echo ""

# Summary
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "=================="
echo ""
echo "Resources configured:"
echo "  • Account ID: $ACCOUNT_ID"
echo "  • D1 Database ID: $DB_ID"
echo "  • KV Namespace ID: $KV_ID"
echo "  • R2 Bucket: claude-code-files"
echo "  • Queue: claude-code-jobs"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Edit .env.production and update:"
echo "   - BRIDGE_URL with your actual domain"
echo "   - ANTHROPIC_API_KEY with your API key"
echo "   - WORKER_URL with your worker URL"
echo ""
echo "2. Configure DNS in Cloudflare Dashboard:"
echo "   - Add CNAME for your worker domain"
echo "   - Add CNAME for your bridge tunnel"
echo ""
echo "3. Set up Cloudflare Tunnel:"
echo "   ./scripts/setup-tunnel.sh"
echo ""
echo "4. Start your bridge server:"
echo "   npm run dev:server"
echo ""
echo "Done! Your Cloudflare resources are configured."