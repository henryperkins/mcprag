---
title: Agents · Cloudflare Agents docs
description: An agent is an AI system that can autonomously execute tasks by
  making decisions about tool usage and process flow. Unlike traditional
  automation that follows predefined paths, agents can dynamically adapt their
  approach based on context and intermediate results. Agents are also distinct
  from co-pilots (e.g. traditional chat applications) in that they can fully
  automate a task, as opposed to simply augmenting and extending human input.
lastUpdated: 2025-02-25T13:55:21.000Z
chatbotDeprioritize: false
source_url:
  html: https://developers.cloudflare.com/agents/concepts/what-are-agents/
  md: https://developers.cloudflare.com/agents/concepts/what-are-agents/index.md
---

### What are agents?

An agent is an AI system that can autonomously execute tasks by making decisions about tool usage and process flow. Unlike traditional automation that follows predefined paths, agents can dynamically adapt their approach based on context and intermediate results. Agents are also distinct from co-pilots (e.g. traditional chat applications) in that they can fully automate a task, as opposed to simply augmenting and extending human input.

* **Agents** → non-linear, non-deterministic (can change from run to run)
* **Workflows** → linear, deterministic execution paths
* **Co-pilots** → augmentative AI assistance requiring human intervention

### Example: Booking vacations

If this is your first time working with, or interacting with agents, this example will illustrate how an agent works within a context like booking a vacation. If you are already familiar with the topic, read on.

Imagine you're trying to book a vacation. You need to research flights, find hotels, check restaurant reviews, and keep track of your budget.

#### Traditional workflow automation

A traditional automation system follows a predetermined sequence:

* Takes specific inputs (dates, location, budget)
* Calls predefined API endpoints in a fixed order
* Returns results based on hardcoded criteria
* Cannot adapt if unexpected situations arise

![Traditional workflow automation diagram](https://developers.cloudflare.com/_astro/workflow-automation.D1rsykgR_15theP.svg)

#### AI Co-pilot

A co-pilot acts as an intelligent assistant that:

* Provides hotel and itinerary recommendations based on your preferences
* Can understand and respond to natural language queries
* Offers guidance and suggestions
* Requires human decision-making and action for execution

![A co-pilot diagram](https://developers.cloudflare.com/_astro/co-pilot.BZ_kRuK6_Z9KfL9.svg)

#### Agent

An agent combines AI's ability to make judgements and call the relevant tools to execute the task. An agent's output will be nondeterministic given:

* Real-time availability and pricing changes
* Dynamic prioritization of constraints
* Ability to recover from failures
* Adaptive decision-making based on intermediate results

![An agent diagram](https://developers.cloudflare.com/_astro/agent-workflow.5VDKtHdO_ALLGh.svg)

An agents can dynamically generate an itinerary and execute on booking reservations, similarly to what you would expect from a travel agent.

### Three primary components of agent systems:

* **Decision Engine**: Usually an LLM (Large Language Model) that determines action steps
* **Tool Integration**: APIs, functions, and services the agent can utilize
* **Memory System**: Maintains context and tracks task progress

#### How agents work

Agents operate in a continuous loop of:

1. **Observing** the current state or task
2. **Planning** what actions to take, using AI for reasoning
3. **Executing** those actions using available tools (often APIs or [MCPs](https://modelcontextprotocol.io/introduction))
4. **Learning** from the results (storing results in memory, updating task progress, and preparing for next iteration)
