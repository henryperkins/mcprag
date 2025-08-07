---
title: Agents · Cloudflare Agents docs
description: The Agents SDK enables you to build and deploy AI-powered agents
  that can autonomously perform tasks, communicate with clients in real time,
  call AI models, persist state, schedule tasks, run asynchronous workflows,
  browse the web, query data from your database, support human-in-the-loop
  interactions, and a lot more.
lastUpdated: 2025-03-18T12:13:40.000Z
chatbotDeprioritize: false
source_url:
  html: https://developers.cloudflare.com/agents/
  md: https://developers.cloudflare.com/agents/index.md
---

The Agents SDK enables you to build and deploy AI-powered agents that can autonomously perform tasks, communicate with clients in real time, call AI models, persist state, schedule tasks, run asynchronous workflows, browse the web, query data from your database, support human-in-the-loop interactions, and [a lot more](https://developers.cloudflare.com/agents/api-reference/).

### Ship your first Agent

To use the Agent starter template and create your first Agent with the Agents SDK:

```sh
# install it
npm create cloudflare@latest agents-starter -- --template=cloudflare/agents-starter
# and deploy it
npx wrangler@latest deploy
```

Head to the guide on [building a chat agent](https://developers.cloudflare.com/agents/getting-started/build-a-chat-agent) to learn how the starter project is built and how to use it as a foundation for your own agents.

If you're already building on [Workers](https://developers.cloudflare.com/workers/), you can install the `agents` package directly into an existing project:

```sh
npm i agents
```

And then define your first Agent by creating a class that extends the `Agent` class:

* JavaScript

  ```js
  import { Agent, AgentNamespace } from "agents";


  export class MyAgent extends Agent {
    // Define methods on the Agent:
    // https://developers.cloudflare.com/agents/api-reference/agents-api/
    //
    // Every Agent has built in state via this.setState and this.sql
    // Built-in scheduling via this.schedule
    // Agents support WebSockets, HTTP requests, state synchronization and
    // can run for seconds, minutes or hours: as long as the tasks need.
  }
  ```

* TypeScript

  ```ts
  import { Agent, AgentNamespace } from 'agents';


  export class MyAgent extends Agent {
    // Define methods on the Agent:
    // https://developers.cloudflare.com/agents/api-reference/agents-api/
    //
    // Every Agent has built in state via this.setState and this.sql
    // Built-in scheduling via this.schedule
    // Agents support WebSockets, HTTP requests, state synchronization and
    // can run for seconds, minutes or hours: as long as the tasks need.
  }
  ```

Dive into the [Agent SDK reference](https://developers.cloudflare.com/agents/api-reference/agents-api/) to learn more about how to use the Agents SDK package and defining an `Agent`.

### Why build agents on Cloudflare?

We built the Agents SDK with a few things in mind:

* **Batteries (state) included**: Agents come with [built-in state management](https://developers.cloudflare.com/agents/api-reference/store-and-sync-state/), with the ability to automatically sync state between an Agent and clients, trigger events on state changes, and read+write to each Agent's SQL database.
* **Communicative**: You can connect to an Agent via [WebSockets](https://developers.cloudflare.com/agents/api-reference/websockets/) and stream updates back to client in real-time. Handle a long-running response from a reasoning model, the results of an [asynchronous workflow](https://developers.cloudflare.com/agents/api-reference/run-workflows/), or build a chat app that builds on the `useAgent` hook included in the Agents SDK.
* **Extensible**: Agents are code. Use the [AI models](https://developers.cloudflare.com/agents/api-reference/using-ai-models/) you want, bring-your-own headless browser service, pull data from your database hosted in another cloud, add your own methods to your Agent and call them.

Agents built with Agents SDK can be deployed directly to Cloudflare and run on top of [Durable Objects](https://developers.cloudflare.com/durable-objects/) — which you can think of as stateful micro-servers that can scale to tens of millions — and are able to run wherever they need to. Run your Agents close to a user for low-latency interactivity, close to your data for throughput, and/or anywhere in between.

***

### Build on the Cloudflare Platform

**[Workers](https://developers.cloudflare.com/workers/)**

Build serverless applications and deploy instantly across the globe for exceptional performance, reliability, and scale.

**[AI Gateway](https://developers.cloudflare.com/ai-gateway/)**

Observe and control your AI applications with caching, rate limiting, request retries, model fallback, and more.

**[Vectorize](https://developers.cloudflare.com/vectorize/)**

Build full-stack AI applications with Vectorize, Cloudflare’s vector database. Adding Vectorize enables you to perform tasks such as semantic search, recommendations, anomaly detection or can be used to provide context and memory to an LLM.

**[Workers AI](https://developers.cloudflare.com/workers-ai/)**

Run machine learning models, powered by serverless GPUs, on Cloudflare's global network.

**[Workflows](https://developers.cloudflare.com/workflows/)**

Build stateful agents that guarantee executions, including automatic retries, persistent state that runs for minutes, hours, days, or weeks.
