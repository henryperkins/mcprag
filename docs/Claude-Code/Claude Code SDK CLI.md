Build custom AI agents with the Claude Code SDK

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#why-use-the-claude-code-sdk%3F)

Why use the Claude Code SDK?

The Claude Code SDK provides all the building blocks you need to build production-ready agents:

- **Optimized Claude integration**: Automatic prompt caching and performance optimizations
- **Rich tool ecosystem**: File operations, code execution, web search, and MCP extensibility
- **Advanced permissions**: Fine-grained control over agent capabilities
- **Production essentials**: Built-in error handling, session management, and monitoring

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#what-can-you-build-with-the-sdk%3F)

What can you build with the SDK?

Here are some example agent types you can create:

**Coding agents:**

- SRE agents that diagnose and fix production issues
- Security review bots that audit code for vulnerabilities
- Oncall engineering assistants that triage incidents
- Code review agents that enforce style and best practices

**Business agents:**

- Legal assistants that review contracts and compliance
- Finance advisors that analyze reports and forecasts
- Customer support agents that resolve technical issues
- Content creation assistants for marketing teams

The SDK is currently available in TypeScript and Python, with a command line interface (CLI) for quick prototyping.

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#quick-start)

Quick start

Get your first agent running in under 5 minutes:

1 Install the SDK

- Command line
- TypeScript
- Python

Install `@anthropic-ai/claude-code` from NPM:


```bash
npm install -g @anthropic-ai/claude-code
```

2 Set your API key

Get your API key from the [Anthropic Console](https://console.anthropic.com/) and set the `ANTHROPIC_API_KEY` environment variable:


```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

3 Create your first agent

Create one of these example agents:

- Command line
- TypeScript
- Python

```bash
# Create a simple legal assistant
claude -p "Review this contract clause for potential issues: 'The party agrees to unlimited liability...'" \
  --append-system-prompt "You are a legal assistant. Identify risks and suggest improvements."
```

4 Run the agent

- Command line
- TypeScript
- Python

Copy and paste the command above directly into your terminal.

Each example above creates a working agent that will:

- Analyze the prompt using Claude’s reasoning capabilities
- Plan a multi-step approach to solve the problem
- Execute actions using tools like file operations, bash commands, and web search
- Provide actionable recommendations based on the analysis

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#core-usage)

Core usage

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#overview)

Overview

The Claude Code SDK allows you to interface with Claude Code in non-interactive mode from your applications.

- Command line
- TypeScript
- Python

**Prerequisites**

- Node.js 18+
- `@anthropic-ai/claude-code` from NPM

**Basic usage**

The primary command-line interface to Claude Code is the `claude` command. Use the `--print` (or `-p`) flag to run in non-interactive mode and print the final result:

```bash
claude -p "Analyze system performance" \
  --append-system-prompt "You are a performance engineer" \
  --allowedTools "Bash,Read,WebSearch" \
  --permission-mode acceptEdits \
  --cwd /path/to/project
```

**Configuration**

The SDK leverages all the CLI options available in Claude Code. Here are the key ones for SDK usage:

|Flag|Description|Example|
|---|---|---|
|`--print`, `-p`|Run in non-interactive mode|`claude -p "query"`|
|`--output-format`|Specify output format (`text`, `json`, `stream-json`)|`claude -p --output-format json`|
|`--resume`, `-r`|Resume a conversation by session ID|`claude --resume abc123`|
|`--continue`, `-c`|Continue the most recent conversation|`claude --continue`|
|`--verbose`|Enable verbose logging|`claude --verbose`|
|`--append-system-prompt`|Append to system prompt (only with `--print`)|`claude --append-system-prompt "Custom instruction"`|
|`--allowedTools`|Space-separated list of allowed tools, or  <br>  <br>string of comma-separated list of allowed tools|`claude --allowedTools mcp__slack mcp__filesystem`  <br>  <br>`claude --allowedTools "Bash(npm install),mcp__filesystem"`|
|`--disallowedTools`|Space-separated list of denied tools, or  <br>  <br>string of comma-separated list of denied tools|`claude --disallowedTools mcp__splunk mcp__github`  <br>  <br>`claude --disallowedTools "Bash(git commit),mcp__github"`|
|`--mcp-config`|Load MCP servers from a JSON file|`claude --mcp-config servers.json`|
|`--permission-prompt-tool`|MCP tool for handling permission prompts (only with `--print`)|`claude --permission-prompt-tool mcp__auth__prompt`|

For a complete list of CLI options and features, see the [CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-reference) documentation.

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#authentication)

Authentication

#### [](https://docs.anthropic.com/en/docs/claude-code/sdk#anthropic-api-key)

Anthropic API key

For basic authentication, retrieve an Anthropic API key from the [Anthropic Console](https://console.anthropic.com/) and set the `ANTHROPIC_API_KEY` environment variable, as demonstrated in the [Quick start](https://docs.anthropic.com/en/docs/claude-code/sdk#quick-start).

#### [](https://docs.anthropic.com/en/docs/claude-code/sdk#third-party-api-credentials)

Third-party API credentials

The SDK also supports authentication via third-party API providers:

- **Amazon Bedrock**: Set `CLAUDE_CODE_USE_BEDROCK=1` environment variable and configure AWS credentials
- **Google Vertex AI**: Set `CLAUDE_CODE_USE_VERTEX=1` environment variable and configure Google Cloud credentials

For detailed configuration instructions for third-party providers, see the [Amazon Bedrock](https://docs.anthropic.com/en/docs/claude-code/amazon-bedrock) and [Google Vertex AI](https://docs.anthropic.com/en/docs/claude-code/google-vertex-ai) documentation.

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#multi-turn-conversations)

Multi-turn conversations

For multi-turn conversations, you can resume conversations or continue from the most recent session:

- Command line
- TypeScript
- Python

```bash
# Continue the most recent conversation
claude --continue "Now refactor this for better performance"

# Resume a specific conversation by session ID
claude --resume 550e8400-e29b-41d4-a716-446655440000 "Update the tests"

# Resume in non-interactive mode
claude --resume 550e8400-e29b-41d4-a716-446655440000 "Fix all linting issues" --no-interactive
```

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#custom-system-prompts)

Custom system prompts

System prompts define your agent’s role, expertise, and behavior. This is where you specify what kind of agent you’re building:

- Command line
- TypeScript
- Python

```bash
# SRE incident response agent
claude -p "API is down, investigate" \
  --append-system-prompt "You are an SRE expert. Diagnose issues systematically and provide actionable solutions."

# Legal document review agent  
claude -p "Review this contract" \
  --append-system-prompt "You are a corporate lawyer. Identify risks, suggest improvements, and ensure compliance."

# Append to default system prompt
claude -p "Refactor this function" \
  --append-system-prompt "Always include comprehensive error handling and unit tests."
```

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#advanced-usage)

Advanced Usage

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#custom-tools-via-mcp)

Custom tools via MCP

The Model Context Protocol (MCP) lets you give your agents custom tools and capabilities. This is crucial for building specialized agents that need domain-specific integrations.

**Example agent tool configurations:**


```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {"SLACK_TOKEN": "your-slack-token"}
    },
    "jira": {
      "command": "npx", 
      "args": ["-y", "@modelcontextprotocol/server-jira"],
      "env": {"JIRA_TOKEN": "your-jira-token"}
    },
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {"DB_CONNECTION_STRING": "your-db-url"}
    }
  }
}
```

**Usage examples:**

- Command line
- TypeScript
- Python

```bash
# SRE agent with monitoring tools
claude -p "Investigate the payment service outage" \
  --mcp-config sre-tools.json \
  --allowedTools "mcp__datadog,mcp__pagerduty,mcp__kubernetes" \
  --append-system-prompt "You are an SRE. Use monitoring data to diagnose issues."

