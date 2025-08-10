---
title: "Get started using the Azure MCP Server - Azure MCP Server"
source: "https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started?tabs=one-click%2Cazure-cli&pivots=mcp-python"
author:
  - "[[alexwolfmsft]]"
published:
created: 2025-08-09
description: "Learn how to connect to and consume Azure MCP Server operations"
tags:
  - "clippings"
---
## Get started with Azure MCP Server

The Azure MCP Server uses the Model Context Protocol (MCP) to standardize integrations between AI apps and external tools and data sources, allowing for AI systems to perform operations that are context-aware of your Azure resources.

In this article, you learn how to complete the following tasks:

- Install and authenticate to the Azure MCP Server
- Connect to Azure MCP Server using using GitHub Copilot agent mode in Visual Studio Code
- Run prompts to test Azure MCP Server operations and interact with Azure resources

## Prerequisites

- An [Azure account](https://azure.microsoft.com/free/?ref=microsoft.com&utm_source=microsoft.com&utm_medium=docs&utm_campaign=visualstudio) with an active subscription
- [Visual Studio Code](https://code.visualstudio.com/download)
- [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) Visual Studio Code extension

Select one of the following options to install the Azure MCP Server in Visual Studio Code:

- [Global install](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/?tabs=one-click%2Cazure-cli&pivots=mcp-python#tabpanel_1_one-click)
- [Directory install](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/?tabs=one-click%2Cazure-cli&pivots=mcp-python#tabpanel_1_manual)

1. To install the Azure MCP Server for Visual Studio Code in your user settings, select the following link:
	[![Install with NPX in Visual Studio Code](https://img.shields.io/badge/VS_Code-Install_Azure_MCP_Server-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Azure%20MCP%20Server&config=%7B%22command%22%3A%22npx%22%2C%22args%22%3A%5B%22-y%22%2C%22%40azure%2Fmcp%40latest%22%2C%22server%22%2C%22start%22%5D%7D)
	A list of installation options opens inside Visual Studio Code. Select **Install Server** to add the server configuration to your user settings.
	![A screenshot showing Azure MCP Server installation options.](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/media/install-mcp-server.png)
	A screenshot showing Azure MCP Server installation options.
2. Open GitHub Copilot and select Agent Mode. To learn more about Agent Mode, visit the [Visual Studio Code Documentation](https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode).
3. Refresh the tools list to see Azure MCP Server as an available option:
	![A screenshot showing Azure MCP Server as GitHub Copilot tool.](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/media/github-copilot-integration.png)
	A screenshot showing Azure MCP Server as GitHub Copilot tool.

1. Open GitHub Copilot and select Agent Mode.
2. Enter a prompt that causes the agent to use Azure MCP Server tools, such as *List my Azure resource groups*.
3. In order to authenticate Azure MCP Server, Copilot prompts you to sign-in to Azure using the browser.
4. Copilot requests permission to run the necessary Azure MCP Server operation for your prompt. Select **Continue** or use the arrow to select a more specific behavior:
	- **Current session** always runs the operation in the current GitHub Copilot Agent Mode session.
	- **Current workspace** always runs the command for current Visual Studio Code workspace.
	- **Always allow** sets the operation to always run for any GitHub Copilot Agent Mode session or any Visual Studio Code workspace.
	![A screenshot showing the options available to run Azure MCP Server operations.](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/media/run-command-prompt.png)
	A screenshot showing the options available to run Azure MCP Server operations.
	The output for the previous prompt should resemble the following text:
	```
	The following resource groups are available for your subscription:
	1. **DefaultResourceGroup-EUS** (Location: \`eastus\`)
	2. **rg-testing** (Location: \`centralus\`)
	3. **rg-azd** (Location: \`eastus2\`)
	4. **msdocs-sample** (Location: \`southcentralus\`)
	14. **ai-testing** (Location: \`eastus2\`)
	Let me know if you need further details or actions related to any of these resource groups!
	```
5. Explore and test the Azure MCP operations using other relevant prompts, such as:
	```
	List all of the storage accounts in my subscription
	Get the available tables in my storage accounts
	```

In this article, you learn how to complete the following tasks:

- Install and authenticate to the Azure MCP Server
- Connect to Azure MCP Server using a custom.NET client
- Run prompts to test Azure MCP Server operations and manage Azure resources

## Prerequisites

- An [Azure account](https://azure.microsoft.com/free/?ref=microsoft.com&utm_source=microsoft.com&utm_medium=docs&utm_campaign=visualstudio) with an active subscription
- [.NET 9.0](https://dotnet.microsoft.com/en-us/download)
- [Node.js](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)

Azure MCP Server provides a seamless authentication experience using token-based authentication via Microsoft Entra ID. Internally, Azure MCP Server uses [`DefaultAzureCredential`](https://learn.microsoft.com/en-us/dotnet/azure/sdk/authentication/credential-chains?tabs=dac) from the [Azure Identity library](https://learn.microsoft.com/en-us/dotnet/api/overview/azure/identity-readme?view=azure-dotnet&preserve-view=true) to authenticate users.

You need to sign-in to one of the tools supported by `DefaultAzureCredential` locally with your Azure account to work with Azure MCP Server. Sign-in using a terminal window, such as the Visual Studio Code terminal:

Once you have signed-in successfully to one of the preceding tools, Azure MCP Server can automatically discover your credentials and use them to authenticate and perform operations on Azure services.

Complete the following steps to create a.NET console app. The app connects to an AI model and acts as a host for an MCP client that connects to an Azure MCP Server.

1. Open a terminal to an empty folder where you want to create the project.
2. Run the following command to create a new.NET console application:
	```
	dotnet new console -n MCPHostApp
	```
3. Navigate into the newly created project folder:
	```
	cd MCPHostApp
	```
4. Open the project folder in your editor of choice, such as Visual Studio Code:
	```
	code .
	```
1. In the terminal, run the following commands to add the necessary NuGet packages:
	```
	dotnet add package Azure.AI.OpenAI --prerelease
	dotnet add package Azure.Identity
	dotnet add package Microsoft.Extensions.AI --prerelease
	dotnet add package Microsoft.Extensions.AI.OpenAI --prerelease
	dotnet add package ModelContextProtocol --prerelease
	```
2. Verify that the packages were added by checking the `MCPHostApp.csproj` file.
3. Run the following command to build the project and ensure everything is set up correctly:
	```
	dotnet build
	```

Replace the contents of `Program.cs` with the following code:

```csharp
using Azure.AI.OpenAI;
using Azure.Identity;
using Microsoft.Extensions.AI;
using ModelContextProtocol.Client;
using ModelContextProtocol.Protocol.Transport;

// Create an IChatClient
IChatClient client =
    new ChatClientBuilder(
        new AzureOpenAIClient(new Uri("<your-Azure-OpenAI-endpoint>"), 
        new DefaultAzureCredential())
        .GetChatClient("gpt-4o").AsIChatClient())
    .UseFunctionInvocation()
    .Build();

// Create the MCP client
var mcpClient = await McpClientFactory.CreateAsync(
    new StdioClientTransport(new()
    {
        Command = "npx",
        Arguments = ["-y", "@azure/mcp@latest", "server", "start"],
        Name = "Azure MCP",
    }));

// Get all available tools from the MCP server
Console.WriteLine("Available tools:");
var tools = await mcpClient.ListToolsAsync();
foreach (var tool in tools)
{
    Console.WriteLine($"{tool}");
}
Console.WriteLine();

// Conversational loop that can utilize the tools
List<ChatMessage> messages = [];
while (true)
{
    Console.Write("Prompt: ");
    messages.Add(new(ChatRole.User, Console.ReadLine()));

    List<ChatResponseUpdate> updates = [];
    await foreach (var update in client
        .GetStreamingResponseAsync(messages, new() { Tools = [.. tools] }))
    {
        Console.Write(update);
        updates.Add(update);
    }
    Console.WriteLine();

    messages.AddMessages(updates);
}
```

The preceding code accomplishes the following tasks:

- Initializes an `IChatClient` abstraction using the [`Microsoft.Extensions.AI`](https://learn.microsoft.com/en-us/dotnet/ai/microsoft-extensions-ai) libraries.
- Creates an MCP client to interact with the Azure MCP Server using a standard I/O transport. The provided `npx` command and corresponding arguments download and start the Azure MCP Server.
- Retrieves and displays a list of available tools from the MCP server, which is a standard MCP function.
- Implements a conversational loop that processes user prompts and utilizes the tools for responses.

Complete the following steps to test your.NET host app:

1. In a terminal window open to the root of your project, run the following command to start the app:
	```
	dotnet run
	```
2. Once the app is running, enter the following test prompt:
	```
	List all of the resource groups in my subscription
	```
	The output for the previous prompt should resemble the following text:
	```
	The following resource groups are available for your subscription:
	1. **DefaultResourceGroup-EUS** (Location: \`eastus\`)
	2. **rg-testing** (Location: \`centralus\`)
	3. **rg-azd** (Location: \`eastus2\`)
	4. **msdocs-sample** (Location: \`southcentralus\`)
	14. **ai-testing** (Location: \`eastus2\`)
	Let me know if you need further details or actions related to any of these resource groups!
	```
3. Explore and test the Azure MCP operations using other relevant prompts, such as:
	```
	List all of the storage accounts in my subscription
	Get the available tables in my storage accounts
	```

In this article, you learn how to complete the following tasks:

- Install and authenticate to the Azure MCP Server
- Connect to Azure MCP Server using a custom Python client
- Run prompts to test Azure MCP Server operations and manage Azure resources

## Prerequisites

- An [Azure account](https://azure.microsoft.com/free/?ref=microsoft.com&utm_source=microsoft.com&utm_medium=docs&utm_campaign=visualstudio) with an active subscription
- [Python 3.9 or higher](https://www.python.org/downloads/) installed locally
- [Node.js](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) installed locally

Azure MCP Server provides a seamless authentication experience using token-based authentication via Microsoft Entra ID. Internally, Azure MCP Server uses [`DefaultAzureCredential`](https://learn.microsoft.com/en-us/dotnet/azure/sdk/authentication/credential-chains?tabs=dac) from the [Azure Identity library](https://learn.microsoft.com/en-us/dotnet/api/overview/azure/identity-readme?view=azure-dotnet&preserve-view=true) to authenticate users.

You need to sign-in to one of the tools supported by `DefaultAzureCredential` locally with your Azure account to work with Azure MCP Server. Sign-in using a terminal window, such as the Visual Studio Code terminal:

Once you have signed-in successfully to one of the preceding tools, Azure MCP Server can automatically discover your credentials and use them to authenticate and perform operations on Azure services.

Complete the following steps to create a Python app. The app connects to an AI model and acts as a host for an MCP client that connects to an Azure MCP Server.

1. Open an empty folder inside your editor of choice.
2. Create a new file named `requirements.txt` and add the following library dependencies:
	```
	mcp
	azure-identity
	openai
	logging
	```
3. In the same folder, create a new file named `.env` and add the following environment variables:
	```
	AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>
	AZURE_OPENAI_MODEL=<your-model-deployment-name>
	```
4. Create an empty file named `main.py` to hold the code for your app.
1. Open a terminal in your new folder and create a Python virtual environment for the app:
	```
	python -m venv venv
	```
2. Activate the virtual environment:
	```
	venv\Scripts\activate
	```
3. Install the dependencies from `requirements.txt`:
	```
	pip install -r requirements.txt
	```

Update the contents of `Main.py` with the following code:

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import json, os, logging, asyncio
from dotenv import load_dotenv

# Setup logging and load environment variables
logger = logging.getLogger(__name__)
load_dotenv()

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")

# Initialize Azure credentials
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

async def run():
    # Initialize Azure OpenAI client
    client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT, 
            api_version="2024-04-01-preview", 
            azure_ad_token_provider=token_provider
        )

    # MCP client configurations
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@azure/mcp@latest", "server", "start"],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            for tool in tools.tools: print(tool.name)

            # Format tools for Azure OpenAI
            available_tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            } for tool in tools.tools]

            # Start conversational loop
            messages = []
            while True:
                try:
                    user_input = input("\nPrompt: ")
                    messages.append({"role": "user", "content": user_input})

                    # First API call with tool configuration
                    response = client.chat.completions.create(
                        model = AZURE_OPENAI_MODEL,
                        messages = messages,
                        tools = available_tools)

                    # Process the model's response
                    response_message = response.choices[0].message
                    messages.append(response_message)

                    # Handle function calls
                    if response_message.tool_calls:
                        for tool_call in response_message.tool_calls:
                                function_args = json.loads(tool_call.function.arguments)
                                result = await session.call_tool(tool_call.function.name, function_args)

                                # Add the tool response to the messages
                                messages.append({
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": tool_call.function.name,
                                    "content": result.content,
                                })
                    else:
                        logger.info("No tool calls were made by the model")

                    # Get the final response from the model
                    final_response = client.chat.completions.create(
                        model = AZURE_OPENAI_MODEL,
                        messages = messages,
                        tools = available_tools)

                    for item in final_response.choices:
                        print(item.message.content)
                except Exception as e:
                    logger.error(f"Error in conversation loop: {e}")
                    print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
```

The preceding code accomplishes the following tasks:

- Sets up logging and loads environment variables from a `.env` file.
- Configures Azure OpenAI client using `azure-identity` and `openai` libraries.
- Initializes an MCP client to interact with the Azure MCP Server using a standard I/O transport.
- Retrieves and displays a list of available tools from the MCP server.
- Implements a conversational loop to process user prompts, utilize tools, and handle tool calls.

Complete the following steps to test your.NET host app:

1. In a terminal window open to the root of your project, run the following command to start the app:
	```
	python main.py
	```
2. Once the app is running, enter the following test prompt:
	```
	List all of the resource groups in my subscription
	```
	The output for the previous prompt should resemble the following text:
	```
	The following resource groups are available for your subscription:
	1. **DefaultResourceGroup-EUS** (Location: \`eastus\`)
	2. **rg-testing** (Location: \`centralus\`)
	3. **rg-azd** (Location: \`eastus2\`)
	4. **msdocs-sample** (Location: \`southcentralus\`)
	14. **ai-testing** (Location: \`eastus2\`)
	Let me know if you need further details or actions related to any of these resource groups!
	```
3. Explore and test the Azure MCP operations using other relevant prompts, such as:
	```
	List all of the storage accounts in my subscription
	Get the available tables in my storage accounts
	```

[Learn more about Azure MCP Server tools](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/)

---

## Additional resources

Training

Module

[Integrate MCP Tools with Azure AI Agents - Training](https://learn.microsoft.com/en-us/training/modules/connect-agent-to-mcp-tools/?source=recommendations)

Enable dynamic tool access for your Azure AI agents. Learn how to connect MCP-hosted tools and integrate them seamlessly into agent workflows.

Certification

[Microsoft Certified: Azure Developer Associate - Certifications](https://learn.microsoft.com/en-us/credentials/certifications/azure-developer/?source=recommendations)

Build end-to-end solutions in Microsoft Azure to create Azure Functions, implement and manage web apps, develop solutions utilizing Azure storage, and more.