# [[Debugging - Model Context Protocol]]

Effective debugging is crucial when building **MCP (Model Context Protocol)** servers or integrating them with applications. This guide consolidates the tools, common pitfalls, and best‑practice strategies you’ll need to troubleshoot and improve your MCP workflows.

---

## 📋 MCP Debugging Tools

| Tool | Purpose | Quick Link |
|------|---------|-----------|
| **MCP Inspector** | Interactive debugging UI; test servers directly | [Inspector guide](https://modelcontextprotocol.io/legacy/tools/inspector) |
| **Claude Desktop Developer Tools** | Integration testing, log collection, Chrome DevTools | – |
| **Server‑side Logging** | Custom log output, error tracking, performance metrics | – |

---

## 🖥️ Debugging in Claude Desktop

### 1️⃣ Check Server Status

1. Click the **MCP plug‑in** icon ![plugin](https://mintlify.s3.us-west-1.amazonaws.com/mcp/images/claude-desktop-mcp-plug-icon.svg) to see:
   - Connected servers
   - Available prompts & resources
2. Click the **“Search and tools”** slider ![slider](https://mintlify.s3.us-west-1.amazonaws.com/mcp/images/claude-desktop-mcp-slider.svg) to view tools that the model can call.

---

### 📜 Viewing Logs

```bash
# Follow MCP logs in real‑time (macOS)
tail -n 20 -F ~/Library/Logs/Claude/mcp*.log
```

The logs capture:

- Server connection events
- Configuration errors
- Runtime exceptions
- JSON‑RPC message payloads

---

### 🛠️ Using Chrome DevTools (Inside Claude Desktop)

1. Enable DevTools by creating `developer_settings.json`:

```json
{
  "allowDevTools": true
}
```

```bash
# macOS example
echo '{"allowDevTools": true}' > ~/Library/Application\ Support/Claude/developer_settings.json
```

2. Open DevTools: **⌘ Option Shift I** (or **F12**)

You’ll see two windows: the **main content** and the **title‑bar**. Use the **Console** for client‑side errors and the **Network** tab to inspect:

- Request/response payloads
- Connection timing
- HTTP status


---

## 🐞 Common Issues & Fixes

### 📂 Working Directory

- Servers launched via `claude_desktop_config.json` may run from an undefined directory (e.g., `/` on macOS).
- **Always** use **absolute** paths in config files and `.env` files.

```json
{
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "/Users/username/data"
  ]
}
```

**Never** use relative paths like `"./data"`.

---

### 🌐 Environment Variables

MCP servers only inherit a limited set of env vars (`USER`, `HOME`, `PATH`). To add custom variables:

```json
{
  "myweather": {
    "command": "my-weather-server",
    "env": {
      "API_KEY": "my_secret_key",
      "DEBUG": "true"
    }
  }
}
```

---

### 🛠️ Server Initialization

| Problem | Typical cause | Remedy |
|--------|--------------|-------|
| **Path Issues** | Wrong executable path, missing files, bad permissions | Use absolute paths; verify file permissions |
| **Configuration Errors** | Invalid JSON, missing fields, type mismatches | Validate JSON with a linter; check schema |
| **Environment Problems** | Missing env vars, wrong values, permission restrictions | Add `env` key; verify permissions |

---

### 🔌 Connection Problems

1. Check Claude Desktop logs (`mcp*.log`).
2. Confirm the server process is running (`ps`, `Task Manager`).
3. Test the server directly with **MCP Inspector**.
4. Verify that client and server are using the same MCP version.

---

## 🗂️ Implementing Logging

### Server‑Side Logging (StdIO Transport)

All messages written to **stderr** are automatically captured by the host (e.g., Claude Desktop).

**Best‑practice log events**:

- Server initialization steps
- Resource access / file reads
- Tool execution start & end
- Errors & stack traces
- Performance metrics (timings, sizes)

#### Example (Python)

```python
import logging
import sys

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
```

---

### Client‑Side Logging

1. Enable debug mode in your client (`DEBUG=1`).
2. Capture network traffic (e.g., `Wireshark`, browser devtools).
3. Log request/response pairs with request IDs.
4. Record error states (e.g., reconnection attempts).

---

## 🔄 Debugging Workflow

### Development Cycle

1. **Prototype** – Use **Inspector** for quick tests.
2. **Add Logging** – Structured `JSON` logs with timestamps and request IDs.
3. **Integrate** – Test in Claude Desktop; monitor logs and UI.
4. **Iterate** – Fix issues, update tests, repeat.

### Testing Changes Efficiently

| Change type | Action |
|------------|-------|
| **Configuration** | Restart Claude Desktop. |
| **Server code** | Use **Cmd‑R** (or restart the server) to reload. |
| **Small tweaks** | Use **MCP Inspector** for immediate feedback. |

---

## 🛠️ Best Practices

### Logging Strategy

- **Structured logs** (JSON) with fields: `timestamp`, `level`, `requestId`, `message`.
- **Error handling**: Log stack traces, context (input args, user ID).
- **Performance**: Log start/end timestamps; compute latency.
- **Sensitive data**: Redact secrets, PII.

### Security Considerations

1. **Sensitive data** – Sanitize logs; avoid printing API keys or tokens.
2. **Access control** – Verify permissions; use least‑privilege tokens.
3. **Audit** – Keep an audit trail of who/when changed configuration.

---

## 🙋 Getting Help

| Step | Action |
|------|-------|
| **First** | Check server logs (`mcp*.log`). |
| | Test with **MCP Inspector**. |
| | Verify config (`claude_desktop_config.json`). |
| | Double‑check environment variables. |
| **Support** | GitHub Issues (bug reports). |
| | GitHub Discussions (questions, best‑practice). |
| **When asking for help** | Provide log snippets; share config (redacted). |
| | Describe steps to reproduce. |
| | Include OS, MCP SDK version, transport type. |

---

## 🚀 Next Steps

- **Explore** the full **MCP Inspector** tutorial.
- **Add** structured logging to your server.
- **Enable** Chrome DevTools in Claude Desktop for client‑side debugging.
- **Join** the community on GitHub for troubleshooting tips and feature requests.
