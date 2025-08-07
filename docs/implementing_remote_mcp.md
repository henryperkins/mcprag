Implementing secure remote access for this specific MCP server (FastMCP + Azure code search stack) involves: enabling HTTP/SSE transport, adding lightweight auth, packaging (Docker/systemd), and adding a local proxy path for legacy clients. Below is a tailored, end‑to‑end solution.

Checklist:
1. Add remote transport support (SSE / streamable-http) via CLI/env.
2. Add bearer token (MCP_REMOTE_TOKEN) enforcement.
3. Harden config + logging (stderr only) for remote mode.
4. Provide Docker + systemd run patterns.
5. Add SSH tunnel option (no code change).
6. Provide Cloudflare / Worker proxy pattern (optional).
7. Provide client connection patterns (Claude, mcp-remote).
8. Provide index/admin separation (query vs admin key).
9. Offer minimal health + readiness endpoint (optional enhancement).

## 1. Config additions

Add optional remote auth token + host/port + allowed origins.

````python
# ...existing code...
    MCP_REMOTE_TOKEN: Optional[str] = os.getenv("MCP_REMOTE_TOKEN")
    MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8001"))
    MCP_ALLOWED_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("MCP_ALLOWED_ORIGINS", "*").split(",")
        if o.strip()
    ]
# ...existing code...
    @classmethod
    def validate(cls) -> Dict[str, str]:
        errors = {}
        # ...existing validation...
        if (os.getenv("MCP_REMOTE_REQUIRED", "").lower() in {"1","true"}
            and not cls.MCP_REMOTE_TOKEN):
            errors["remote_auth"] = "MCP_REMOTE_TOKEN required when MCP_REMOTE_REQUIRED=1"
        return errors
````

## 2. Server run enhancements

Add transport selection + bearer token guard for non-stdio transport. (Assumes FastMCP.run accepts host/port for HTTP-like transports—if not, you can wrap with an ASGI layer; see alt wrapper below.)

````python
# ...imports...
import argparse
import logging
from mcprag.config import Config
# ...existing code...

    def run(self, transport: Literal["stdio","sse","streamable-http"]="stdio"):
        """Run the MCP server."""
        # Transport validation
        if transport not in {"stdio","sse","streamable-http"}:
            raise ValueError(f"Unsupported transport: {transport}")

        logger.info(f"Starting MCP server transport={transport}")

        # Start async components before accepting remote traffic
        if transport == "stdio":
            # synchronous warm-up
            try:
                import asyncio
                asyncio.run(self.ensure_async_components_started())
            except Exception:
                logger.exception("Failed to start async components (stdio)")
        else:
            # For remote transports we lazily start in background once loop alive
            pass

        # Inject auth middleware if remote & token present
        if transport != "stdio" and Config.MCP_REMOTE_TOKEN:
            try:
                # FastMCP currently doesn't expose middleware injection formally.
                # Provide defensive patching if attribute exists.
                if hasattr(self.mcp, "set_request_auth_callback"):
                    def _auth_checker(headers: dict[str,str]) -> bool:
                        auth = headers.get("authorization","")
                        return auth == f"Bearer {Config.MCP_REMOTE_TOKEN}"
                    self.mcp.set_request_auth_callback(_auth_checker)  # type: ignore
                    logger.info("Remote bearer token auth enabled")
                else:
                    logger.warning("Auth callback not supported by FastMCP version; deploy external reverse-proxy auth instead.")
            except Exception:
                logger.exception("Failed to configure bearer auth")

        self.mcp.run(
            transport=transport,
            host=Config.MCP_HOST if transport != "stdio" else None,
            port=Config.MCP_PORT if transport != "stdio" else None,
        )

def main():
    parser = argparse.ArgumentParser(description="Azure Code Search MCP Server")
    parser.add_argument("--transport", default=os.getenv("MCP_TRANSPORT","stdio"),
                        choices=["stdio","sse","streamable-http"])
    parser.add_argument("--host", default=os.getenv("MCP_HOST","0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT","8001")))
    args = parser.parse_args()

    # Override dynamic host/port if provided
    Config.MCP_HOST = args.host
    Config.MCP_PORT = args.port

    server = create_server()
    server.run(transport=args.transport)
````

If FastMCP doesn’t actually support host/port params, use an ASGI bridge:

````python
from mcprag.server import create_server
from fastapi import FastAPI, Request, HTTPException
import os

server = create_server()
app = FastAPI()

TOKEN = os.getenv("MCP_REMOTE_TOKEN")

@app.on_event("startup")
async def startup():
    await server.ensure_async_components_started()

@app.post("/mcp")
async def mcp_endpoint(req: Request):
    if TOKEN:
        auth = req.headers.get("authorization","")
        if auth != f"Bearer {TOKEN}":
            raise HTTPException(401, "Unauthorized")
    payload = await req.json()
    # Forward into FastMCP dispatcher (pseudo; adapt to actual API)
    result = await server.mcp.dispatch(payload)
    return result

@app.get("/healthz")
async def health():
    return {"status":"ok","index": server.rag_config.get("index_name")}
````

Run with:
```bash
uvicorn mcprag.remote_app:app --host 0.0.0.0 --port 8001
```

## 3. Environment examples

Local (stdio):
```bash
export ACS_ENDPOINT="https://<search>.search.windows.net"
export ACS_ADMIN_KEY="***"
python -m mcprag.server --transport stdio
```