# Customer support agent with CRM access
claude -p "Help resolve customer ticket #12345" \
  --mcp-config support-tools.json \
  --allowedTools "mcp__zendesk,mcp__stripe,mcp__user_db" \
  --append-system-prompt "You are a technical support specialist."
```

When using MCP tools, you must explicitly allow them using the `--allowedTools` flag. MCP tool names follow the pattern `mcp__<serverName>__<toolName>` where:

- `serverName` is the key from your MCP configuration file
- `toolName` is the specific tool provided by that server

This security measure ensures that MCP tools are only used when explicitly permitted.

If you specify just the server name (i.e., `mcp__<serverName>`), all tools from that server will be allowed.

Glob patterns (e.g., `mcp__go*`) are not supported.

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#custom-permission-prompt-tool)

Custom permission prompt tool

Optionally, use `--permission-prompt-tool` to pass in an MCP tool that we will use to check whether or not the user grants the model permissions to invoke a given tool. When the model invokes a tool the following happens:

1. We first check permission settings: all [settings.json files](https://docs.anthropic.com/en/docs/claude-code/settings), as well as `--allowedTools` and `--disallowedTools` passed into the SDK; if one of these allows or denies the tool call, we proceed with the tool call
2. Otherwise, we invoke the MCP tool you provided in `--permission-prompt-tool`

The `--permission-prompt-tool` MCP tool is passed the tool name and input, and must return a JSON-stringified payload with the result. The payload must be one of:

```ts
// tool call is allowed
{
  "behavior": "allow",
  "updatedInput": {...}, // updated input, or just return back the original input
}

