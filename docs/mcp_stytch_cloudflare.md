## Create a remote MCP server with Stytch authentication on Cloudflare

In this guide, we'll walk through the creation of a Remote Model Context Protocol (MCP) server which manages authentication as a Stytch Connected App. We will be examining a simple application that manages a list of tasks (TODO app) ([GitHub project](https://github.com/stytchauth/mcp-stytch-consumer-todo-list)). The TODO app has a web browser client that communicates to the server via an HTTP API. Additionally, the server implements the MCP protocol to become accessible to an MCP-compliant Large Language Model (LLM) AI client (for example Anthropic's [Claude](https://claude.ai/)), allowing us to compare and contrast the approach taken for each implementation. This app can be run locally and can also be deployed as a Cloudflare Worker, but the basic concepts we'll cover here generalize to any cloud platform.

## Before you start

In order to complete this guide, you'll need:

- A Stytch project. In the [Stytch Dashboard](https://stytch.com/dashboard?env=test), click on your existing project name at the top of the Dashboard, click "Create project", and select "Consumer Authentication".
- The [MCP Inspector](https://github.com/modelcontextprotocol/inspector). This is a tool that will help us ensure that our MCP server is exposing the correct interface, is running properly, and allows us to explore the features of the MCP protocol in a web-based tool.

###

1

Configure Stytch for our example app

Navigate to "Project Settings" to note your "Project ID" and "Public token". You will need these values later.

![Project ID and Public token](https://static.stytch.com/docs/_next/static/media/project-id-public-token-b2c-dark.e3224258.png)

Navigate to "Frontend SDKs" to enable the Frontend SDK for http://localhost:3000

![Authorized frontend applications for SDK use](https://static.stytch.com/docs/_next/static/media/authorized-frontend-applications-b2c-dark.1c057d2b.png)

Navigate to "Connected Apps" and enable "Allow dynamic client registration". [Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591) is a protocol that allows applications to register themselves with Stytch as a Connected App client. We will dive more into how Dynamic Client Registration works [later in this guide](https://stytch.com/docs/guides/connected-apps/mcp-servers#learn-how-authentication-with-stytch-is-implemented).

![Allow dynamic client registration](https://static.stytch.com/docs/_next/static/media/allow-dynamic-client-b2c-dark.d760bae6.png)

###

2

Clone the GitHub repository for this guide

The companion repository for this guide is located [in GitHub](https://github.com/stytchauth/mcp-stytch-consumer-todo-list). Go to that repository, clone it, and follow the README to get the TODO app up and running on your local machine.

Once you have the example up and running, explore its functionality and start to get a sense of how the app is structured, then return here for a tour of the app's implementation.

###

3

Examine how the HTTP client and server implementations are built

The app exposes a straightforward REST API that implements state management and access control. This API (which can be examined at [/api/TodoAPI.ts](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/TodoAPI.ts)) exposes methods to create, read, update, and delete TODO items. State management and persistence are eventually handled by the [/api/TodoService.ts](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/TodoService.ts) class which manages the app's data in the data store.

The browser frontend includes React components that work together to render the app. In [/src/Todos.tsx](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/src/Todos.tsx), the frontend makes requests to the backend API to change the state of our data.

Take a moment to read the source code, run the app, and interact with the app's state to get a feel for how data is being modeled and what operations are valid.

###

4

Learn how the MCP server is defined

The [MCP Core architecture documentation](https://modelcontextprotocol.io/docs/concepts/architecture) is a good reference for understanding how an MCP server is implemented. Below is a brief summary of relevant concepts.

MCP servers use a protocol based on JSON-RPC 2.0 for message passing between the remote MCP server (what we're building) and the client, which is the LLM that is integrating with the server. The RPC protocol uses POST requests and Server-Sent Events to pass messages back and forth between the server and client. There are a few core primitives (Resources, Prompts, Tools, etc...) defined by the MCP specification that describe the schema of the messages in this protocol and what behaviors can be expected.

This is a structurally different protocol than vanilla HTTP requests, so implementing a Remote MCP server is more nuanced than a typical HTTP request/response flow. Thankfully there are libraries to assist in implementing MCP servers. Our example uses [@modelcontextprotocol/sdk](https://www.npmjs.com/package/@modelcontextprotocol/sdk) to handle the specifics of conforming with the MCP protocol.

In [/api/TodoMCP.ts](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/TodoMCP.ts), you can follow along as the McpServer class defines the resources and tools that are exposed through the MCP protocol. Note that, just as in the HTTP implementation, the MCP server uses the same TodoService class to handle application state.

The details of how exactly an MCP server defines its components are implementation-dependent, but for the purposes of this walkthrough the key concept is that MCP defines a protocol for our server to implement in order to establish communications with an LLM client. This protocol can coexist with an HTTP server or stand on its own, but the fundamentals of establishing authentication and access control are similar for each.

We'll dive more deeply into how authentication is implemented in the next step.

###

5

Learn how authentication with Stytch is implemented

### Dynamic Client Registration

[Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591) is an OAuth standard for allowing a client to automatically register itself with an Identity Provider (IdP) server and is included as part of the Remote MCP protocol.

The first time the MCP Inspector attempts to access our TODO app it will receive a 401 Unauthorized response. This will cause the MCP Inspector to fetch metadata about our server. In [/api/index.ts](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/index.ts) the TODO app creates a route at /.well-known/oauth-authorization-server which returns metadata about the OAuth server (as covered in the [Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414) standard).

Once the MCP Inspector has fetched the metadata from our TODO app Stytch and the MCP Inspector will handle the rest of the Dynamic Client Registration process to create a new [Connected Apps](https://stytch.com/docs/b2b/guides/connected-apps/getting-started) client.

### Connected Apps authorization

All dynamically registered clients are [Third Party Public](https://stytch.com/docs/guides/connected-apps/client-types) apps and will show up in the Stytch Dashboard when registration is complete.

![MCP Inspector has registered as a Connected Apps client](https://static.stytch.com/docs/_next/static/media/mcp-inspector-connected-app-client-b2c-dark.936e3073.png)

Now that the MCP Inspector is registered as a client app the flow continues through the standard Connected Apps authorization process. As the MCP Inspector is a "Third Party" app, this includes showing an access request dialog for the user to allow the MCP Inspector to access data in our app. Upon completion of this flow the MCP inspector should show a successful connection and allow access to the data managed by our TODO app.

### Client-side authentication

In the web client, the app wraps components in a [parent component](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/src/Todos.tsx#L29) that enforces authentication. This component verifies that there is a current Stytch user logged in before rendering its child component. If no user is logged in, it redirects to the login page.

### Server-side authentication

On the server side, authentication is handled slightly differently depending on whether the REST API or the MCP protocol are being used.

For the REST API, [Hono middleware](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/lib/auth.ts#L10) is used to grab the Stytch session cookie and check its validity. This middleware is used on each route in [/api/TodoAPI.ts](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/TodoAPI.ts). As each operation happens within the context of a single API request, wrapping each request in the middleware will enforce the validity of each operation.

Similarly, when the connection to the MCP server is first established, again using Hono middleware, the server [saves the credentials](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/lib/auth.ts#L46) from the request into properties that will be accessible to the MCP server. These credentials are used when [constructing the TodoService](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/TodoMCP.ts#L16) class.

### Authorization

Rather than implementing specific authorization logic, for both the HTTP and the MCP server the TodoService class implements a very basic authorization scheme by namespacing the list of TODOs [by the user's ID](https://github.com/stytchauth/mcp-stytch-consumer-todo-list/blob/main/api/TodoService.ts#L16) to keep each user's data private to that user.

If you would be interested to see how to implement more nuanced authorization rules with a Stytch B2C project, read [this guide](https://stytch.com/docs/guides/authorization/rbac) on how this can be achieved with Stytch metadata. Additionally, a more robust authentication implementation with Stytch Role-Based Access Control can be found in our [B2B MCP Server example app](https://stytch.com/docs/b2b/guides/connected-apps/mcp-servers).

###

6

Deploying to Cloudflare

The GitHub README covers the steps necessary to deploy the app as a Cloudflare Worker. After the deploy, be sure to note that the location of the server will have changed, which requires additional configuration in Stytch. Once you have the URL for your Cloudflare Worker, repeat the process in [Step 1](https://stytch.com/docs/guides/connected-apps/mcp-servers#configure-stytch-for-our-example-app) to add this URL as an "Authorized Application" in the "Frontend SDK" settings.

## What's next

- View our guide on our [B2B MCP Server example app](https://stytch.com/docs/b2b/guides/connected-apps/mcp-servers) to see a similar app using B2B Authentication with OAuth scopes and Role-Based Access Control
- Familiarize yourself with [Stytch's SDKs](https://stytch.com/docs/sdks) for a deeper dive on how to integrate your MCP server with Stytch.
- Browse the [Model Context Protocol](https://modelcontextprotocol.io/introduction) documentation for more information about Remote MCP Servers.
