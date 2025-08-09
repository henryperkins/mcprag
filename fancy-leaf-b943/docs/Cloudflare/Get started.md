---
title: "Get started"
source: "https://developers.cloudflare.com/workers/vite-plugin/get-started/"
author:
  - "[[Cloudflare Docs]]"
published: 2025-06-05
created: 2025-08-09
description: "Get started with the Vite plugin"
tags:
  - "clippings"
---
[Skip to content](https://developers.cloudflare.com/workers/vite-plugin/get-started/#_top)

```json
{
  "name": "cloudflare-vite-get-started",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "npm run build && vite preview",
    "deploy": "npm run build && wrangler deploy"
  }
}
```

- [npm](https://developers.cloudflare.com/workers/vite-plugin/get-started/#tab-panel-2560)
- [yarn](https://developers.cloudflare.com/workers/vite-plugin/get-started/#tab-panel-2561)
- [pnpm](https://developers.cloudflare.com/workers/vite-plugin/get-started/#tab-panel-2562)

```sh
npm i -D vite @cloudflare/vite-plugin wrangler
```

```ts
import { defineConfig } from "vite";
import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig({
  plugins: [cloudflare()],
});
```

The Cloudflare Vite plugin doesn't require any configuration by default and will look for a `wrangler.jsonc`, `wrangler.json` or `wrangler.toml` in the root of your application.

Refer to the [API reference](https://developers.cloudflare.com/workers/vite-plugin/reference/api/) for configuration options.

- [wrangler.jsonc](https://developers.cloudflare.com/workers/vite-plugin/get-started/#tab-panel-2563)
- [wrangler.toml](https://developers.cloudflare.com/workers/vite-plugin/get-started/#tab-panel-2564)

```jsonc
{
  "name": "cloudflare-vite-get-started",
  "compatibility_date": "2025-04-03",
  "main": "./src/index.ts"
}
```

The `name` field specifies the name of your Worker. By default, this is also used as the name of the Worker's Vite Environment (see [Vite Environments](https://developers.cloudflare.com/workers/vite-plugin/reference/vite-environments/) for more information). The `main` field specifies the entry file for your Worker code.

For more information about the Worker configuration, see [Configuration](https://developers.cloudflare.com/workers/wrangler/configuration/).

```ts
export default {
  fetch() {
  },
};
```

A request to this Worker will return **'Running in Cloudflare-Workers!'**, demonstrating that the code is running inside the Workers runtime.

You can now start the Vite development server (`npm run dev`), build the application (`npm run build`), preview the built application (`npm run preview`), and deploy to Cloudflare (`npm run deploy`).