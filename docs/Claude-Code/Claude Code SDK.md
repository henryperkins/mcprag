Build custom AI agents with the Claude Code SDK

## Why use the Claude Code SDK? ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#why-use-the-claude-code-sdk%3F))

The Claude Code SDK provides all the building blocks you need to build production-ready agents:

- Optimized Claude integration: Automatic prompt caching and performance optimizations
- Rich tool ecosystem: File operations, code execution, web search, and MCP extensibility
- Advanced permissions: Fine-grained control over agent capabilities
- Production essentials: Built-in error handling, session management, and monitoring

## What can you build with the SDK? ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#what-can-you-build-with-the-sdk%3F))

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

## Quick start ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#quick-start))

Get your first agent running in under 5 minutes:

1) Install the SDK
- Command line
- TypeScript
- Python

Install `@anthropic-ai/claude-code` from NPM:

Copy

```bash
npm install -g @anthropic-ai/claude-code
```

2) Set your API key

Get your API key from the [Anthropic Console](https://console.anthropic.com/) and set the `ANTHROPIC_API_KEY` environment variable:

Copy

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

3) Create your first agent

Create one of these example agents:

- Command line
- TypeScript
- Python

Copy

```ts
// legal-agent.ts
import { query } from "@anthropic-ai/claude-code";

// Create a simple legal assistant
for await (const message of query({
  prompt: "Review this contract clause for potential issues: 'The party agrees to unlimited liability...'",
  options: {
    systemPrompt: "You are a legal assistant. Identify risks and suggest improvements.",
    maxTurns: 2
  }
})) {
  if (message.type === "result") {
    console.log(message.result);
  }
}
```

4) Run the agent

- Command line
- TypeScript
- Python

1. Set up project:

Copy

```bash
npm init -y
npm install @anthropic-ai/claude-code tsx
```

2. Add `"type": "module"` to your package.json

3. Save the code above as `legal-agent.ts`, then run:

Copy

```bash
npx tsx legal-agent.ts
```

Each example above creates a working agent that will:
- Analyze the prompt using Claude’s reasoning capabilities
- Plan a multi-step approach to solve the problem
- Execute actions using tools like file operations, bash commands, and web search
- Provide actionable recommendations based on the analysis

## Core usage ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#core-usage))

### Overview ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#overview))

The Claude Code SDK allows you to interface with Claude Code in non-interactive mode from your applications.

- Command line
- TypeScript
- Python

**Prerequisites**
- Node.js 18+
- `@anthropic-ai/claude-code` from NPM

