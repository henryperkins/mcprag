---
title: "Tutorial - React SPA with an API"
source: "https://developers.cloudflare.com/workers/vite-plugin/tutorial/"
author:
  - "[[Cloudflare Docs]]"
published: 2025-07-01
created: 2025-08-09
description: "Create a React SPA with an API Worker using the Vite plugin"
tags:
  - "clippings"
---
[Skip to content](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#_top)

This tutorial takes you through the steps needed to adapt a Vite project to use the Cloudflare Vite plugin. Much of the content can also be applied to adapting existing Vite projects and to front-end frameworks other than React.

## Introduction

In this tutorial, you will create a React SPA that can be deployed as a Worker with static assets. You will then add an API Worker that can be accessed from the front-end code. You will develop, build, and preview the application using Vite before finally deploying to Cloudflare.

Start by creating a React TypeScript project with Vite.

- [npm](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2565)
- [yarn](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2566)
- [pnpm](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2567)

```sh
npm create vite@latest -- cloudflare-vite-tutorial --template react-ts
```

Next, open the `cloudflare-vite-tutorial` directory in your editor of choice.

- [npm](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2568)
- [yarn](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2569)
- [pnpm](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2570)

```sh
npm i -D @cloudflare/vite-plugin wrangler
```

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig({
  plugins: [react(), cloudflare()],
});
```

The Cloudflare Vite plugin doesn't require any configuration by default and will look for a `wrangler.jsonc`, `wrangler.json` or `wrangler.toml` in the root of your application.

Refer to the [API reference](https://developers.cloudflare.com/workers/vite-plugin/reference/api/) for configuration options.

- [wrangler.jsonc](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2574)
- [wrangler.toml](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2575)

```jsonc
{
  "name": "cloudflare-vite-tutorial",
  "compatibility_date": "2025-04-03",
  "assets": {
    "not_found_handling": "single-page-application"
  }
}
```

The [`not_found_handling`](https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/) value has been set to `single-page-application`. This means that all not found requests will serve the `index.html` file. With the Cloudflare plugin, the `assets` routing configuration is used in place of Vite's default behavior. This ensures that your application's [routing configuration](https://developers.cloudflare.com/workers/static-assets/routing/) works the same way while developing as it does when deployed to production.

Note that the [`directory`](https://developers.cloudflare.com/workers/static-assets/binding/#directory) field is not used when configuring assets with Vite. The `directory` in the output configuration will automatically point to the client build output. See [Static Assets](https://developers.cloudflare.com/workers/vite-plugin/reference/static-assets/) for more information.

When developing Workers, additional files are used and/or generated that should not be stored in git. Add the following lines to your `.gitignore` file:

```txt
.wrangler
.dev.vars*
```

Run `npm run dev` to start the Vite development server and verify that your application is working as expected.

For a purely front-end application, you could now build (`npm run build`), preview (`npm run preview`), and deploy (`npm exec wrangler deploy`) your application. This tutorial, however, will show you how to go a step further and add an API Worker.

- [npm](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2571)
- [yarn](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2572)
- [pnpm](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2573)

```sh
npm i -D @cloudflare/workers-types
```

```jsonc
{
  "extends": "./tsconfig.node.json",
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.worker.tsbuildinfo",
    "types": ["@cloudflare/workers-types/2023-07-01", "vite/client"],
  },
  "include": ["worker"],
}
```

```jsonc
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" },
    { "path": "./tsconfig.worker.json" },
  ],
}
```

- [wrangler.jsonc](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2576)
- [wrangler.toml](https://developers.cloudflare.com/workers/vite-plugin/tutorial/#tab-panel-2577)

```jsonc
{
  "name": "cloudflare-vite-tutorial",
  "compatibility_date": "2025-04-03",
  "assets": {
    "not_found_handling": "single-page-application"
  },
  "main": "./worker/index.ts"
}
```

The `main` field specifies the entry file for your Worker code.

```ts
export default {
  fetch(request) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/")) {
      return Response.json({
        name: "Cloudflare",
      });
    }

    return new Response(null, { status: 404 });
  },
} satisfies ExportedHandler;
```

The Worker above will be invoked for any non-navigation request that does not match a static asset. It returns a JSON response if the `pathname` starts with `/api/` and otherwise return a `404` response.

Edit `src/App.tsx` so that it includes an additional button that calls the API and sets some state:

```tsx
import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";

function App() {
  const [count, setCount] = useState(0);
  const [name, setName] = useState("unknown");

  return (
    <>
16 collapsed lines
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button
          onClick={() => setCount((count) => count + 1)}
          aria-label="increment"
        >
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <div className="card">
        <button
          onClick={() => {
            fetch("/api/")
              .then((res) => res.json() as Promise<{ name: string }>)
              .then((data) => setName(data.name));
          }}
          aria-label="get name"
        >
          Name from API is: {name}
        </button>
        <p>
          Edit <code>api/index.ts</code> to change the name
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  );
}

export default App;
```

Now, if you click the button, it will display 'Name from API is: Cloudflare'.

Increment the counter to update the application state in the browser. Next, edit `api/index.ts` by changing the `name` it returns to `'Cloudflare Workers'`. If you click the button again, it will display the new `name` while preserving the previously set counter value.

With Vite and the Cloudflare plugin, you can iterate on the client and server parts of your app together, without losing UI state between edits.

Run `npm run build` to build your application.

```sh
npm run build
```

If you inspect the `dist` directory, you will see that it contains two subdirectories:

- `client` - the client code that runs in the browser
- `cloudflare-vite-tutorial` - the Worker code alongside the output `wrangler.json` configuration file

Run `npm run preview` to validate that your application runs as expected.

```sh
npm run preview
```

This command will run your build output locally in the Workers runtime, closely matching its behaviour in production.

Run `npm exec wrangler deploy` to deploy your application to Cloudflare.

```sh
npm exec wrangler deploy
```

This command will automatically use the output `wrangler.json` that was included in the build output.

In this tutorial, we created an SPA that could be deployed as a Worker with static assets. We then added an API Worker that could be accessed from the front-end code. Finally, we deployed both the client and server-side parts of the application to Cloudflare.

Possible next steps include:

- Adding a binding to another Cloudflare service such as a [KV namespace](https://developers.cloudflare.com/kv/) or [D1 database](https://developers.cloudflare.com/d1/)
- Expanding the API to include additional routes
- Using a library, such as [Hono ↗](https://hono.dev/) or [tRPC ↗](https://trpc.io/), in your API Worker