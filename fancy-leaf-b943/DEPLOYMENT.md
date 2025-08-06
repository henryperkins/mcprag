# Claude Code UI Deployment Guide

## Prerequisites

1. Node.js 18+ installed
2. Cloudflare account
3. Anthropic API key

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure API Key

The Anthropic API key must be configured as a Cloudflare secret (not in wrangler.jsonc for security):

```bash
# For local development
echo "ANTHROPIC_API_KEY=your-api-key-here" > .dev.vars

# For production deployment
wrangler secret put ANTHROPIC_API_KEY
# Enter your API key when prompted
```

### 3. Optional: Configure MCP Servers

If you want to use MCP (Model Context Protocol) servers, update the `MCP_CONFIG` variable in `wrangler.jsonc`:

```jsonc
"vars": {
  "MCP_CONFIG": "{\"servers\":[{\"name\":\"my-mcp-server\",\"url\":\"http://localhost:3000\"}]}"
}
```

### 4. Build the Application

```bash
npm run build
```

### 5. Test Locally

```bash
npm run dev
```

The application will be available at http://localhost:5173

### 6. Deploy to Cloudflare

```bash
npm run deploy
```

## Testing the Integration

### Basic Test
```bash
# Test health endpoint
curl http://localhost:5173/api/health

# Test with a simple query
curl -N -H "Content-Type: application/json" \
  -X POST http://localhost:5173/api/query \
  -d '{"prompt":"Hello, Claude!"}'
```

### Test with Tools
```bash
# Test with file operations
curl -N -H "Content-Type: application/json" \
  -X POST http://localhost:5173/api/query \
  -d '{
    "prompt": "Create a hello.txt file with 'Hello World' content",
    "allowedTools": ["Write"],
    "permissionMode": "acceptEdits"
  }'
```

### Test Interrupt
```bash
# Start a long-running query and get the session ID from the response
# Then interrupt it:
curl -H "Content-Type: application/json" \
  -X POST http://localhost:5173/api/interrupt \
  -d '{"sessionId":"your-session-id-here"}'
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key (set as secret) |
| `MCP_CONFIG` | No | JSON string with MCP server configuration |
| `CLAUDE_CODE_USE_BEDROCK` | No | Set to "true" to use AWS Bedrock |
| `CLAUDE_CODE_USE_VERTEX` | No | Set to "true" to use Google Vertex AI |

## Troubleshooting

### API Key Not Working
- Ensure the API key is set as a secret, not in wrangler.jsonc
- For local dev, create a `.dev.vars` file
- For production, use `wrangler secret put ANTHROPIC_API_KEY`

### Build Errors
- Ensure you're using Node.js 18 or higher
- Try clearing node_modules and reinstalling: `rm -rf node_modules && npm install`
- Check that TypeScript version matches: `npm ls typescript`

### Streaming Not Working
- Check browser console for CORS errors
- Ensure the Worker is returning proper SSE headers
- Verify the API key has appropriate permissions

### MCP Not Connecting
- Verify MCP_CONFIG is valid JSON
- Check MCP server URLs are accessible from Cloudflare Workers
- Review Worker logs: `wrangler tail`

## Production Considerations

1. **Rate Limiting**: Consider implementing rate limiting for the API endpoints
2. **Authentication**: Add user authentication if deploying publicly
3. **Monitoring**: Use Cloudflare Analytics and Workers Analytics
4. **Caching**: Consider caching responses for common queries
5. **Error Handling**: Implement comprehensive error logging
6. **CORS**: Update CORS headers to restrict to your domain in production

## Security Notes

- Never commit API keys to version control
- Use Cloudflare secrets for all sensitive data
- Restrict CORS origins in production
- Implement request validation and sanitization
- Consider adding authentication for public deployments