To view the TypeScript SDK source code, visit the [`@anthropic-ai/claude-code` page on NPM](https://www.npmjs.com/package/@anthropic-ai/claude-code?activeTab=code).

**Basic usage**

The primary interface via the TypeScript SDK is the `query` function, which returns an async iterator that streams messages as they arrive:

Copy

```ts
import { query } from "@anthropic-ai/claude-code";

for await (const message of query({
  prompt: "Analyze system performance",
  abortController: new AbortController(),
  options: {
    maxTurns: 5,
    systemPrompt: "You are a performance engineer",
    allowedTools: ["Bash", "Read", "WebSearch"]
  }
})) {
  if (message.type === "result") {
    console.log(message.result);
  }
}
```

**Configuration**

The TypeScript SDK accepts all arguments supported by the [command line](https://docs.anthropic.com/en/docs/claude-code/cli-reference), as well as the following additional options:

|Argument|Description|Default|
|---|---|---|
|`abortController`|Abort controller|`new AbortController()`|
|`cwd`|Current working directory|`process.cwd()`|
|`executable`|Which JavaScript runtime to use|`node` when running with Node.js, `bun` when running with Bun|
|`executableArgs`|Arguments to pass to the executable|`[]`|
|`pathToClaudeCodeExecutable`|Path to the Claude Code executable|Executable that ships with `@anthropic-ai/claude-code`|

### Authentication ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#authentication))

#### Anthropic API key ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#anthropic-api-key))

For basic authentication, retrieve an Anthropic API key from the [Anthropic Console](https://console.anthropic.com/) and set the `ANTHROPIC_API_KEY` environment variable, as demonstrated in the [Quick start](https://docs.anthropic.com/en/docs/claude-code/sdk#quick-start).

#### Third-party API credentials ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#third-party-api-credentials))

The SDK also supports authentication via third-party API providers:
- Amazon Bedrock: Set `CLAUDE_CODE_USE_BEDROCK=1` environment variable and configure AWS credentials
- Google Vertex AI: Set `CLAUDE_CODE_USE_VERTEX=1` environment variable and configure Google Cloud credentials

For detailed configuration instructions for third-party providers, see the [Amazon Bedrock](https://docs.anthropic.com/en/docs/claude-code/amazon-bedrock) and [Google Vertex AI](https://docs.anthropic.com/en/docs/claude-code/google-vertex-ai) documentation.

### Multi-turn conversations ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#multi-turn-conversations))

For multi-turn conversations, you can resume conversations or continue from the most recent session:

- Command line
- TypeScript
- Python

Copy

```ts
import { query } from "@anthropic-ai/claude-code";

// Continue most recent conversation
for await (const message of query({
  prompt: "Now refactor this for better performance",
  options: { continueSession: true }
})) {
  if (message.type === "result") console.log(message.result);
}

// Resume specific session
for await (const message of query({
  prompt: "Update the tests",
  options: { 
    resumeSessionId: "550e8400-e29b-41d4-a716-446655440000",
    maxTurns: 3
  }
})) {
  if (message.type === "result") console.log(message.result);
}
```

### Custom system prompts ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#custom-system-prompts))

System prompts define your agent’s role, expertise, and behavior. This is where you specify what kind of agent you’re building:

- Command line
- TypeScript
- Python

Copy

```ts
import { query } from "@anthropic-ai/claude-code";

// SRE incident response agent
for await (const message of query({
  prompt: "API is down, investigate",
  options: {
    systemPrompt: "You are an SRE expert. Diagnose issues systematically and provide actionable solutions.",
    maxTurns: 3
  }
})) {
  if (message.type === "result") console.log(message.result);
}

// Append to default system prompt
for await (const message of query({
  prompt: "Refactor this function",
  options: {
    appendSystemPrompt: "Always include comprehensive error handling and unit tests.",
    maxTurns: 2
  }
})) {
  if (message.type === "result") console.log(message.result);
}
```

## Advanced Usage ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#advanced-usage))

### Custom tools via MCP ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#custom-tools-via-mcp))

The Model Context Protocol (MCP) lets you give your agents custom tools and capabilities. This is crucial for building specialized agents that need domain-specific integrations.

**Example agent tool configurations:**

Copy

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

Copy

```ts
import { query } from "@anthropic-ai/claude-code";

// SRE agent with monitoring tools
for await (const message of query({
  prompt: "Investigate the payment service outage",
  options: {
    mcpConfig: "sre-tools.json",
    allowedTools: ["mcp__datadog", "mcp__pagerduty", "mcp__kubernetes"],
    systemPrompt: "You are an SRE. Use monitoring data to diagnose issues.",
    maxTurns: 4
  }
})) {
  if (message.type === "result") console.log(message.result);
}
```

When using MCP tools, you must explicitly allow them using the `--allowedTools` flag. MCP tool names follow the pattern `mcp__<serverName>__<toolName>` where:
- `serverName` is the key from your MCP configuration file
- `toolName` is the specific tool provided by that server

This security measure ensures that MCP tools are only used when explicitly permitted.

If you specify just the server name (i.e., `mcp__<serverName>`), all tools from that server will be allowed.

Glob patterns (e.g., `mcp__go*`) are not supported.

### Custom permission prompt tool ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#custom-permission-prompt-tool))

Optionally, use `--permission-prompt-tool` to pass in an MCP tool that we will use to check whether or not the user grants the model permissions to invoke a given tool. When the model invokes a tool the following happens:

1. We first check permission settings: all [settings.json files](https://docs.anthropic.com/en/docs/claude-code/settings), as well as `--allowedTools` and `--disallowedTools` passed into the SDK; if one of these allows or denies the tool call, we proceed with the tool call
2. Otherwise, we invoke the MCP tool you provided in `--permission-prompt-tool`

The `--permission-prompt-tool` MCP tool is passed the tool name and input, and must return a JSON-stringified payload with the result. The payload must be one of:

Copy

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

Copy

```ts
const server = new McpServer({
  name: "Test permission prompt MCP Server",
  version: "0.0.1",
});

server.tool(
  "approval_prompt",
  'Simulate a permission check - approve if the input contains "allow", otherwise deny',
  {
    tool_name: z.string().describe("The name of the tool requesting permission"),
    input: z.object({}).passthrough().describe("The input for the tool"),
    tool_use_id: z.string().optional().describe("The unique tool use request ID"),
  },
  async ({ tool_name, input }) => {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            JSON.stringify(input).includes("allow")
              ? {
                  behavior: "allow",
                  updatedInput: input,
                }
              : {
                  behavior: "deny",
                  message: "Permission denied by test approval_prompt tool",
                }
          ),
        },
      ],
    };
  }
);

// Use in SDK
import { query } from "@anthropic-ai/claude-code";

for await (const message of query({
  prompt: "Analyze the codebase",
  options: {
    permissionPromptTool: "mcp__test-server__approval_prompt",
    mcpConfig: "my-config.json",
    allowedTools: ["Read", "Grep"]
  }
})) {
  if (message.type === "result") console.log(message.result);
}
```

Usage notes:
- Use `updatedInput` to tell the model that the permission prompt mutated its input; otherwise, set `updatedInput` to the original input, as in the example above. For example, if the tool shows a file edit diff to the user and lets them edit the diff manually, the permission prompt tool should return that updated edit.
- The payload must be JSON-stringified

## Output formats ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#output-formats))

The SDK supports multiple output formats:

### Text output (default) ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#text-output-default))

- Command line
- TypeScript
- Python

Copy

```ts
// Default text output
for await (const message of query({
  prompt: "Explain file src/components/Header.tsx"
})) {
  if (message.type === "result") {
    console.log(message.result);
    // Output: This is a React component showing...
  }
}
```

### JSON output ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#json-output))

Returns structured data including metadata:

- Command line
- TypeScript
- Python

Copy

```ts
// Collect all messages for JSON-like access
const messages = [];
for await (const message of query({
  prompt: "How does the data layer work?"
})) {
  messages.push(message);
}

// Access result message with metadata
const result = messages.find(m => m.type === "result");
console.log({
  result: result.result,
  cost: result.total_cost_usd,
  duration: result.duration_ms
});
```

Response format:

Copy

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

### Streaming JSON output ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#streaming-json-output))

Streams each message as it is received:

Copy

```bash
$ claude -p "Build an application" --output-format stream-json
```

Each conversation begins with an initial `init` system message, followed by a list of user and assistant messages, followed by a final `result` system message with stats. Each message is emitted as a separate JSON object.

## Message schema ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#message-schema))

Messages returned from the JSON API are strictly typed according to the following schema:

Copy

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

`Message` and `MessageParam` types are available in Anthropic SDKs. For example, see the Anthropic [TypeScript](https://github.com/anthropics/anthropic-sdk-typescript) and [Python](https://github.com/anthropics/anthropic-sdk-python/) SDKs.

## Input formats ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#input-formats))

The SDK supports multiple input formats:

### Text input (default) ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#text-input-default))

- Command line
- TypeScript
- Python

Copy

```ts
// Direct prompt
for await (const message of query({
  prompt: "Explain this code"
})) {
  if (message.type === "result") console.log(message.result);
}

// From variable
const userInput = "Explain this code";
for await (const message of query({ prompt: userInput })) {
  if (message.type === "result") console.log(message.result);
}
```

### Streaming JSON input ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#streaming-json-input))

A stream of messages provided via `stdin` where each message represents a user turn. This allows multiple turns of a conversation without re-launching the `claude` binary and allows providing guidance to the model while it is processing a request.

Each message is a JSON ‘User message’ object, following the same format as the output message schema. Messages are formatted using the [jsonl](https://jsonlines.org/) format where each line of input is a complete JSON object. Streaming JSON input requires `-p` and `--output-format stream-json`.

Currently this is limited to text-only user messages.

Copy

```bash
$ echo '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Explain this code"}]}}' | claude -p --output-format=stream-json --input-format=stream-json --verbose
```

## Agent integration examples ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#agent-integration-examples))

### SRE incident response bot ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#sre-incident-response-bot))

- Command line
- TypeScript
- Python

Copy

```ts
import { query } from "@anthropic-ai/claude-code";

// Automated incident response agent
async function investigateIncident(
  incidentDescription: string, 
  severity = "medium"
) {
  const messages = [];
  
  for await (const message of query({
    prompt: `Incident: ${incidentDescription} (Severity: ${severity})`,
    options: {
      systemPrompt: "You are an SRE expert. Diagnose the issue, assess impact, and provide immediate action items.",
      maxTurns: 6,
      allowedTools: ["Bash", "Read", "WebSearch", "mcp__datadog"],
      mcpConfig: "monitoring-tools.json"
    }
  })) {
    messages.push(message);
  }
  
  return messages.find(m => m.type === "result");
}

// Usage
const result = await investigateIncident("Payment API returning 500 errors", "high");
console.log(result.result);
```

### Automated security review ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#automated-security-review))

- Command line
- TypeScript
- Python

Copy

```ts
import { query } from "@anthropic-ai/claude-code";
import { execSync } from "child_process";

async function auditPR(prNumber: number) {
  // Get PR diff
  const prDiff = execSync(`gh pr diff ${prNumber}`, { encoding: 'utf8' });
  
  const messages = [];
  for await (const message of query({
    prompt: prDiff,
    options: {
      systemPrompt: "You are a security engineer. Review this PR for vulnerabilities, insecure patterns, and compliance issues.",
      maxTurns: 3,
      allowedTools: ["Read", "Grep", "WebSearch"]
    }
  })) {
    messages.push(message);
  }
  
  return messages.find(m => m.type === "result");
}

// Usage
const report = await auditPR(123);
console.log(JSON.stringify(report, null, 2));
```

### Multi-turn legal assistant ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#multi-turn-legal-assistant))

- Command line
- TypeScript
- Python

Copy

```ts
import { query } from "@anthropic-ai/claude-code";

async function legalReview() {
  // Start legal review session
  let sessionId: string;
  
  for await (const message of query({
    prompt: "Start legal review session",
    options: { maxTurns: 1 }
  })) {
    if (message.type === "system" && message.subtype === "init") {
      sessionId = message.session_id;
    }
  }
  
  // Multi-step review using same session
  const steps = [
    "Review contract.pdf for liability clauses",
    "Check compliance with GDPR requirements",
    "Generate executive summary of risks"
  ];
  
  for (const step of steps) {
    for await (const message of query({
      prompt: step,
      options: { resumeSessionId: sessionId, maxTurns: 2 }
    })) {
      if (message.type === "result") {
        console.log(`Step: ${step}`);
        console.log(message.result);
      }
    }
  }
}
```

## Python-Specific Best Practices ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#python-specific-best-practices))

### Key Patterns ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#key-patterns))

Copy

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

### IPython/Jupyter Tips ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#ipython%2Fjupyter-tips))

Copy

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

## Best practices ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#best-practices))

- Use JSON output format for programmatic parsing of responses:

  Copy

  ```bash
  # Parse JSON response with jq
  result=$(claude -p "Generate code" --output-format json)
  code=$(echo "$result" | jq -r '.result')
  cost=$(echo "$result" | jq -r '.cost_usd')
  ```

- Handle errors gracefully - check exit codes and stderr:

  Copy

  ```bash
  if ! claude -p "$prompt" 2>error.log; then
      echo "Error occurred:" >&2
      cat error.log >&2
      exit 1
  fi
  ```

- Use session management for maintaining context in multi-turn conversations
- Consider timeouts for long-running operations:

  Copy

  ```bash
  timeout 300 claude -p "$complex_prompt" || echo "Timed out after 5 minutes"
  ```

- Respect rate limits when making multiple requests by adding delays between calls

## Related resources ([​](https://docs.anthropic.com/en/docs/claude-code/sdk#related-resources))

- [CLI usage and controls](https://docs.anthropic.com/en/docs/claude-code/cli-reference) - Complete CLI documentation
- [GitHub Actions integration](https://docs.anthropic.com/en/docs/claude-code/github-actions) - Automate your GitHub workflow with Claude
- [Common workflows](https://docs.anthropic.com/en/docs/claude-code/common-workflows) - Step-by-step guides for common use cases