# [[Building a Custom MCP Weather Server for Claude for Desktop]]

> **Goal:** Build a simple MCP weather server and connect it to Claude for Desktop (or any other MCP client).

---

## 📋 Overview

| **What we’ll build** | **Tools** |
|---|---|
| A server that fetches **weather forecasts** and **severe weather alerts** from the US National Weather Service (NWS) | `get_alerts` – weather alerts for a US state<br>`get_forecast` – forecast for a latitude/longitude pair |

<div align="center">
  <img src="https://mintlify.s3.us-west-1.amazonaws.com/mcp/images/weather-alerts.png" width="45%"/>
  <img src="https://mintlify.s3.us-west-1.amazonaws.com/mcp/images/current-weather.png" width="45%"/>
</div>

> **Note:** MCP servers can be used with any client. We’re using Claude for Desktop for simplicity, but you can also build your own client (see [building a client](/quickstart/client) and the list of other clients [/clients](/clients)).

---

## Core MCP Concepts

1. **Resources** – File‑like data (e.g., API responses) that can be read by clients.
2. **Tools** – Functions that the LLM can call (with user approval).
3. **Prompts** – Pre‑written templates that help users accomplish specific tasks.

> This tutorial focuses on **tools**.

---

## 📦 Prerequisites

- **Python** (or TypeScript/Java/Kotlin/C# – see the language‑specific tabs below)
- **LLMs** (e.g., Claude)

### Logging in MCP Servers

| Transport | **Never write** to `stdout` (will corrupt JSON‑RPC) |
|---|---|
| **STDIO** | `print()`, `console.log()`, `fmt.Println()`, etc. |
| **HTTP** | Standard output fine (doesn’t interfere with HTTP responses) |

#### Best practice
- Use a logging library that writes to **stderr** or to a log file.

#### Quick examples

```python
# ❌ Bad (STDIO)
print("Processing request")

# ✅ Good (STDIO)
import logging
logging.info("Processing request")
```

---

## 🛠️ System Requirements

- **Python 3.10+** (or Node ≥ 16 for TypeScript, Java 17+, Kotlin ≥ 1.6, .NET 8+).
- **Python MCP SDK 1.2.0+**.

---

## 📦 Set up (Python)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

> Restart the terminal so `uv` is on your PATH.

### Create the project

```bash
# macOS / Linux
uv init weather
cd weather

# create + activate a virtual environment
uv venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate    # Windows PowerShell

# install dependencies
uv add "mcp[cli]" httpx

# create the server file
touch weather.py   # Windows:  New-Item weather.py
```

---

## 🏗️ Building the Server (Python)

### 1️⃣ Import packages & create a FastMCP instance

```python
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# FastMCP automatically creates tool definitions from type hints & docstrings
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
```

### 2️⃣ Helper functions

```python
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """GET request to the NWS API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Turn an alert feature into a readable string."""
    p = feature["properties"]
    return f"""
Event: {p.get('event', 'Unknown')}
Area: {p.get('areaDesc', 'Unknown')}
Severity: {p.get('severity', 'Unknown')}
Description: {p.get('description', 'No description')}
Instructions: {p.get('instruction', 'No instructions')}
"""
```

### 3️⃣ Tool definitions

```python
@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state (two‑letter code)."""
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(f) for f in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get a short forecast for a location."""
    # 1️⃣ Get grid point
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points = await make_nws_request(points_url)
    if not points:
        return "Unable to fetch forecast data for this location."

    # 2️⃣ Get forecast URL
    forecast_url = points["properties"]["forecast"]
    forecast = await make_nws_request(forecast_url)
    if not forecast:
        return "Unable to fetch detailed forecast."

    # 3️⃣ Format up to 5 periods
    periods = forecast["properties"]["periods"][:5]
    out = []
    for p in periods:
        out.append(f"""
{p['name']}:
  Temp: {p['temperature']}°{p['temperatureUnit']}
  Wind: {p['windSpeed']} {p['windDirection']}
  Forecast: {p['detailedForecast']}
""")
    return "\n---\n".join(out)
```

### 4️⃣ Run the server (STDIO)

```python
if __name__ == "__main__":
    # launch with stdio transport
    mcp.run(transport="stdio")
```

**Run the server**

```bash
uv run weather.py
```

---

## 🚀 Test with Claude for Desktop

> **Claude for Desktop is not yet available on Linux** – Linux users should follow the [Build a client](/quickstart/client) tutorial.

### 1️⃣ Install Claude for Desktop

Download & install the latest version from https://claude.ai/download and make sure it’s up‑to‑date.

### 2️⃣ Add the server to `claude_desktop_config.json`

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Open the file (e.g., `code ~/.config/...`), then add:

#### macOS / Linux

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/PARENT/FOLDER/weather",
        "run",
        "weather.py"
      ]
    }
  }
}
```

#### Windows

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "--directory",
          "C:\\ABSOLUTE\\PATH\\TO\\PARENT\\FOLDER\\weather",
          "run",
          "weather.py"
        ]
      }
    }
}
```

