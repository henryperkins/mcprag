---
title: Tools · Cloudflare Agents docs
description: Model Context Protocol (MCP) tools are functions that a MCP Server
  provides and MCP clients can call.
lastUpdated: 2025-03-25T10:04:19.000Z
chatbotDeprioritize: false
source_url:
  html: https://developers.cloudflare.com/agents/model-context-protocol/tools/
  md: https://developers.cloudflare.com/agents/model-context-protocol/tools/index.md
---

Model Context Protocol (MCP) tools are functions that a [MCP Server](https://developers.cloudflare.com/agents/model-context-protocol) provides and MCP clients can call.

When you build MCP Servers with the `@cloudflare/model-context-protocol` package, you can define tools the [same way as shown in the `@modelcontextprotocol/typescript-sdk` package's examples](https://github.com/modelcontextprotocol/typescript-sdk?tab=readme-ov-file#tools).

For example, the following code from [this example MCP server](https://github.com/cloudflare/ai/tree/main/demos/remote-mcp-server) defines a simple MCP server that adds two numbers together:

* JavaScript

  ```js
  import { McpServer } from "@modelcontextprotocol/sdk/server/mcp";
  import { McpAgent } from "agents/mcp";


  export class MyMCP extends McpAgent {
    server = new McpServer({ name: "Demo", version: "1.0.0" });
    async init() {
      this.server.tool(
        "add",
        { a: z.number(), b: z.number() },
        async ({ a, b }) => ({
          content: [{ type: "text", text: String(a + b) }],
        }),
      );
    }
  }
  ```

* TypeScript

  ```ts
  import { McpServer } from "@modelcontextprotocol/sdk/server/mcp";
  import { McpAgent } from "agents/mcp";


  export class MyMCP extends McpAgent {
    server = new McpServer({ name: "Demo", version: "1.0.0" });
    async init() {
      this.server.tool(
        "add",
        { a: z.number(), b: z.number() },
        async ({ a, b }) => ({
          content: [{ type: "text", text: String(a + b) }],
        }),
      );
    }
  }
  ```