// tool call is denied
{
  "behavior": "deny",
  "message": "..." // human-readable string explaining why the permission was denied
}
```

**Implementation examples:**

- Command line
- TypeScript
- Python

```bash
# Use with your MCP server configuration
claude -p "Analyze and fix the security issues" \
  --permission-prompt-tool mcp__security__approval_prompt \
  --mcp-config security-tools.json \
  --allowedTools "Read,Grep" \
  --disallowedTools "Bash(rm*),Write"

# With custom permission rules
claude -p "Refactor the codebase" \
  --permission-prompt-tool mcp__custom__permission_check \
  --mcp-config custom-config.json \
  --output-format json
```

Usage notes:

- Use `updatedInput` to tell the model that the permission prompt mutated its input; otherwise, set `updatedInput` to the original input, as in the example above. For example, if the tool shows a file edit diff to the user and lets them edit the diff manually, the permission prompt tool should return that updated edit.
- The payload must be JSON-stringified

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#output-formats)

Output formats

The SDK supports multiple output formats:

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#text-output-default)

Text output (default)

- Command line
- TypeScript
- Python

```bash
claude -p "Explain file src/components/Header.tsx"
# Output: This is a React component showing...
```

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#json-output)

JSON output

Returns structured data including metadata:

- Command line
- TypeScript
- Python

```bash
claude -p "How does the data layer work?" --output-format json
```

Response format:

```json
{
  "type": "result",
  "subtype": "success",
  "total_cost_usd": 0.003,
  "is_error": false,
  "duration_ms": 1234,
  "duration_api_ms": 800,
  "num_turns": 6,
  "result": "The response text here...",
  "session_id": "abc123"
}
```

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#streaming-json-output)

Streaming JSON output

Streams each message as it is received:

```bash
$ claude -p "Build an application" --output-format stream-json
```

Each conversation begins with an initial `init` system message, followed by a list of user and assistant messages, followed by a final `result` system message with stats. Each message is emitted as a separate JSON object.

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#message-schema)

Message schema

Messages returned from the JSON API are strictly typed according to the following schema:

```ts
type SDKMessage =
  // An assistant message
  | {
      type: "assistant";
      message: Message; // from Anthropic SDK
      session_id: string;
    }

  // A user message
  | {
      type: "user";
      message: MessageParam; // from Anthropic SDK
      session_id: string;
    }

  // Emitted as the last message
  | {
      type: "result";
      subtype: "success";
      duration_ms: float;
      duration_api_ms: float;
      is_error: boolean;
      num_turns: int;
      result: string;
      session_id: string;
      total_cost_usd: float;
    }

  // Emitted as the last message, when we've reached the maximum number of turns
  | {
      type: "result";
      subtype: "error_max_turns" | "error_during_execution";
      duration_ms: float;
      duration_api_ms: float;
      is_error: boolean;
      num_turns: int;
      session_id: string;
      total_cost_usd: float;
    }

  // Emitted as the first message at the start of a conversation
  | {
      type: "system";
      subtype: "init";
      apiKeySource: string;
      cwd: string;
      session_id: string;
      tools: string[];
      mcp_servers: {
        name: string;
        status: string;
      }[];
      model: string;
      permissionMode: "default" | "acceptEdits" | "bypassPermissions" | "plan";
    };
```

We will soon publish these types in a JSONSchema-compatible format. We use semantic versioning for the main Claude Code package to communicate breaking changes to this format.

`Message` and `MessageParam` types are available in Anthropic SDKs. For example, see the Anthropic [TypeScript](https://github.com/anthropics/anthropic-sdk-typescript) and [Python](https://github.com/anthropics/anthropic-sdk-python/) SDKs.

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#input-formats)

Input formats

The SDK supports multiple input formats:

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#text-input-default)

Text input (default)

- Command line
- TypeScript
- Python

```bash
# Direct argument
claude -p "Explain this code"

# From stdin
echo "Explain this code" | claude -p
```

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#streaming-json-input)

Streaming JSON input

A stream of messages provided via `stdin` where each message represents a user turn. This allows multiple turns of a conversation without re-launching the `claude` binary and allows providing guidance to the model while it is processing a request.

Each message is a JSON ‘User message’ object, following the same format as the output message schema. Messages are formatted using the [jsonl](https://jsonlines.org/) format where each line of input is a complete JSON object. Streaming JSON input requires `-p` and `--output-format stream-json`.

Currently this is limited to text-only user messages.

```bash
$ echo '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Explain this code"}]}}' | claude -p --output-format=stream-json --input-format=stream-json --verbose
```

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#agent-integration-examples)

Agent integration examples

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#sre-incident-response-bot)

SRE incident response bot

- Command line
- TypeScript
- Python

```bash
#!/bin/bash