> **Tip:** Use `which uv` (macOS/Linux) or `where uv` (Windows) to get the absolute path to `uv`.
> **Tip:** Use `pwd` (macOS/Linux) or `cd` (Windows) to get the absolute path to the server folder.

Restart **Claude for Desktop**. The **Search & Tools** slider (🔧) should now show the two tools.

---

## 📚 Other Language Implementations

> All language‑specific tutorials have the same structure (setup, helper functions, tool registration, and running the server). Below are quick‑start snippets for each language.

### TypeScript (Node)

```bash
# Install Node & npm if you haven’t already.
node --version && npm --version

# Project setup
mkdir weather && cd $_
npm init -y
npm i @modelcontextprotocol/sdk zod
npm i -D @types/node typescript
mkdir src && touch src/index.ts

# package.json additions
{
  "type": "module",
  "bin": {"weather":"./build/index.js"},
  "scripts": {"build":"tsc && chmod 755 build/index.js"},
  "files":["build"]
}
```

#### `src/index.ts` (excerpt)

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const NWS_API_BASE = "https://api.weather.gov";
const USER_AGENT = "weather-app/1.0";

const server = new McpServer({
  name: "weather",
  version: "1.0.0",
  capabilities: {tools:{}, resources:{}}
});

// ... helper functions (makeNWSRequest, formatAlert) ...

// Register tools (same logic as Python)

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Weather MCP Server running on stdio");
}
main().catch(e => {
  console.error("Fatal error:", e);
  process.exit(1);
});
```

**Run**

```bash
npm run build
node build/index.js
```

#### `claude_desktop_config.json` (Node)

```json
{
  "mcpServers": {
    "weather": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/FOLDER/weather/build/index.js"]
    }
  }
}
```

---

### Java (Spring AI)

> **Dependencies** (Maven/Gradle) – `spring-ai-starter-mcp-server` + `spring-web`

```xml
<dependency>
  <groupId>org.springframework.ai</groupId>
  <artifactId>spring-ai-starter-mcp-server</artifactId>
</dependency>
<dependency>
  <groupId>org.springframework</groupId>
  <artifactId>spring-web</artifactId>
</dependency>
```

#### `WeatherService.java` (excerpt)

```java
@Service
public class WeatherService {
    private final RestClient restClient = RestClient.builder()
        .baseUrl("https://api.weather.gov")
        .defaultHeader("Accept", "application/geo+json")
        .defaultHeader("User-Agent", "WeatherApiClient/1.0 (you@domain.com)")
        .build();

    @Tool(description = "Get weather forecast for a pair of coordinates")
    public String getWeatherForecastByLocation(double lat, double lon) { /* … */ }

