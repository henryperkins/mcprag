#!/bin/bash
# Setup Cloudflare Tunnel for Claude Code Bridge
# This exposes your local bridge server securely without opening ports

set -e

echo "🚇 Cloudflare Tunnel Setup for Claude Code Bridge"
echo "================================================"

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "📦 Installing cloudflared..."
    
    # Detect OS and install accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb
        rm cloudflared-linux-amd64.deb
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install cloudflare/cloudflare/cloudflared
        else
            echo "Please install Homebrew first: https://brew.sh"
            exit 1
        fi
    else
        echo "Unsupported OS. Please install cloudflared manually:"
        echo "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    fi
fi

# Login to Cloudflare
echo ""
echo "🔐 Authenticating with Cloudflare..."
cloudflared tunnel login

# Create tunnel
TUNNEL_NAME="claude-code-bridge-$(date +%s)"
echo ""
echo "🚇 Creating tunnel: $TUNNEL_NAME"
cloudflared tunnel create $TUNNEL_NAME

# Get tunnel ID
TUNNEL_ID=$(cloudflared tunnel list --name $TUNNEL_NAME --output json | jq -r '.[0].id')
echo "   Tunnel ID: $TUNNEL_ID"

# Create config file
CONFIG_FILE="$HOME/.cloudflared/config.yml"
echo ""
echo "📝 Creating tunnel configuration..."

cat > $CONFIG_FILE << EOF
tunnel: $TUNNEL_ID
credentials-file: $HOME/.cloudflared/$TUNNEL_ID.json

ingress:
  # Claude Code Bridge
  - hostname: bridge.yourdomain.com
    service: http://localhost:8787
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      
  # Health check endpoint
  - hostname: bridge-health.yourdomain.com
    service: http://localhost:8787/health
    
  # Catch-all rule (required)
  - service: http_status:404
EOF

echo "   Config saved to: $CONFIG_FILE"

# Route DNS
echo ""
echo "🌐 Setting up DNS routing..."
echo "   Please add a CNAME record in your Cloudflare dashboard:"
echo "   bridge.yourdomain.com → $TUNNEL_ID.cfargotunnel.com"
echo ""
echo "   Or run this command if you have DNS API access:"
echo "   cloudflared tunnel route dns $TUNNEL_NAME bridge.yourdomain.com"

# Create systemd service (Linux) or launchd plist (macOS)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "🔧 Creating systemd service..."
    
    sudo tee /etc/systemd/system/cloudflared-bridge.service > /dev/null << EOF
[Unit]
Description=Cloudflare Tunnel for Claude Code Bridge
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/bin/cloudflared tunnel run $TUNNEL_NAME
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable cloudflared-bridge
    
    echo "   Service created: cloudflared-bridge"
    echo ""
    echo "📌 To start the tunnel:"
    echo "   sudo systemctl start cloudflared-bridge"
    echo ""
    echo "📊 To check status:"
    echo "   sudo systemctl status cloudflared-bridge"
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "🔧 Creating launchd service..."
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.cloudflare.bridge.plist"
    
    cat > $PLIST_FILE << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cloudflare.bridge</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/cloudflared</string>
        <string>tunnel</string>
        <string>run</string>
        <string>$TUNNEL_NAME</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/cloudflared-bridge.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cloudflared-bridge.error.log</string>
</dict>
</plist>
EOF
    
    echo "   Service created: com.cloudflare.bridge"
    echo ""
    echo "📌 To start the tunnel:"
    echo "   launchctl load $PLIST_FILE"
    echo ""
    echo "📊 To check logs:"
    echo "   tail -f /tmp/cloudflared-bridge.log"
fi

# Create convenience script
SCRIPT_FILE="$HOME/bin/claude-tunnel"
mkdir -p $HOME/bin

cat > $SCRIPT_FILE << 'EOF'
#!/bin/bash
# Claude Code Tunnel Manager

case "$1" in
    start)
        echo "Starting tunnel..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl start cloudflared-bridge
        else
            launchctl load ~/Library/LaunchAgents/com.cloudflare.bridge.plist
        fi
        ;;
    stop)
        echo "Stopping tunnel..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl stop cloudflared-bridge
        else
            launchctl unload ~/Library/LaunchAgents/com.cloudflare.bridge.plist
        fi
        ;;
    status)
        echo "Tunnel status:"
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl status cloudflared-bridge
        else
            launchctl list | grep com.cloudflare.bridge
        fi
        ;;
    logs)
        echo "Showing tunnel logs..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo journalctl -u cloudflared-bridge -f
        else
            tail -f /tmp/cloudflared-bridge.log
        fi
        ;;
    test)
        echo "Testing tunnel connection..."
        curl -s https://bridge.yourdomain.com/health | jq .
        ;;
    *)
        echo "Usage: $0 {start|stop|status|logs|test}"
        exit 1
        ;;
esac
EOF

chmod +x $SCRIPT_FILE

echo ""
echo "✅ Tunnel setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update bridge.yourdomain.com to your actual domain"
echo "2. Add the CNAME record in Cloudflare DNS"
echo "3. Start your bridge server: npm run dev:server"
echo "4. Start the tunnel: claude-tunnel start"
echo "5. Update BRIDGE_URL in wrangler.toml"
echo ""
echo "🎯 Quick commands:"
echo "   claude-tunnel start  - Start tunnel"
echo "   claude-tunnel stop   - Stop tunnel"
echo "   claude-tunnel status - Check status"
echo "   claude-tunnel logs   - View logs"
echo "   claude-tunnel test   - Test connection"
echo ""
echo "📚 Documentation: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/"