# Automated incident response agent
investigate_incident() {
    local incident_description="$1"
    local severity="${2:-medium}"
    
    claude -p "Incident: $incident_description (Severity: $severity)" \
      --append-system-prompt "You are an SRE expert. Diagnose the issue, assess impact, and provide immediate action items." \
      --output-format json \
      --allowedTools "Bash,Read,WebSearch,mcp__datadog" \
      --mcp-config monitoring-tools.json
}

# Usage
investigate_incident "Payment API returning 500 errors" "high"
```

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#automated-security-review)

Automated security review

- Command line
- TypeScript
- Python

```bash
# Security audit agent for pull requests
audit_pr() {
    local pr_number="$1"
    
    gh pr diff "$pr_number" | claude -p \
      --append-system-prompt "You are a security engineer. Review this PR for vulnerabilities, insecure patterns, and compliance issues." \
      --output-format json \
      --allowedTools "Read,Grep,WebSearch"
}

# Usage and save to file
audit_pr 123 > security-report.json
```

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#multi-turn-legal-assistant)

Multi-turn legal assistant

- Command line
- TypeScript
- Python

```bash
# Legal document review with session persistence
session_id=$(claude -p "Start legal review session" --output-format json | jq -r '.session_id')

# Review contract in multiple steps
claude -p --resume "$session_id" "Review contract.pdf for liability clauses"
claude -p --resume "$session_id" "Check compliance with GDPR requirements" 
claude -p --resume "$session_id" "Generate executive summary of risks"
```

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#python-specific-best-practices)

Python-Specific Best Practices

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#key-patterns)

Key Patterns

```python
import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

# Always use context managers
async with ClaudeSDKClient() as client:
    await client.query("Analyze this code")
    async for msg in client.receive_response():
        # Process streaming messages
        pass

# Run multiple agents concurrently
async with ClaudeSDKClient() as reviewer, ClaudeSDKClient() as tester:
    await asyncio.gather(
        reviewer.query("Review main.py"),
        tester.query("Write tests for main.py")
    )

# Error handling
from claude_code_sdk import CLINotFoundError, ProcessError

try:
    async with ClaudeSDKClient() as client:
        # Your code here
        pass
except CLINotFoundError:
    print("Install CLI: npm install -g @anthropic-ai/claude-code")
except ProcessError as e:
    print(f"Process error: {e}")

# Collect full response with metadata
async def get_response(client, prompt):
    await client.query(prompt)
    text = []
    async for msg in client.receive_response():
        if hasattr(msg, 'content'):
            for block in msg.content:
                if hasattr(block, 'text'):
                    text.append(block.text)
        if type(msg).__name__ == "ResultMessage":
            return {'text': ''.join(text), 'cost': msg.total_cost_usd}
```

### [](https://docs.anthropic.com/en/docs/claude-code/sdk#ipython%2Fjupyter-tips)

IPython/Jupyter Tips

```python
# In Jupyter, use await directly in cells
client = ClaudeSDKClient()
await client.connect()
await client.query("Analyze data.csv")
async for msg in client.receive_response():
    print(msg)
await client.disconnect()

# Create reusable helper functions
async def stream_print(client, prompt):
    await client.query(prompt)
    async for msg in client.receive_response():
        if hasattr(msg, 'content'):
            for block in msg.content:
                if hasattr(block, 'text'):
                    print(block.text, end='', flush=True)
```

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#best-practices)

Best practices

- **Use JSON output format** for programmatic parsing of responses:
    
    ```bash
    # Parse JSON response with jq
    result=$(claude -p "Generate code" --output-format json)
    code=$(echo "$result" | jq -r '.result')
    cost=$(echo "$result" | jq -r '.cost_usd')
    ```
    
- **Handle errors gracefully** - check exit codes and stderr:
    
    ```bash
    if ! claude -p "$prompt" 2>error.log; then
        echo "Error occurred:" >&2
        cat error.log >&2
        exit 1
    fi
    ```
    
- **Use session management** for maintaining context in multi-turn conversations
    
- **Consider timeouts** for long-running operations:
    
    ```bash
    timeout 300 claude -p "$complex_prompt" || echo "Timed out after 5 minutes"
    ```
    
- **Respect rate limits** when making multiple requests by adding delays between calls
    

## [](https://docs.anthropic.com/en/docs/claude-code/sdk#related-resources)

Related resources

- [CLI usage and controls](https://docs.anthropic.com/en/docs/claude-code/cli-reference) - Complete CLI documentation
- [GitHub Actions integration](https://docs.anthropic.com/en/docs/claude-code/github-actions) - Automate your GitHub workflow with Claude
- [Common workflows](https://docs.anthropic.com/en/docs/claude-code/common-workflows) - Step-by-step guides for common use cases