    @Tool(description = "Get weather alerts for a US state")
    public String getAlerts(@ToolParam(description = "Two‑letter state code") String state) { /* … */ }
}
```

#### `McpServerApplication.java`

```java
@SpringBootApplication
public class McpServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(McpServerApplication.class, args);
    }

    @Bean
    public ToolCallbackProvider weatherTools(WeatherService service) {
        return MethodToolCallbackProvider.builder()
                .toolObjects(service)
                .build();
    }
}
```

**Build & run**

```bash
./mvnw clean install   # produces mcp-weather-stdio-server-0.0.1-SNAPSHOT.jar
```

#### `claude_desktop_config.json` (Java)

```json
{
  "mcpServers": {
    "spring-ai-mcp-weather": {
      "command": "java",
      "args": [
        "-Dspring.ai.mcp.server.stdio=true",
        "-jar",
        "/ABSOLUTE/PATH/TO/mcp-weather-stdio-server-0.0.1-SNAPSHOT.jar"
      ]
    }
  }
}
```

---

### Kotlin

**Gradle setup**

```kotlin
plugins {
    kotlin("jvm") version "1.9.0"
    kotlin("plugin.serialization") version "1.9.0"
    id("com.github.johnrengelman.shadow") version "8.1.1"
}
```

**Dependencies**

```kotlin
dependencies {
    implementation("io.modelcontextprotocol:kotlin-sdk:0.4.0")
    implementation("org.slf4j:slf4j-nop:2.0.9")
    implementation("io.ktor:ktor-client-content-negotiation:3.1.1")
    implementation("io.ktor:ktor-serialization-kotlinx-json:3.1.1")
}
```

#### Server entry (`run mcp server`)

```kotlin
fun `run mcp server`() {
    val server = Server(
        Implementation(name = "weather", version = "1.0.0"),
        ServerOptions(ServerCapabilities(tools = ServerCapabilities.Tools(listChanged = true)))
    val transport = StdioServerTransport(
        System.`in`.asInput(),
        System.out.asSink().buffered()
    )
    runBlocking {
        server.connect(transport)
        val done = CompletableDeferred<Unit>()
        server.onClose { done.complete(Unit) }
        done.await()
    }
}
```

**Tool registration** – `get_alerts` and `get_forecast` are implemented exactly as in the Python version (using `HttpClient` + `kotlinx.serialization`).

**Run**

```bash
./gradlew build   # produces weather-0.1.0-all.jar
```

#### `claude_desktop_config.json` (Kotlin)

```json
{
  "mcpServers": {
    "weather": {
      "command": "java",
      "args": [
        "-jar",
        "/ABSOLUTE/PATH/TO/weather/build/libs/weather-0.1.0-all.jar"
        ]
    }
  }
}
```

---

### C# (.NET 8)

```bash
dotnet new console -n weather
cd weather
dotnet add package ModelContextProtocol --prerelease
dotnet add package Microsoft.Extensions.Hosting
```

#### `Program.cs` (excerpt)

```csharp
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ModelContextProtocol;
using System.Net.Http.Headers;

var builder = Host.CreateEmptyApplicationBuilder();

builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

builder.Services.AddSingleton(_ =>
{
    var client = new HttpClient { BaseAddress = new Uri("https://api.weather.gov") };
    client.DefaultRequestHeaders.UserAgent.Add(new ProductInfoHeaderValue("weather-tool", "1.0"));
    return client;
});

var app = builder.Build();
await app.RunAsync();
```

#### Helper extensions (`HttpClientExt`) and `WeatherTools` (same logic as Python, using `System.Text.Json`).

**Run**

```bash
dotnet run
```

#### `claude_desktop_config.json` (C#)

```json
{
  "mcpServers": {
    "weather": {
      "command": "dotnet",
      "args": [
        "run",
          "--project",
          "/ABSOLUTE/PATH/TO/weather/Weather.csproj",
          "--no-build"
        ]
    }
  }
}
```

---

## ✅ Test the Tools in Claude for Desktop

1. Look for the **“Search & tools”** slider (🔧) in the Claude UI.
2. Click the slider; you should see **`get_alerts`** and **`get_forecast`**.

**Example queries**

- “What’s the weather in Sacramento?”
- “What are the active weather alerts in Texas?”

> The NWS only covers the United States, so queries must be U.S. locations.

---

## 🔎 What’s happening under the hood

1. **Claude** receives your request.
2. Claude decides which tool(s) to call.
3. The client executes the tool(s) via the MCP server.
4. Results are returned to Claude.
5. Claude generates a natural‑language response.
6. You see the answer in the UI.

---

## 🛠️ Troubleshooting

<details>
<summary>Claude for Desktop Integration Issues</summary>

**Logs**

- General logs: `~/Library/Logs/Claude/mcp.log`
- Server‑specific logs: `mcp-server-<NAME>.log` (stderr)

```bash
# follow logs in real‑time
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Common problems**

| Problem | Fix |
|---|---|
| Server doesn’t appear | ✔︎ Verify JSON in `claude_desktop_config.json`<br>✔︎ Use absolute paths<br>✔︎ Restart Claude |
| Tools fail silently | Check logs for errors<br>Make sure the server builds & runs<br>Restart Claude |
| Nothing works | Follow the [debugging guide](/legacy/tools/debugging) |

</details>

<details>
<summary>Weather API Issues</summary>

| Issue | Likely cause | Fix |
|---|---|---|
| “Failed to retrieve grid point data” | Coordinates outside the US, API outage, rate‑limit | Use US coordinates; add delay; check NWS status |
| “No active alerts for [STATE]” | No active alerts; not an error | Try a different state or wait for alerts |
</details>

> **More advanced debugging:** see the [Debugging MCP](/legacy/tools/debugging) guide.

---

## 🚀 Next Steps

- **[[Building a client]](/quickstart/client)** – Learn how to build a custom MCP client.
- **[[Example servers]](/examples)** – Browse official MCP server implementations.
- **[[Debugging Guide]](/legacy/tools/debugging)** – Techniques for diagnosing MCP issues.
- **[[Building MCP with LLMs]](/tutorials/building-mcp-with-llms)** – Use LLMs to speed up MCP development.

---


## Python

### Imports & instance setup
```python
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
```

### Helper functions
```python
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""
```

### Tool definitions
```python
@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(f) for f in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # Get grid point
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get forecast URL
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format up to 5 periods
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:
        forecasts.append(f"""
{period['name']}:
  Temperature: {period['temperature']}°{period['temperatureUnit']}
  Wind: {period['windSpeed']} {period['windDirection']}
  Forecast: {period['detailedForecast']}
""")
    return "\n---\n".join(forecasts)
```

### Run the server
```python
if __name__ == "__main__":
    # Start the server using STDIO transport
    mcp.run(transport='stdio')
```

---

## TypeScript / JavaScript

### Server setup & imports
```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const NWS_API_BASE = "https://api.weather.gov";
const USER_AGENT = "weather-app/1.0";

const server = new McpServer({
  name: "weather",
  version: "1.0.0",
  capabilities: {
    resources: {},
    tools: {},
  },
});
```

### Helper functions
```typescript
// Helper for NWS API requests
async function makeNWSRequest<T>(url: string): Promise<T | null> {
  const headers = {
    "User-Agent": USER_AGENT,
    Accept: "application/geo+json",
  };
  try {
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error("Error making NWS request:", error);
    return null;
  }
}

interface AlertFeature {
  properties: {
    event?: string;
    areaDesc?: string;
    severity?: string;
    status?: string;
    headline?: string;
  };
}

// Format alert data
function formatAlert(feature: AlertFeature): string {
  const p = feature.properties;
  return [
    `Event: ${p.event ?? "Unknown"}`,
    `Area: ${p.areaDesc ?? "Unknown"}`,
    `Severity: ${p.severity ?? "Unknown"}`,
    `Status: ${p.status ?? "Unknown"}`,
    `Headline: ${p.headline ?? "No headline"}`,
    "---",
  ].join("\n");
}
```

### Tool registration
```typescript
// Register get_alerts
server.tool(
  "get_alerts",
  "Get weather alerts for a state",
  {
    state: z.string().length(2).describe("Two‑letter state code (e.g. CA, NY)"),
  },
  async ({ state }) => {
    const stateCode = state.toUpperCase();
    const alertsUrl = `${NWS_API_BASE}/alerts?area=${stateCode}`;
    const alertsData = await makeNWSRequest<{ features: AlertFeature[] }>(alertsUrl);

    if (!alertsData) {
      return {
        content: [{ type: "text", text: "Failed to retrieve alerts data" }],
      };
    }

    const features = alertsData.features ?? [];
    if (features.length === 0) {
      return {
        content: [{ type: "text", text: `No active alerts for ${stateCode}` }],
      };
    }

    const alertsText = features.map(formatAlert).join("\n");
    return { content: [{ type: "text", text: `Active alerts for ${stateCode}:\n\n${alertsText}` }] };
  },
);

// Register get_forecast
server.tool(
  "get_forecast",
  "Get weather forecast for a location",
  {
    latitude: z.number().min(-90).max(90).describe("Latitude"),
    longitude: z.number().min(-180).max(180).describe("Longitude"),
  },
  async ({ latitude, longitude }) => {
    const pointsUrl = `${NWS_API_BASE}/points/${latitude.toFixed(4)},${longitude.toFixed(4)}`;
    const pointsData = await makeNWSRequest<{
      properties: { forecast?: string };
    }>(pointsUrl);

    if (!pointsData?.properties?.forecast) {
      return {
        content: [{ type: "text", text: "Unable to retrieve forecast data" }],
      };
    }

    const forecastData = await makeNWSRequest<{
      properties: { periods: any[] };
    }>(pointsData.properties.forecast);

    if (!forecastData?.properties?.periods?.length) {
      return {
        content: [{ type: "text", text: "No forecast periods available" }],
      };
    }

    const formatted = forecastData.properties.periods.map((p) => [
      `${p.name || "Unknown"}:`,
      `Temperature: ${p.temperature ?? "Unknown"}°${p.temperatureUnit ?? "F"}`,
      `Wind: ${p.windSpeed ?? "Unknown"} ${p.windDirection ?? ""}`,
      `${p.shortForecast ?? "No forecast"}`,
      "---",
    ].join("\n"));

    return {
      content: [{ type: "text", text: formatted.join("\n") }],
    };
  },
);
```

### Main entry point
```typescript
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Weather MCP Server running on stdio");
}

main().catch((e) => {
  console.error("Fatal error:", e);
  process.exit(1);
});
```
