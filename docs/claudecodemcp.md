# Model Context Protocol (MCP) with Claude Code

## Overview

Model Context Protocol (MCP) is an open protocol that enables LLMs to access external tools and data sources. For more details about MCP, see the [MCP documentation](https://modelcontextprotocol.io/introduction).

**Important Security Notice:** Use third-party MCP servers at your own risk. Make sure you trust the MCP servers, and be especially careful when using MCP servers that talk to the internet, as these can expose you to prompt injection risk.

---

## Configuring MCP Servers

### Adding Servers

Claude Code supports three server types: **stdio**, **SSE**, and **HTTP**.

#### 1. Add an MCP stdio Server
```bash
# Basic syntax
claude mcp add <name> <command> [args...]

# Example: Adding a local server
claude mcp add my-server -e API_KEY=123 -- /path/to/server arg1 arg2
# This creates: command="/path/to/server", args=["arg1", "arg2"]
```

#### 2. Add an MCP SSE Server
```bash
# Basic syntax
claude mcp add --transport sse <name> <url>

# Example: Adding an SSE server
claude mcp add --transport sse sse-server https://example.com/sse-endpoint

# Example: Adding an SSE server with custom headers
claude mcp add --transport sse api-server https://api.example.com/mcp --header "X-API-Key: your-key"
```

#### 3. Add an MCP HTTP Server
```bash
# Basic syntax
claude mcp add --transport http <name> <url>

# Example: Adding a streamable HTTP server
claude mcp add --transport http http-server https://example.com/mcp

# Example: Adding an HTTP server with authentication header
claude mcp add --transport http secure-server https://api.example.com/mcp --header "Authorization: Bearer your-token"
```

#### 4. Manage your MCP servers
```bash
# List all configured servers
claude mcp list

# Get details for a specific server
claude mcp get my-server

# Remove a server
claude mcp remove my-server
```

### Configuration Tips
- Use the `-s` or `--scope` flag to specify where the configuration is stored:
  - `local` (default): Available only to you in the current project (was called `project` in older versions)
  - `project`: Shared with everyone in the project via `.mcp.json` file
  - `user`: Available to you across all projects (was called `global` in older versions)
- Set environment variables with `-e` or `--env` flags (e.g., `-e KEY=value`)
- Configure MCP server startup timeout using the MCP_TIMEOUT environment variable (e.g., `MCP_TIMEOUT=10000 claude` sets a 10-second timeout)
- Check MCP server status any time using the `/mcp` command within Claude Code
- MCP follows a client-server architecture where Claude Code (the client) can connect to multiple specialized servers
- Claude Code supports SSE (Server-Sent Events) and streamable HTTP servers for real-time communication
- Use `/mcp` to authenticate with remote servers that require OAuth 2.0 authentication

### Windows-Specific Configuration
**Windows Users**: On native Windows (not WSL), local MCP servers that use `npx` require the `cmd /c` wrapper to ensure proper execution.
```bash
# This creates command="cmd" which Windows can execute
claude mcp add my-server -- cmd /c npx -y @some/package
```
Without the `cmd /c` wrapper, you'll encounter "Connection closed" errors because Windows cannot directly execute `npx`.

---

## Understanding MCP Server Scopes

MCP servers can be configured at three different scope levels, each serving distinct purposes for managing server accessibility and sharing.

### Scope Hierarchy and Precedence
MCP server configurations follow a clear precedence hierarchy. When servers with the same name exist at multiple scopes, the system resolves conflicts by prioritizing local-scoped servers first, followed by project-scoped servers, and finally user-scoped servers. This design ensures that personal configurations can override shared ones when needed.

### Local Scope
Local-scoped servers represent the default configuration level and are stored in your project-specific user settings. These servers remain private to you and are only accessible when working within the current project directory. This scope is ideal for personal development servers, experimental configurations, or servers containing sensitive credentials that shouldn't be shared.

```bash
# Add a local-scoped server (default)
claude mcp add my-private-server /path/to/server

# Explicitly specify local scope
claude mcp add my-private-server -s local /path/to/server
```

### Project Scope
Project-scoped servers enable team collaboration by storing configurations in a `.mcp.json` file at your project's root directory. This file is designed to be checked into version control, ensuring all team members have access to the same MCP tools and services. When you add a project-scoped server, Claude Code automatically creates or updates this file with the appropriate configuration structure.

```bash
# Add a project-scoped server
claude mcp add shared-server -s project /path/to/server
```

The resulting `.mcp.json` file follows a standardized format:
```json
{
  "mcpServers": {
    "shared-server": {
      "command": "/path/to/server",
      "args": [],
      "env": {}
    }
  }
}
```

For security reasons, Claude Code prompts for approval before using project-scoped servers from `.mcp.json` files. If you need to reset these approval choices, use the `claude mcp reset-project-choices` command.

### User Scope
User-scoped servers provide cross-project accessibility, making them available across all projects on your machine while remaining private to your user account. This scope works well for personal utility servers, development tools, or services you frequently use across different projects.

```bash
# Add a user server
claude mcp add my-user-server -s user /path/to/server
```

### Choosing the Right Scope
Select your scope based on:
- **Local scope**: Personal servers, experimental configurations, or sensitive credentials specific to one project
- **Project scope**: Team-shared servers, project-specific tools, or services required for collaboration
- **User scope**: Personal utilities needed across multiple projects, development tools, or frequently-used services

### Environment Variable Expansion in `.mcp.json`
Claude Code supports environment variable expansion in `.mcp.json` files, allowing teams to share configurations while maintaining flexibility for machine-specific paths and sensitive values like API keys.

**Supported syntax:**
- `${VAR}` - Expands to the value of environment variable `VAR`
- `${VAR:-default}` - Expands to `VAR` if set, otherwise uses `default`

**Expansion locations:** Environment variables can be expanded in:
- `command` - The server executable path
- `args` - Command-line arguments
- `env` - Environment variables passed to the server
- `url` - For SSE/HTTP server types
- `headers` - For SSE/HTTP server authentication

**Example with variable expansion:**
```json
{
  "mcpServers": {
    "api-server": {
      "type": "sse",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

If a required environment variable is not set and has no default value, Claude Code will fail to parse the config.

---

## Authenticate with Remote MCP Servers

Many remote MCP servers require authentication. Claude Code supports OAuth 2.0 authentication flow for secure connection to these servers.

### Authentication Process

1. **Add a remote server requiring authentication**
```bash
# Add an SSE or HTTP server that requires OAuth
claude mcp add --transport sse github-server https://api.github.com/mcp
```

2. **Authenticate using the /mcp command**
Within Claude Code, use the `/mcp` command to manage authentication:
```
> /mcp
```
This opens an interactive menu where you can:
- View connection status for all servers
- Authenticate with servers requiring OAuth
- Clear existing authentication
- View server capabilities

3. **Complete the OAuth flow**
When you select "Authenticate" for a server:
4. Your browser opens automatically to the OAuth provider
5. Complete the authentication in your browser
6. Claude Code receives and securely stores the access token
7. The server connection becomes active

### Authentication Tips
- Authentication tokens are stored securely and refreshed automatically
- Use "Clear authentication" in the `/mcp` menu to revoke access
- If your browser doesn't open automatically, copy the provided URL
- OAuth authentication works with both SSE and HTTP transports

---

## Connect to a Postgres MCP Server

Suppose you want to give Claude read-only access to a PostgreSQL database for querying and schema inspection.

### Setup Process

1. **Add the Postgres MCP server**
```bash
claude mcp add postgres-server /path/to/postgres-mcp-server --connection-string "postgresql://user:pass@localhost:5432/mydb"
```

2. **Query your database with Claude**
```
> describe the schema of our users table
```

```
> what are the most recent orders in the system?
```

```
> show me the relationship between customers and invoices
```

### Database Connection Tips
- The Postgres MCP server provides read-only access for safety
- Claude can help you explore database structure and run analytical queries
- You can use this to quickly understand database schemas in unfamiliar projects
- Make sure your connection string uses appropriate credentials with minimum required permissions

---

## Add MCP Servers from JSON Configuration

Suppose you have a JSON configuration for a single MCP server that you want to add to Claude Code.

### JSON Configuration Process

1. **Add an MCP server from JSON**
```bash
# Basic syntax
claude mcp add-json <name> '<json>'

# Example: Adding a stdio server with JSON configuration
claude mcp add-json weather-api '{"type":"stdio","command":"/path/to/weather-cli","args":["--api-key","abc123"],"env":{"CACHE_DIR":"/tmp"}}'
```

2. **Verify the server was added**
```bash
claude mcp get weather-api
```

### JSON Configuration Tips
- Make sure the JSON is properly escaped in your shell
- The JSON must conform to the MCP server configuration schema
- You can use `-s global` to add the server to your global configuration instead of the project-specific one

---

## Import MCP Servers from Claude Desktop

Suppose you have already configured MCP servers in Claude Desktop and want to use the same servers in Claude Code without manually reconfiguring them.

### Import Process

1. **Import servers from Claude Desktop**
```bash
# Basic syntax 
claude mcp add-from-claude-desktop 
```

2. **Select which servers to import**
After running the command, you'll see an interactive dialog that allows you to select which servers you want to import.

3. **Verify the servers were imported**
```bash
claude mcp list 
```

### Import Tips
- This feature only works on macOS and Windows Subsystem for Linux (WSL)
- It reads the Claude Desktop configuration file from its standard location on those platforms
- Use the `-s global` flag to add servers to your global configuration
- Imported servers will have the same names as in Claude Desktop
- If servers with the same names already exist, they will get a numerical suffix (e.g., `server_1`)

---

## Use Claude Code as an MCP Server

Suppose you want to use Claude Code itself as an MCP server that other applications can connect to, providing them with Claude's tools and capabilities.

### Setup Process

1. **Start Claude as an MCP server**
```bash
# Basic syntax
claude mcp serve
```

2. **Connect from another application**
You can connect to Claude Code MCP server from any MCP client, such as Claude Desktop. If you're using Claude Desktop, you can add the Claude Code MCP server using this configuration:
```json
{
  "command": "claude",
  "args": ["mcp", "serve"],
  "env": {}
}
```

### Usage Tips
- The server provides access to Claude's tools like View, Edit, LS, etc.
- In Claude Desktop, try asking Claude to read files in a directory, make edits, and more.
- Note that this MCP server is simply exposing Claude Code's tools to your MCP client, so your own client is responsible for implementing user confirmation for individual tool calls.

---

## Use MCP Resources

MCP servers can expose resources that you can reference using @ mentions, similar to how you reference files.

### Reference MCP Resources

1. **List available resources**
Type `@` in your prompt to see available resources from all connected MCP servers. Resources appear alongside files in the autocomplete menu.

2. **Reference a specific resource**
Use the format `@server:protocol://resource/path` to reference a resource:
```
> Can you analyze @github:issue://123 and suggest a fix?
```

```
> Please review the API documentation at @docs:file://api/authentication
```

3. **Multiple resource references**
You can reference multiple resources in a single prompt:
```
> Compare @postgres:schema://users with @docs:file://database/user-model
```

### Resource Usage Tips
- Resources are automatically fetched and included as attachments when referenced
- Resource paths are fuzzy-searchable in the @ mention autocomplete
- Claude Code automatically provides tools to list and read MCP resources when servers support them
- Resources can contain any type of content that the MCP server provides (text, JSON, structured data, etc.)

---

## Use MCP Prompts as Slash Commands

MCP servers can expose prompts that become available as slash commands in Claude Code.

### Execute MCP Prompts

1. **Discover available prompts**
Type `/` to see all available commands, including those from MCP servers. MCP prompts appear with the format `/mcp__servername__promptname`.

2. **Execute a prompt without arguments**
```
> /mcp__github__list_prs
```

3. **Execute a prompt with arguments**
Many prompts accept arguments. Pass them space-separated after the command:
```
> /mcp__github__pr_review 456
```

```
> /mcp__jira__create_issue "Bug in login flow" high
```

### Prompt Usage Tips
- MCP prompts are dynamically discovered from connected servers
- Arguments are parsed based on the prompt's defined parameters
- Prompt results are injected directly into the conversation
- Server and prompt names are normalized (spaces become underscores)

---

This comprehensive guide includes all information from the original note with improved organization, consistent formatting, and clear section headings for better reference. The content maintains all technical details, examples, tips, and security considerations from the source material.