Remote (SSE) with token:
```bash
export ACS_ENDPOINT="https://<search>.search.windows.net"
export ACS_ADMIN_KEY="***"
export MCP_TRANSPORT="sse"
export MCP_REMOTE_TOKEN="$(openssl rand -hex 24)"
python -m mcprag.server --transport sse --host 0.0.0.0 --port 8001
```

## 4. Docker run pattern

Minimal override (Dockerfile already present—append entrypoint logic if needed):

````dockerfile
ENV MCP_TRANSPORT=sse MCP_PORT=8001 MCP_HOST=0.0.0.0
EXPOSE 8001
CMD ["python","-m","mcprag.server","--transport","sse","--host","0.0.0.0","--port","8001"]
````

Build & run:
```bash
docker build -t mcprag-remote .
docker run -d --name mcprag \
  -e ACS_ENDPOINT="$ACS_ENDPOINT" \
  -e ACS_ADMIN_KEY="$ACS_ADMIN_KEY" \
  -e MCP_REMOTE_TOKEN="$MCP_REMOTE_TOKEN" \
  -p 8001:8001 mcprag-remote
```

## 5. systemd unit

````ini
# /etc/systemd/system/mcprag.service
[Unit]
Description=Azure Code Search MCP (remote)
After=network.target

[Service]
User=mcprag
Group=mcprag
WorkingDirectory=/opt/mcprag
Environment=ACS_ENDPOINT=https://<search>.search.windows.net
Environment=ACS_ADMIN_KEY=<redacted>
Environment=MCP_TRANSPORT=sse
Environment=MCP_REMOTE_TOKEN=<redacted>
ExecStart=/opt/mcprag/.venv/bin/python -m mcprag.server --transport sse --host 127.0.0.1 --port 8001
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
````

Then reverse-proxy (nginx/Caddy) with TLS + rate limiting; proxy Authorization header through.

## 6. SSH tunnel alternative (no HTTP exposure)

On client:
```bash
ssh -N -L 9001:127.0.0.1:8001 user@remote-host
```
Then connect to http://localhost:9001/sse (if SSE transport) via mcp-remote or custom client.

## 7. Client integration patterns

Claude (local spawn over SSH, preserves stdio):
```json
{
  "mcpServers": {
    "azure-code-search": {
      "command": "ssh",
      "args": ["user@remote-host", "source /opt/mcprag/.venv/bin/activate && python -m mcprag.server --transport stdio"],
      "env": {}
    }
  }
}
```

Claude via remote proxy (using mcp-remote):
```bash
npx mcp-remote --server-url https://code-search.example.com/sse \
  --bearer $MCP_REMOTE_TOKEN \
  --name azure-code-search
```
This exposes a local stdio-compatible shim for Claude; configure it like a normal local command:
```json
{
  "mcpServers": {
    "azure-code-search": {
      "command": "npx",
      "args": ["mcp-remote","--server-url","https://code-search.example.com/sse","--bearer","$MCP_REMOTE_TOKEN","--name","azure-code-search"]
    }
  }
}
```

## 8. Security recommendations

- Use query key (Azure Search “Query Key”) for remote read-only deployments; keep ADMIN_KEY only on indexer host.
- Rotate MCP_REMOTE_TOKEN regularly; store in a secrets manager.
- Enable WAF / rate limits (10–20 RPS baseline).
- Log tool invocations to a structured log (JSON to stderr) for audit.
- Strip accidental prints in stdio mode (already using logging).

## 9. Health / readiness

Add `/healthz` (shown in remote_app) and optionally an internal `/status` that calls `status.py` logic; keep unauthenticated health minimal (no secrets).

## 10. Indexing separation

Run indexing on a private worker:
```bash
python smart_indexer.py --repo-path /data/repos/your-repo --repo-name your-repo
python index/recreate_index_fixed.py  # when schema changes
```
Grant only query key to public-facing remote server if mutation not needed.

## 11. Observability quick wins

- Set `MCP_LOG_LEVEL=INFO` (DEBUG only during diagnosis).
- Ship stderr to journald (systemd) or sidecar log collector.
- Add latency metrics by wrapping tool functions with timing decorator (log as JSON: {tool, ms}).

Example timing wrapper:

````python
import time, logging, functools, json
log = logging.getLogger("metrics")

def timed(tool_name: str):
    def deco(fn):
        @functools.wraps(fn)
        async def inner(*a, **kw):
            t0 = time.perf_counter()
            try:
                return await fn(*a, **kw)
            finally:
                log.info(json.dumps({"event":"tool_time","tool":tool_name,"ms":round((time.perf_counter()-t0)*1000,2)}))
        return inner
    return deco
````

Wrap a tool registration site:
```python
@timed("search_code")
async def search_code(...):
    ...
```

## 12. Cloudflare Worker proxy (optional)

If you keep Python server private, create a Worker that:
- Validates request (Bearer)
- Streams SSE to client
- Forwards to origin: `fetch("https://internal-host:8001/sse", {headers})`

This offloads TLS + global edge caching of static metadata.

## 13. Minimal run recap

Local dev (stdio):
```bash
python -m mcprag.server --transport stdio
```

Remote (SSE, token):
```bash
export MCP_TRANSPORT=sse
export MCP_REMOTE_TOKEN=$(openssl rand -hex 24)
python -m mcprag.server --transport sse --host 0.0.0.0 --port 8001
```

## 14. Follow-up enhancements (optional)

- Add tool-level scopes (MCP_REMOTE_SCOPES env specifying allowed tool regex).
- Implement per-user quota (wrap dispatch counting).
- Add persistent caching layer (Redis) keyed by query embedding hash.

Let me know if you’d like the ASGI wrapper finalized or an nginx config snippet. Done.
