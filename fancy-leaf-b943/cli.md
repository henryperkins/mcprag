[Skip to content](https://developers.cloudflare.com/workers/wrangler/commands/#_top)

Wrangler offers a number of commands to manage your Cloudflare Workers.

- [`docs`](https://developers.cloudflare.com/workers/wrangler/commands/#docs) - Open this page in your default browser.
- [`init`](https://developers.cloudflare.com/workers/wrangler/commands/#init) - Create a new project from a variety of web frameworks and templates.
- [`containers`](https://developers.cloudflare.com/workers/wrangler/commands/#containers) - Interact with Containers.
- [`d1`](https://developers.cloudflare.com/workers/wrangler/commands/#d1) - Interact with D1.
- [`vectorize`](https://developers.cloudflare.com/workers/wrangler/commands/#vectorize) - Interact with Vectorize indexes.
- [`hyperdrive`](https://developers.cloudflare.com/workers/wrangler/commands/#hyperdrive) - Manage your Hyperdrives.
- [`deploy`](https://developers.cloudflare.com/workers/wrangler/commands/#deploy) - Deploy your Worker to Cloudflare.
- [`dev`](https://developers.cloudflare.com/workers/wrangler/commands/#dev) - Start a local server for developing your Worker.
- [`delete`](https://developers.cloudflare.com/workers/wrangler/commands/#delete-1) - Delete your Worker from Cloudflare.
- [`kv namespace`](https://developers.cloudflare.com/workers/wrangler/commands/#kv-namespace) - Manage Workers KV namespaces.
- [`kv key`](https://developers.cloudflare.com/workers/wrangler/commands/#kv-key) - Manage key-value pairs within a Workers KV namespace.
- [`kv bulk`](https://developers.cloudflare.com/workers/wrangler/commands/#kv-bulk) - Manage multiple key-value pairs within a Workers KV namespace in batches.
- [`r2 bucket`](https://developers.cloudflare.com/workers/wrangler/commands/#r2-bucket) - Manage Workers R2 buckets.
- [`r2 object`](https://developers.cloudflare.com/workers/wrangler/commands/#r2-object) - Manage Workers R2 objects.
- [`secret`](https://developers.cloudflare.com/workers/wrangler/commands/#secret) - Manage the secret variables for a Worker.
- [`secret bulk`](https://developers.cloudflare.com/workers/wrangler/commands/#secret-bulk) - Manage multiple secret variables for a Worker.
- [`secrets-store secret`](https://developers.cloudflare.com/workers/wrangler/commands/#secrets-store-secret) - Manage account secrets within a secrets store.
- [`secrets-store store`](https://developers.cloudflare.com/workers/wrangler/commands/#secrets-store-store) - Manage your store within secrets store.
- [`workflows`](https://developers.cloudflare.com/workers/wrangler/commands/#workflows) - Manage and configure Workflows.
- [`tail`](https://developers.cloudflare.com/workers/wrangler/commands/#tail) - Start a session to livestream logs from a deployed Worker.
- [`pages`](https://developers.cloudflare.com/workers/wrangler/commands/#pages) - Configure Cloudflare Pages.
- [`pipelines`](https://developers.cloudflare.com/workers/wrangler/commands/#pipelines) - Configure Cloudflare Pipelines.
- [`queues`](https://developers.cloudflare.com/workers/wrangler/commands/#queues) - Configure Workers Queues.
- [`login`](https://developers.cloudflare.com/workers/wrangler/commands/#login) - Authorize Wrangler with your Cloudflare account using OAuth.
- [`logout`](https://developers.cloudflare.com/workers/wrangler/commands/#logout) - Remove Wrangler’s authorization for accessing your account.
- [`whoami`](https://developers.cloudflare.com/workers/wrangler/commands/#whoami) - Retrieve your user information and test your authentication configuration.
- [`versions`](https://developers.cloudflare.com/workers/wrangler/commands/#versions) - Retrieve details for recent versions.
- [`deployments`](https://developers.cloudflare.com/workers/wrangler/commands/#deployments) - Retrieve details for recent deployments.
- [`rollback`](https://developers.cloudflare.com/workers/wrangler/commands/#rollback) - Rollback to a recent deployment.
- [`dispatch-namespace`](https://developers.cloudflare.com/workers/wrangler/commands/#dispatch-namespace) - Interact with a [dispatch namespace](https://developers.cloudflare.com/cloudflare-for-platforms/workers-for-platforms/reference/how-workers-for-platforms-works/#dispatch-namespace).
- [`mtls-certificate`](https://developers.cloudflare.com/workers/wrangler/commands/#mtls-certificate) - Manage certificates used for mTLS connections.
- [`cert`](https://developers.cloudflare.com/workers/wrangler/commands/#cert) - Manage certificates used for mTLS and Certificate Authority (CA) chain connections.
- [`types`](https://developers.cloudflare.com/workers/wrangler/commands/#types) - Generate types from bindings and module rules in configuration.
- [`telemetry`](https://developers.cloudflare.com/workers/wrangler/commands/#telemetry) - Configure whether Wrangler can collect anonymous usage data.
- [`check`](https://developers.cloudflare.com/workers/wrangler/commands/#check) - Validate your Worker.

---

This page provides a reference for Wrangler commands.

```txt
wrangler <COMMAND> <SUBCOMMAND> [PARAMETERS] [OPTIONS]
```

Since Cloudflare recommends [installing Wrangler locally](https://developers.cloudflare.com/workers/wrangler/install-and-update/) in your project(rather than globally), the way to run Wrangler will depend on your specific setup and package manager.

- [npm](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2596)
- [yarn](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2597)
- [pnpm](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2598)

```sh
npx wrangler <COMMAND> <SUBCOMMAND> [PARAMETERS] [OPTIONS]
```

You can add Wrangler commands that you use often as scripts in your project's `package.json` file:

```json
{
  ...
  "scripts": {
    "deploy": "wrangler deploy",
    "dev": "wrangler dev"
  }
  ...
}
```

You can then run them using your package manager of choice:

- [npm](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2599)
- [yarn](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2600)
- [pnpm](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2601)

```sh
npm run deploy
```

---

## docs

Open the Cloudflare developer documentation in your default browser.

```txt
wrangler docs [<COMMAND>]
```

- `COMMAND` string optional
	- The Wrangler command you want to learn more about. This opens your default browser to the section of the documentation that describes the command.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

## init

Create a new project via the [create-cloudflare-cli (C3) tool](https://developers.cloudflare.com/workers/get-started/guide/#1-create-a-new-worker-project). A variety of web frameworks are available to choose from as well as templates. Dependencies are installed by default, with the option to deploy your project immediately.

```txt
wrangler init [<NAME>] [OPTIONS]
```

- `NAME` string optional (default: name of working directory)
	- The name of the Workers project. This is both the directory name and `name` property in the generated [Wrangler configuration](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--yes` boolean optional
	- Answer yes to any prompts for new projects.
- `--from-dash` string optional
	- Fetch a Worker initialized from the dashboard. This is done by passing the flag and the Worker name. `wrangler init --from-dash <WORKER_NAME>`.
	- The `--from-dash` command will not automatically sync changes made to the dashboard after the command is used. Therefore, it is recommended that you continue using the CLI.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## containers

Interact with Cloudflare's Container Platform.

### build

Build a Container image from a Dockerfile.

```txt
wrangler containers build [PATH] [OPTIONS]
```

- `PATH` string optional
	- Path for the directory containing the Dockerfile to build.

#### Options:

- `-t, --tag` string required
	- Name and optionally a tag (format: "name:tag").
- `--path-to-docker` string optional
	- Path to your docker binary if it's not on $PATH.
	- Default: "docker"
- `-p, --push` boolean optional
	- Push the built image to Cloudflare's managed registry.
	- Default: false
- `--platform` string optional
	- Platform to build for. Defaults to the architecture supported by Workers (linux/amd64).
	- Default: "linux/amd64"
- `--json` boolean optional
	- Return output as clean JSON.
	- Default: false

### delete

Delete a Container (application).

```txt
wrangler containers delete <CONTAINER_ID> [OPTIONS]
```

- `CONTAINER_ID` string required
	- The ID of the Container to delete.
- `-y, --skip-confirmation` boolean optional
	- Skip deletion confirmation prompt.
- `--json` boolean optional
	- Return output as JSON rather than a table.

### images

Perform operations on images in your containers registry.

#### images list

List images in your containers registry.

```txt
wrangler containers images list [OPTIONS]
```

#### Options:

- `--filter` string optional
	- Regex to filter results.
- `--json` boolean optional
	- Return output as clean JSON.
	- Default: false

#### images delete

Remove an image from your containers registry.

```txt
wrangler containers images delete [IMAGE] [OPTIONS]
```

- `IMAGE` string required
	- Image to delete.

#### Options:

- `--json` boolean optional
	- Return output as clean JSON.
	- Default: false

### info

Get information about a specific Container, including top-level details and a list of instances.

```txt
wrangler containers info <CONTAINER_ID> [OPTIONS]
```

- `CONTAINER_ID` string required
	- The ID of the Container to get information about.
- `--json` boolean optional
	- Return output as JSON rather than a table.

### list

List the Containers in your account.

```txt
wrangler containers list [OPTIONS]
```

- `--json` boolean optional
	- Return output as JSON rather than a table.

### push

Push a tagged image to a Cloudflare managed registry, which is automatically integrated with your account.

```txt
wrangler containers push [TAG] [OPTIONS]
```

- `TAG` string required
	- The name and tag of the container image to push.

#### Options:

- `--path-to-docker` string optional
	- Path to your docker binary if it's not on $PATH.
	- Default: "docker"
- `--json` boolean optional
	- Return output as clean JSON.
	- Default: false

## d1

Interact with Cloudflare's D1 service.

### create

Creates a new D1 database, and provides the binding and UUID that you will put in your Wrangler file.

```txt
wrangler d1 create <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the new D1 database.
- `--location` string optional
	- Provide an optional [location hint](https://developers.cloudflare.com/d1/configuration/data-location/) for your database leader.
	- Available options include `weur` (Western Europe), `eeur` (Eastern Europe), `apac` (Asia Pacific), `oc` (Oceania), `wnam` (Western North America), and `enam` (Eastern North America).

### info

Get information about a D1 database, including the current database size and state.

```txt
wrangler d1 info <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database to get information about.
- `--json` boolean optional
	- Return output as JSON rather than a table.

### list

List all D1 databases in your account.

```txt
wrangler d1 list [OPTIONS]
```

- `--json` boolean optional
	- Return output as JSON rather than a table.

### delete

Delete a D1 database.

```txt
wrangler d1 delete <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database to delete.
- `-y, --skip-confirmation` boolean optional
	- Skip deletion confirmation prompt.

### execute

Execute a query on a D1 database.

```txt
wrangler d1 execute <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database to execute a query on.
- `--command` string optional
	- The SQL query you wish to execute.
- `--file` string optional
	- Path to the SQL file you wish to execute.
- `-y, --yes` boolean optional
	- Answer `yes` to any prompts.
- `--local` boolean (default: true) optional
	- Execute commands/files against a local database for use with [wrangler dev](https://developers.cloudflare.com/workers/wrangler/commands/#dev).
- `--remote` boolean (default: false) optional
	- Execute commands/files against a remote D1 database for use with [wrangler dev --remote](https://developers.cloudflare.com/workers/wrangler/commands/#dev).
- `--persist-to` string optional
	- Specify directory to use for local persistence (for use in combination with `--local`).
- `--json` boolean optional
	- Return output as JSON rather than a table.
- `--preview` boolean optional
	- Execute commands/files against a preview D1 database (as defined by `preview_database_id` in the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/#d1-databases)).

### export

Export a D1 database or table's schema and/or content to a `.sql` file.

```txt
wrangler d1 export <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database to export.
- `--local` boolean (default: true) optional
	- Export from a local database for use with [wrangler dev](https://developers.cloudflare.com/workers/wrangler/commands/#dev).
- `--remote` boolean (default: false) optional
	- Export from a remote D1 database for use with [wrangler dev --remote](https://developers.cloudflare.com/workers/wrangler/commands/#dev).
- `--output` string required
	- Path to the SQL file for your export.
- `--table` string optional
	- The name of the table within a D1 database to export.
- `--no-data` boolean (default: false) optional
	- Controls whether export SQL file contains database data. Note that `--no-data=true` is not recommended due to a known wrangler limitation that intreprets the value as false.
- `--no-schema` boolean (default: false) optional
	- Controls whether export SQL file contains database schema. Note that `--no-schema=true` is not recommended due to a known wrangler limitation that intreprets the value as false.

### time-travel restore

Restore a database to a specific point-in-time using [Time Travel](https://developers.cloudflare.com/d1/reference/time-travel/).

```txt
wrangler d1 time-travel restore <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database to execute a query on.
- `--bookmark` string optional
	- A D1 bookmark representing the state of a database at a specific point in time.
- `--timestamp` string optional
	- A UNIX timestamp or JavaScript date-time `string` within the last 30 days.
- `--json` boolean optional
	- Return output as JSON rather than a table.

### time-travel info

Inspect the current state of a database for a specific point-in-time using [Time Travel](https://developers.cloudflare.com/d1/reference/time-travel/).

```txt
wrangler d1 time-travel info <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database to execute a query on.
- `--timestamp` string optional
	- A UNIX timestamp or JavaScript date-time `string` within the last 30 days.
- `--json` b boolean optional
	- Return output as JSON rather than a table.

### migrations create

Create a new migration.

This will generate a new versioned file inside the `migrations` folder. Name your migration file as a description of your change. This will make it easier for you to find your migration in the `migrations` folder. An example filename looks like:

`0000_create_user_table.sql`

The filename will include a version number and the migration name you specify below.

```txt
wrangler d1 migrations create <DATABASE_NAME> <MIGRATION_NAME>
```

- `DATABASE_NAME` string required
	- The name of the D1 database you wish to create a migration for.
- `MIGRATION_NAME` string required
	- A descriptive name for the migration you wish to create.

### migrations list

View a list of unapplied migration files.

```txt
wrangler d1 migrations list <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database you wish to list unapplied migrations for.
- `--local` boolean optional
	- Show the list of unapplied migration files on your locally persisted D1 database.
- `--remote` boolean (default: false) optional
	- Show the list of unapplied migration files on your remote D1 database.
- `--persist-to` string optional
	- Specify directory to use for local persistence (for use in combination with `--local`).
- `--preview` boolean optional
	- Show the list of unapplied migration files on your preview D1 database (as defined by `preview_database_id` in the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/#d1-databases)).

### migrations apply

Apply any unapplied migrations.

This command will prompt you to confirm the migrations you are about to apply. Confirm that you would like to proceed. After, a backup will be captured.

The progress of each migration will be printed in the console.

When running the apply command in a CI/CD environment or another non-interactive command line, the confirmation step will be skipped, but the backup will still be captured.

If applying a migration results in an error, this migration will be rolled back, and the previous successful migration will remain applied.

```txt
wrangler d1 migrations apply <DATABASE_NAME> [OPTIONS]
```

- `DATABASE_NAME` string required
	- The name of the D1 database you wish to apply your migrations on.
- `--env` string optional
	- Specify which environment configuration to use for D1 binding
- `--local` boolean (default: true) optional
	- Execute any unapplied migrations on your locally persisted D1 database.
- `--remote` boolean (default: false) optional
	- Execute any unapplied migrations on your remote D1 database.
- `--persist-to` string optional
	- Specify directory to use for local persistence (for use in combination with `--local`).
- `--preview` boolean optional
	- Execute any unapplied migrations on your preview D1 database (as defined by `preview_database_id` in the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/#d1-databases)).

---

## hyperdrive

Manage [Hyperdrive](https://developers.cloudflare.com/hyperdrive/) database configurations.

### create

Create a new Hyperdrive configuration.

```txt
wrangler hyperdrive create <CONFIG_NAME> [OPTIONS]
```

- `CONFIG_NAME` string required
	- The name of the Hyperdrive configuration to create.
- `--connection-string` string optional
	- The database connection string in the form `postgres://user:password@hostname:port/database`.
- `--origin-host` string optional
	- The hostname or IP address Hyperdrive should connect to.
- `--origin-port` number optional
	- The database port to connect to.
- `--origin-scheme` string optional
	- The scheme used to connect to the origin database, for example, postgresql or postgres.
- `--database` string optional
	- The database (name) to connect to. For example, Postgres or defaultdb.
- `--origin-user` string optional
	- The username used to authenticate to the database.
- `--origin-password` string optional
	- The password used to authenticate to the database.
- `--access-client-id` string optional
	- The Client ID of the Access token to use when connecting to the origin database, must be set with a Client Access Secret. Mutually exclusive with `origin-port`.
- `--access-client-secret` string optional
	- The Client Secret of the Access token to use when connecting to the origin database, must be set with a Client Access ID. Mutually exclusive with `origin-port`.
- `--caching-disabled` boolean optional
	- Disables the caching of SQL responses.
- `--max-age` number optional
	- Specifies max duration for which items should persist in the cache, cannot be set when caching is disabled.
- `--swr` number optional
	- Stale While Revalidate - Indicates the number of seconds cache may serve the response after it becomes stale, cannot be set when caching is disabled.
- `--ca-certificate-id` string optional
	- Sets custom CA certificate when connecting to origin database.
- `--mtls-certificate-id` string optional
	- Sets custom mTLS client certificates when connecting to origin database.
- `--sslmode` string optional
	- Sets SSL mode for CA verification. Must be `require` | `verify-ca` | `verify-full`.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### update

Update an existing Hyperdrive configuration.

```txt
wrangler hyperdrive update <ID> [OPTIONS]
```

- `ID` string required
	- The ID of the Hyperdrive configuration to update.
- `--name` string optional
	- The new name of the Hyperdrive configuration.
- `--connection-string` string optional
	- The database connection string in the form `postgres://user:password@hostname:port/database`.
- `--origin-host` string optional
	- The new database hostname or IP address Hyperdrive should connect to.
- `--origin-port` string optional
	- The new database port to connect to.
- `--origin-scheme` string optional
	- The scheme used to connect to the origin database, for example, postgresql or postgres.
- `--database` string optional
	- The new database (name) to connect to. For example, Postgres or defaultdb.
- `--origin-user` string optional
	- The new username used to authenticate to the database.
- `--origin-password` string optional
	- The new password used to authenticate to the database.
- `--access-client-id` string optional
	- The Client ID of the Access token to use when connecting to the origin database, must be set with a Client Access Secret. Mutually exclusive with `origin-port`.
- `--access-client-secret` string optional
	- The Client Secret of the Access token to use when connecting to the origin database, must be set with a Client Access ID. Mutually exclusive with `origin-port`.
- `--caching-disabled` boolean optional
	- Disables the caching of SQL responses.
- `--max-age` number optional
	- Specifies max duration for which items should persist in the cache, cannot be set when caching is disabled.
- `--swr` number optional
	- Stale While Revalidate - Indicates the number of seconds cache may serve the response after it becomes stale, cannot be set when caching is disabled.
- `--ca-certificate-id` string optional
	- Sets custom CA certificate when connecting to origin database.
- `--mtls-certificate-id` string optional
	- Sets custom mTLS client certificates when connecting to origin database.
- `--sslmode` string optional
	- Sets SSL mode for CA verification. Must be `require` | `verify-ca` | `verify-full`.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### list

List all Hyperdrive configurations.

```txt
wrangler hyperdrive list
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### delete

Delete an existing Hyperdrive configuration.

```txt
wrangler hyperdrive delete <ID>
```

- `ID` string required
	- The name of the Hyperdrive configuration to delete.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### get

Get an existing Hyperdrive configuration.

```txt
wrangler hyperdrive get <ID>
```

- `ID` string required
	- The name of the Hyperdrive configuration to get.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## vectorize

Interact with a [Vectorize](https://developers.cloudflare.com/vectorize/) vector database.

### create

Creates a new vector index, and provides the binding and name that you will put in your Wrangler file.

```sh
npx wrangler vectorize create <INDEX_NAME> [--dimensions=<NUM_DIMENSIONS>] [--metric=<DISTANCE_METRIC>] [--description=<DESCRIPTION>]
```

- `INDEX_NAME` string required
	- The name of the new index to create. Must be unique for an account and cannot be changed after creation.
- `--dimensions` number required
	- The vector dimension width to configure the index for. Cannot be changed after creation.
- `--metric` string required
	- The distance metric to use for calculating vector distance. Must be one of `cosine`, `euclidean`, or `dot-product`.
- `--description` string optional
	- A description for your index.
- `--deprecated-v1` boolean optional
	- Create a legacy Vectorize index. Please note that legacy Vectorize indexes are on a [deprecation path](https://developers.cloudflare.com/vectorize/reference/transition-vectorize-legacy).

### list

List all Vectorize indexes in your account, including the configured dimensions and distance metric.

```sh
npx wrangler vectorize list
```

- `--deprecated-v1` boolean optional
	- List legacy Vectorize indexes. Please note that legacy Vectorize indexes are on a [deprecation path](https://developers.cloudflare.com/vectorize/reference/transition-vectorize-legacy).

### get

Get details about an individual index, including its configuration.

```sh
npx wrangler vectorize get <INDEX_NAME>
```

- `INDEX_NAME` string required
	- The name of the index to fetch details for.
- `--deprecated-v1` boolean optional
	- Get a legacy Vectorize index. Please note that legacy Vectorize indexes are on a [deprecation path](https://developers.cloudflare.com/vectorize/reference/transition-vectorize-legacy).

### info

Get some additional information about an individual index, including the vector count and details about the last processed mutation.

```sh
npx wrangler vectorize info <INDEX_NAME>
```

- `INDEX_NAME` string required
	- The name of the index to fetch details for.

### delete

Delete a Vectorize index.

```sh
npx wrangler vectorize delete <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index to delete.
- `--force` boolean optional
	- Skip confirmation when deleting the index (Note: This is not a recoverable operation).
- `--deprecated-v1` boolean optional
	- Delete a legacy Vectorize index. Please note that legacy Vectorize indexes are on a [deprecation path](https://developers.cloudflare.com/vectorize/reference/transition-vectorize-legacy).

### insert

Insert vectors into an index.

```sh
npx wrangler vectorize insert <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index to upsert vectors in.
- `--file` string required
	- A file containing the vectors to insert in newline-delimited JSON (JSON) format.
- `--batch-size` number optional
	- The number of vectors to insert at a time (default: `1000`).
- `--deprecated-v1` boolean optional
	- Insert into a legacy Vectorize index. Please note that legacy Vectorize indexes are on a [deprecation path](https://developers.cloudflare.com/vectorize/reference/transition-vectorize-legacy).

### upsert

Upsert vectors into an index. Existing vectors in the index would be overwritten.

```sh
npx wrangler vectorize upsert <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index to upsert vectors in.
- `--file` string required
	- A file containing the vectors to insert in newline-delimited JSON (JSON) format.
- `--batch-size` number optional
	- The number of vectors to insert at a time (default: `5000`).

### query

Query a Vectorize index for similar vectors.

```sh
npx wrangler vectorize query <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index to query.
- `--vector` array optional
	- Vector against which the Vectorize index is queried. Either this or the `vector-id` param must be provided.
- `--vector-id` string optional
	- Identifier for a vector that is already present in the index against which the index is queried. Either this or the `vector` param must be provided.
- `--top-k` number optional
	- The number of vectors to query (default: `5`).
- `--return-values` boolean optional
	- Enable to return vector values in the response (default: `false`).
- `--return-metadata` string optional
	- Enable to return vector metadata in the response. Must be one of `none`, `indexed`, or `all` (default: `none`).
- `--namespace` string optional
	- Query response to only include vectors from this namespace.
- `--filter` string optional
	- Filter vectors based on this metadata filter. Example: `'{ 'p1': 'abc', 'p2': { '$ne': true }, 'p3': 10, 'p4': false, 'nested.p5': 'abcd' }'`

### get-vectors

Fetch vectors from a Vectorize index using the provided ids.

```sh
npx wrangler vectorize get-vectors <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index from which vectors need to be fetched.
- `--ids` array required
	- List of ids for which vectors must be fetched.

### delete-vectors

Delete vectors in a Vectorize index using the provided ids.

```sh
npx wrangler vectorize delete-vectors <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index from which vectors need to be deleted.
- `--ids` array required
	- List of ids corresponding to the vectors that must be deleted.

Enable metadata filtering on the specified property.

```sh
npx wrangler vectorize create-metadata-index <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index for which metadata index needs to be created.
- `--property-name` string required
	- Metadata property for which metadata filtering should be enabled.
- `--type` string required
	- Data type of the property. Must be one of `string`, `number`, or `boolean`.

List metadata properties on which metadata filtering is enabled.

```sh
npx wrangler vectorize list-metadata-index <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index for which metadata indexes needs to be fetched.

Disable metadata filtering on the specified property.

```sh
npx wrangler vectorize delete-metadata-index <INDEX_NAME> [OPTIONS]
```

- `INDEX_NAME` string required
	- The name of the Vectorize index for which metadata index needs to be disabled.
- `--property-name` string required
	- Metadata property for which metadata filtering should be disabled.

---

## dev

Start a local server for developing your Worker.

```txt
wrangler dev [<SCRIPT>] [OPTIONS]
```

- `SCRIPT` string
	- The path to an entry point for your Worker. Only required if your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/) does not include a `main` key (for example, `main = "index.js"`).
- `--name` string optional
	- Name of the Worker.
- `--config`, `-c` string\[\] optional
	- Path(s) to [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/). If not provided, Wrangler will use the nearest config file based on your current working directory.
	- You can provide multiple configuration files to run multiple Workers in one dev session like this: `wrangler dev -c ./wrangler.toml -c ../other-worker/wrangler.toml`. The first config will be treated as the *primary* Worker, which will be exposed over HTTP. The remaining config files will only be accessible via a service binding from the primary Worker.
- `--no-bundle` boolean (default: false) optional
	- Skip Wrangler's build steps. Particularly useful when using custom builds. Refer to [Bundling ↗](https://developers.cloudflare.com/workers/wrangler/bundling/) for more information.
- `--env` string optional
	- Perform on a specific environment.
- `--compatibility-date` string optional
	- A date in the form yyyy-mm-dd, which will be used to determine which version of the Workers runtime is used.
- `--compatibility-flags`, `--compatibility-flag` string\[\] optional
	- Flags to use for compatibility checks.
- `--latest` boolean (default: true) optional
	- Use the latest version of the Workers runtime.
- `--ip` string optional
	- IP address to listen on, defaults to `localhost`.
- `--port` number optional
	- Port to listen on.
- `--inspector-port` number optional
	- Port for devtools to connect to.
- `--routes`, `--route` string\[\] optional
	- Routes to upload.
	- For example: `--route example.com/*`.
- `--host` string optional
	- Host to forward requests to, defaults to the zone of project.
- `--local-protocol` 'http'|'https' (default: http) optional
	- Protocol to listen to requests on.
- `--https-key-path` string optional
	- Path to a custom certificate key.
- `--https-cert-path` string optional
	- Path to a custom certificate.
- `--local-upstream` string optional
	- Host to act as origin in local mode, defaults to `dev.host` or route.
- `--assets` string optional beta
	- Folder of static assets to be served. Replaces [Workers Sites](https://developers.cloudflare.com/workers/configuration/sites/). Visit [assets](https://developers.cloudflare.com/workers/static-assets/) for more information.
- `--site` string optional deprecated, use \`--assets\`
	- Folder of static assets for Workers Sites.
- `--site-include` string\[\] optional deprecated
	- Array of `.gitignore` -style patterns that match file or directory names from the sites directory. Only matched items will be uploaded.
- `--site-exclude` string\[\] optional deprecated
	- Array of `.gitignore` -style patterns that match file or directory names from the sites directory. Matched items will not be uploaded.
- `--upstream-protocol` 'http'|'https' (default: https) optional
	- Protocol to forward requests to host on.
- `--var` key:value\\\[\] optional
	- Array of `key:value` pairs to inject as variables into your code. The value will always be passed as a string to your Worker.
	- For example, `--var "git_hash:'$(git rev-parse HEAD)'" "test:123"` makes the `git_hash` and `test` variables available in your Worker's `env`.
	- This flag is an alternative to defining [`vars`](https://developers.cloudflare.com/workers/wrangler/configuration/#non-inheritable-keys) in your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/). If defined in both places, this flag's values will be used.
- `--define` key:value\\\[\] optional
	- Array of `key:value` pairs to replace global identifiers in your code.
	- For example, `--define "GIT_HASH:'$(git rev-parse HEAD)'"` will replace all uses of `GIT_HASH` with the actual value at build time.
	- This flag is an alternative to defining [`define`](https://developers.cloudflare.com/workers/wrangler/configuration/#non-inheritable-keys) in your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/). If defined in both places, this flag's values will be used.
- `--tsconfig` string optional
	- Path to a custom `tsconfig.json` file.
- `--minify` boolean optional
	- Minify the Worker.
- `--persist-to` string optional
	- Specify directory to use for local persistence.
- `--remote` boolean (default: false) optional
	- Develop against remote resources and data stored on Cloudflare's network.
- `--test-scheduled` boolean (default: false) optional
	- Exposes a `/__scheduled` fetch route which will trigger a scheduled event (Cron Trigger) for testing during development. To simulate different cron patterns, a `cron` query parameter can be passed in: `/__scheduled?cron=*+*+*+*+*` or `/cdn-cgi/handler/scheduled?cron=*+*+*+*+*`.
- `--log-level` 'debug'|'info'|'log'|'warn'|'error|'none' (default: log) optional
	- Specify Wrangler's logging level.
- `--show-interactive-dev-session` boolean (default: true if the terminal supports interactivity) optional
	- Show the interactive dev session.
- `--alias` `Array<string>`
	- Specify modules to alias using [module aliasing](https://developers.cloudflare.com/workers/wrangler/configuration/#module-aliasing).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

`wrangler dev` is a way to [locally test](https://developers.cloudflare.com/workers/development-testing/) your Worker while developing. With `wrangler dev` running, send HTTP requests to `localhost:8787` and your Worker should execute as expected. You will also see `console.log` messages and exceptions appearing in your terminal.

---

## deploy

Deploy your Worker to Cloudflare.

```txt
wrangler deploy [<SCRIPT>] [OPTIONS]
```

- `SCRIPT` string
	- The path to an entry point for your Worker. Only required if your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/) does not include a `main` key (for example, `main = "index.js"`).
- `--name` string optional
	- Name of the Worker.
- `--no-bundle` boolean (default: false) optional
	- Skip Wrangler's build steps. Particularly useful when using custom builds. Refer to [Bundling ↗](https://developers.cloudflare.com/workers/wrangler/bundling/) for more information.
- `--env` string optional
	- Perform on a specific environment.
- `--outdir` string optional
	- Path to directory where Wrangler will write the bundled Worker files.
- `--compatibility-date` string optional
	- A date in the form yyyy-mm-dd, which will be used to determine which version of the Workers runtime is used.
- `--compatibility-flags`, `--compatibility-flag` string\[\] optional
	- Flags to use for compatibility checks.
- `--latest` boolean (default: true) optional
	- Use the latest version of the Workers runtime.
- `--assets` string optional beta
	- Folder of static assets to be served. Replaces [Workers Sites](https://developers.cloudflare.com/workers/configuration/sites/). Visit [assets](https://developers.cloudflare.com/workers/static-assets/) for more information.
- `--site` string optional deprecated, use \`--assets\`
	- Folder of static assets for Workers Sites.
- `--site-include` string\[\] optional deprecated
	- Array of `.gitignore` -style patterns that match file or directory names from the sites directory. Only matched items will be uploaded.
- `--site-exclude` string\[\] optional deprecated
	- Array of `.gitignore` -style patterns that match file or directory names from the sites directory. Matched items will not be uploaded.
- `--var` key:value\\\[\] optional
	- Array of `key:value` pairs to inject as variables into your code. The value will always be passed as a string to your Worker.
	- For example, `--var git_hash:$(git rev-parse HEAD) test:123` makes the `git_hash` and `test` variables available in your Worker's `env`.
	- This flag is an alternative to defining [`vars`](https://developers.cloudflare.com/workers/wrangler/configuration/#non-inheritable-keys) in your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/). If defined in both places, this flag's values will be used.
- `--define` key:value\\\[\] optional
	- Array of `key:value` pairs to replace global identifiers in your code.
	- For example, `--define GIT_HASH:$(git rev-parse HEAD)` will replace all uses of `GIT_HASH` with the actual value at build time.
	- This flag is an alternative to defining [`define`](https://developers.cloudflare.com/workers/wrangler/configuration/#non-inheritable-keys) in your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/). If defined in both places, this flag's values will be used.
- `--triggers`, `--schedule`, `--schedules` string\[\] optional
	- Cron schedules to attach to the deployed Worker. Refer to [Cron Trigger Examples](https://developers.cloudflare.com/workers/configuration/cron-triggers/#examples).
- `--routes`, `--route` string\[\] optional
	- Routes where this Worker will be deployed.
	- For example: `--route example.com/*`.
- `--tsconfig` string optional
	- Path to a custom `tsconfig.json` file.
- `--minify` boolean optional
	- Minify the bundled Worker before deploying.
- `--dry-run` boolean (default: false) optional
	- Compile a project without actually deploying to live servers. Combined with `--outdir`, this is also useful for testing the output of `npx wrangler deploy`. It also gives developers a chance to upload our generated sourcemap to a service like Sentry, so that errors from the Worker can be mapped against source code, but before the service goes live.
- `--keep-vars` boolean (default: false) optional
	- It is recommended best practice to treat your Wrangler developer environment as a source of truth for your Worker configuration, and avoid making changes via the Cloudflare dashboard.
	- If you change your environment variables in the Cloudflare dashboard, Wrangler will override them the next time you deploy. If you want to disable this behaviour set `keep-vars` to `true`.
	- Secrets are never deleted by a deployment whether this flag is true or false.
- `--dispatch-namespace` string optional
	- Specify the [Workers for Platforms dispatch namespace](https://developers.cloudflare.com/cloudflare-for-platforms/workers-for-platforms/get-started/configuration/#2-create-a-dispatch-namespace) to upload this Worker to.
- `--metafile` string optional
	- Specify a file to write the build metadata from esbuild to. If flag is used without a path string, this defaults to `bundle-meta.json` inside the directory specified by `--outdir`. This can be useful for understanding the bundle size.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## delete

Delete your Worker and all associated Cloudflare developer platform resources.

```txt
wrangler delete [<SCRIPT>] [OPTIONS]
```

- `SCRIPT` string
	- The path to an entry point for your Worker. Only required if your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/) does not include a `main` key (for example, `main = "index.js"`).
- `--name` string optional
	- Name of the Worker.
- `--env` string optional
	- Perform on a specific environment.
- `--dry-run` boolean (default: false) optional
	- Do not actually delete the Worker. This is useful for testing the output of `wrangler delete`.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## kv namespace

Manage Workers KV namespaces.

### create

Create a new namespace.

```txt
wrangler kv namespace create <NAMESPACE> [OPTIONS]
```

- `NAMESPACE` string required
	- The name of the new namespace.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace (the `preview_id` value).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `create` command to create a KV namespace called `MY_KV`.

```sh
npx wrangler kv namespace create "MY_KV"
```

```sh
🌀 Creating namespace with title "worker-MY_KV"
✨ Success!
Add the following to your configuration file in your kv_namespaces array:
kv_namespaces = [
  { binding = "MY_KV", id = "e29b263ab50e42ce9b637fa8370175e8" }
]
```

The following is an example of using the `create` command to create a preview KV namespace called `MY_KV`.

```sh
npx wrangler kv namespace create "MY_KV" --preview
```

```sh
🌀 Creating namespace with title "my-site-MY_KV_preview"
✨ Success!
Add the following to your configuration file in your kv_namespaces array:
kv_namespaces = [
  { binding = "MY_KV", preview_id = "15137f8edf6c09742227e99b08aaf273" }
]
```

### list

List all KV namespaces associated with the current account ID.

```txt
wrangler kv namespace list
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example that passes the Wrangler command through the `jq` command:

```sh
npx wrangler kv namespace list | jq "."
```

```sh
[
  {
    "id": "06779da6940b431db6e566b4846d64db",
    "title": "TEST_NAMESPACE"
  },
  {
    "id": "32ac1b3c2ed34ed3b397268817dea9ea",
    "title": "STATIC_CONTENT"
  }
]
```

### delete

Delete a given namespace.

```txt
wrangler kv namespace delete {--binding=<BINDING>|--namespace-id=<NAMESPACE_ID>} [OPTIONS]
```

- `--binding` string
	- The binding name of the namespace, as stored in the Wrangler file, to delete.
- `--namespace-id` string
	- The ID of the namespace to delete.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace instead of production.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of deleting a KV namespace called `MY_KV.`

```sh
npx wrangler kv namespace delete --binding=MY_KV
```

```sh
Are you sure you want to delete namespace f7b02e7fc70443149ac906dd81ec1791? [y/n]
yes
Deleting namespace f7b02e7fc70443149ac906dd81ec1791
Deleted namespace f7b02e7fc70443149ac906dd81ec1791
```

The following is an example of deleting a preview KV namespace called `MY_KV`.

```sh
npx wrangler kv namespace delete --binding=MY_KV --preview
```

```sh
Are you sure you want to delete namespace 15137f8edf6c09742227e99b08aaf273? [y/n]
yes
Deleting namespace 15137f8edf6c09742227e99b08aaf273
Deleted namespace 15137f8edf6c09742227e99b08aaf273
```

## kv key

Manage key-value pairs within a Workers KV namespace.

### put

Write a single key-value pair to a particular namespace.

```txt
wrangler kv key put <KEY> {<VALUE>|--path=<PATH>} {--binding=<BINDING>|--namespace-id=<NAMESPACE_ID>} [OPTIONS]
```

- `KEY` string required
	- The key to write to.
- `VALUE` string optional
	- The value to write.
- `--path` optional
	- When defined, the value is loaded from the file at `--path` rather than reading it from the `VALUE` argument. This is ideal for security-sensitive operations because it avoids saving keys and values into your terminal history.
- `--binding` string
	- The binding name of the namespace, as stored in the Wrangler file, to write to.
- `--namespace-id` string
	- The ID of the namespace to write to.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace instead of production.
- `--ttl` number optional
	- The lifetime (in number of seconds) that the key-value pair should exist before expiring. Must be at least `60` seconds. This option takes precedence over the `expiration` option.
- `--expiration` number optional
	- The timestamp, in UNIX seconds, indicating when the key-value pair should expire.
- `--metadata` string optional
	- Any (escaped) JSON serialized arbitrary object to a maximum of 1024 bytes.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example that puts a key-value into the namespace with binding name of `MY_KV`.

```sh
npx wrangler kv key put --binding=MY_KV "my-key" "some-value"
```

```sh
Writing the value "some-value" to key "my-key" on namespace f7b02e7fc70443149ac906dd81ec1791.
```

The following is an example that puts a key-value into the preview namespace with binding name of `MY_KV`.

```sh
npx wrangler kv key put --binding=MY_KV --preview "my-key" "some-value"
```

```sh
Writing the value "some-value" to key "my-key" on namespace 15137f8edf6c09742227e99b08aaf273.
```

The following is an example that puts a key-value into a namespace, with a time-to-live value of `10000` seconds.

```sh
npx wrangler kv key put --binding=MY_KV "my-key" "some-value" --ttl=10000
```

```sh
Writing the value "some-value" to key "my-key" on namespace f7b02e7fc70443149ac906dd81ec1791.
```

The following is an example that puts a key-value into a namespace, where the value is read from the `value.txt` file.

```sh
npx wrangler kv key put --binding=MY_KV "my-key" --path=value.txt
```

```sh
Writing the contents of value.txt to the key "my-key" on namespace f7b02e7fc70443149ac906dd81ec1791.
```

### list

Output a list of all keys in a given namespace.

```txt
wrangler kv key list {--binding=<BINDING>|--namespace-id=<NAMESPACE_ID>} [OPTIONS]
```

- `--binding` string
	- The binding name of the namespace, as stored in the Wrangler file, to list from.
- `--namespace-id` string
	- The ID of the namespace to list from.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace instead of production.
- `--prefix` string optional
	- Only list keys that begin with the given prefix.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

Below is an example that passes the Wrangler command through the `jq` command:

```sh
npx wrangler kv key list --binding=MY_KV --prefix="public" | jq "."
```

```sh
[
  {
    "name": "public_key"
  },
  {
    "name": "public_key_with_expiration",
    "expiration": "2019-09-10T23:18:58Z"
  }
]
```

### get

Read a single value by key from the given namespace.

```txt
wrangler kv key get <KEY> {--binding=<BINDING>|--namespace-id=<NAMESPACE_ID>} [OPTIONS]
```

- `KEY` string required
	- The key value to get.
- `--binding` string
	- The binding name of the namespace, as stored in the Wrangler file, to get from.
- `--namespace-id` string
	- The ID of the namespace to get from.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace instead of production.
- `--text` boolean optional
	- Decode the returned value as a UTF-8 string.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example that gets the value of the `"my-key"` key from the KV namespace with binding name `MY_KV`.

```sh
npx wrangler kv key get --binding=MY_KV "my-key"
```

```sh
value
```

### delete

Remove a single key value pair from the given namespace.

```txt
wrangler kv key delete <KEY> {--binding=<BINDING>|--namespace-id=<NAMESPACE_ID>} [OPTIONS]
```

- `KEY` string required
	- The key value to get.
- `--binding` string
	- The binding name of the namespace, as stored in the Wrangler file, to delete from.
- `--namespace-id` string
	- The ID of the namespace to delete from.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace instead of production.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example that deletes the key-value pair with key `"my-key"` from the KV namespace with binding name `MY_KV`.

```sh
npx wrangler kv key delete --binding=MY_KV "my-key"
```

```sh
Deleting the key "my-key" on namespace f7b02e7fc70443149ac906dd81ec1791.
```

## kv bulk

Manage multiple key-value pairs within a Workers KV namespace in batches.

### put

Write a JSON file containing an array of key-value pairs to the given namespace.

```txt
wrangler kv bulk put <FILENAME> {--binding=<BINDING>|--namespace-id=<NAMESPACE_ID>} [OPTIONS]
```

- `FILENAME` string required
	- The JSON file containing an array of key-value pairs to write to the namespace.
- `--binding` string
	- The binding name of the namespace, as stored in the Wrangler file, to write to.
- `--namespace-id` string
	- The ID of the namespace to write to.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace instead of production.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

This command takes a JSON file as an argument with a list of key-value pairs to upload. An example of JSON input:

```json
[
  {
    "key": "test_key",
    "value": "test_value",
    "expiration_ttl": 3600
  }
]
```

KV namespace values can only store strings. In order to save complex a value, stringify it to JSON:

```json
[
  {
    "key": "test_key",
    "value": "{\"name\": \"test_value\"}",
    "expiration_ttl": 3600
  }
]
```

Refer to the full schema for key-value entries uploaded via the bulk API:

- `key` string required
	- The key’s name. The name may be 512 bytes maximum. All printable, non-whitespace characters are valid.
- `value` string required
	- The UTF-8 encoded string to be stored, up to 25 MB in length.
- `metadata` object optional
	- Any arbitrary object (must serialize to JSON) to a maximum of 1,024 bytes.
- `expiration` number optional
	- The time, measured in number of seconds since the UNIX epoch, at which the key should expire.
- `expiration_ttl` number optional
	- The number of seconds the document should exist before expiring. Must be at least `60` seconds.
- `base64` boolean optional
	- When true, the server will decode the value as base64 before storing it. This is useful for writing values that would otherwise be invalid JSON strings, such as images. Defaults to `false`.

The following is an example of writing all the key-value pairs found in the `allthethingsupload.json` file.

```sh
npx wrangler kv bulk put --binding=MY_KV allthethingsupload.json
```

```sh
Success!
```

### delete

Delete all keys read from a JSON file within a given namespace.

```txt
wrangler kv bulk delete <FILENAME> {--binding=<BINDING>|--namespace-id=<NAMESPACE_ID>} [OPTIONS]
```

- `FILENAME` string required
	- The JSON file containing an array of keys to delete from the namespace.
- `--binding` string
	- The binding name of the namespace, as stored in the Wrangler file, to delete from.
- `--namespace-id` string
	- The ID of the namespace to delete from.
- `--env` string optional
	- Perform on a specific environment.
- `--preview` boolean optional
	- Interact with a preview namespace instead of production.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

This command takes a JSON file as an argument containing the keys to delete.

The following is an example of the JSON input:

```json
["test_key_1", "test_key_2"]
```

The command also accepts keys in the format output from `wrangler kv key list`:

```json
[{ "name": "test_key_1" }, { "name": "test_key_2" }]
```

The following is an example of deleting all the keys found in the `allthethingsdelete.json` file.

```sh
npx wrangler kv bulk delete --binding=MY_KV allthethingsdelete.json
```

```sh
? Are you sure you want to delete all keys in allthethingsdelete.json from kv-namespace with id "f7b02e7fc70443149ac906dd81ec1791"? › (Y/n)
Success!
```

---

## r2 bucket

Interact with buckets in an R2 store.

### create

Create a new R2 bucket.

```txt
wrangler r2 bucket create <NAME>
```

- `NAME` string required
	- The name of the new R2 bucket.
- `--location` string optional
	- The optional [location hint](https://developers.cloudflare.com/r2/reference/data-location/#location-hints) that determines geographic placement of the R2 bucket.
- `--storage-class` 'Standard|InfrequentAccess' optional
	- The default storage class for objects uploaded to the bucket.
- `--jurisdiction` string optional
	- The jurisdiction where the R2 bucket is created. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### info

Get information about an R2 bucket, including the bucket size and number of objects.

```txt
wrangler r2 bucket info <NAME>
```

- `NAME` string required
	- The name of the R2 bucket to get information about.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### delete

Delete an R2 bucket.

```txt
wrangler r2 bucket delete <NAME>
```

- `NAME` string required
	- The name of the R2 bucket to delete.

### list

List R2 bucket in the current account.

```txt
wrangler r2 bucket list
```

### catalog enable

Enable [R2 Data Catalog](https://developers.cloudflare.com/r2/data-catalog/) on an R2 bucket.

```txt
wrangler r2 bucket catalog enable <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the bucket to enable R2 Data Catalog for.

### catalog disable

Disable [R2 Data Catalog](https://developers.cloudflare.com/r2/data-catalog/) on an R2 bucket.

```txt
wrangler r2 bucket catalog disable <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the bucket to disable R2 Data Catalog for.

### catalog get

Get the status of [R2 Data Catalog](https://developers.cloudflare.com/r2/data-catalog/) for an R2 bucket, including catalog URI and warehouse name.

```txt
wrangler r2 bucket catalog get <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket whose data catalog status to retrieve.

### cors set

Set the [CORS configuration](https://developers.cloudflare.com/r2/buckets/cors/) for an R2 bucket from a JSON file.

```txt
wrangler r2 bucket cors set <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to set the CORS configuration for.
- `--file` string required
	- Path to the JSON file containing CORS configuration (file must be in format of request body of [put bucket CORS policy API](https://developers.cloudflare.com/api/operations/r2-put-bucket-cors-policy)).
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when setting CORS configuration.

### cors delete

Clear the [CORS configuration](https://developers.cloudflare.com/r2/buckets/cors/) for an R2 bucket.

```txt
wrangler r2 bucket cors delete <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to delete the CORS configuration for.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when clearing the CORS configuration.

### cors list

List the [CORS configuration](https://developers.cloudflare.com/r2/buckets/cors/) rules for an R2 bucket.

```txt
wrangler r2 bucket cors list <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to list the CORS rules for.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### dev-url enable

Enable public access via the [r2.dev URL](https://developers.cloudflare.com/r2/buckets/public-buckets/#enable-managed-public-access) for an R2 bucket.

```txt
wrangler r2 bucket dev-url enable <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to enable public access via its r2.dev URL.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when enabling public access via r2.dev URL.

### dev-url disable

Disable public access via the [r2.dev URL](https://developers.cloudflare.com/r2/buckets/public-buckets/#enable-managed-public-access) for an R2 bucket.

```txt
wrangler r2 bucket dev-url disable <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to disable public access via its r2.dev URL.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when disabling public access via r2.dev URL.

### dev-url get

Get the [r2.dev URL](https://developers.cloudflare.com/r2/buckets/public-buckets/#enable-managed-public-access) and status for an R2 bucket.

```txt
wrangler r2 bucket dev-url get <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket whose r2.dev URL status to retrieve.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### domain add

Connect a [custom domain](https://developers.cloudflare.com/r2/buckets/public-buckets/#custom-domains) to an R2 bucket.

```txt
wrangler r2 bucket domain add <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to connect a custom domain to.
- `--domain` string required
	- The custom domain to connect to the R2 bucket.
- `--zone-id` string required
	- The [zone ID](https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/) associated with the custom domain.
- `--min-tls` '1.0'|'1.1'|'1.2'|'1.3' optional
	- Set the minimum TLS version for the custom domain (defaults to 1.0 if not set).
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when adding the custom domain.

### domain remove

Remove a [custom domain](https://developers.cloudflare.com/r2/buckets/public-buckets/#custom-domains) from an R2 bucket.

```txt
wrangler r2 bucket domain remove <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to remove the custom domain from.
- `--domain` string required
	- The custom domain to remove from the R2 bucket.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when removing the custom domain.

### domain update

Update settings for a [custom domain](https://developers.cloudflare.com/r2/buckets/public-buckets/#custom-domains) connected to an R2 bucket.

```txt
wrangler r2 bucket domain update <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket associated with the custom domain to update.
- `--domain` string required
	- The custom domain whose settings will be updated.
- `--min-tls` '1.0'|'1.1'|'1.2'|'1.3' optional
	- Update the minimum TLS version for the custom domain.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### domain get

Get [custom domain](https://developers.cloudflare.com/r2/buckets/public-buckets/#custom-domains) connected to an R2 bucket.

```txt
wrangler r2 bucket domain get <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket whose custom domain to retrieve.
- `--domain` string required
	- The custom domain to get information for.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### domain list

List [custom domains](https://developers.cloudflare.com/r2/buckets/public-buckets/#custom-domains) for an R2 bucket.

```txt
wrangler r2 bucket domain list <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket whose connected custom domains will be listed.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### lifecycle add

Add an [object lifecycle](https://developers.cloudflare.com/r2/buckets/object-lifecycles/) rule to an R2 bucket.

```txt
wrangler r2 bucket lifecycle add <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to add a lifecycle rule to.
- `--name` string optional
	- A unique name for the lifecycle rule, used to identify and manage it. For example: `delete-logs-180-days`.
- `--prefix` string optional
	- Prefix condition for the lifecycle rule (leave empty for all prefixes).
- `--expire-days` number optional
	- Sets the lifecycle rule action to expire objects after this number of days. Note you can provide only one of `--expire-days` or `--expire-date`.
- `--expire-date` string optional
	- Sets the lifecycle rule action to expire objects after this date (YYYY-MM-DD). Note you can provide only one of `--expire-days` or `--expire-date`.
- `--ia-transition-days` number optional
	- Sets the lifecycle rule action to transition objects to Infrequent Access storage after this number of days. Note you can provide only one of `--ia-transition-days` or `--ia-transition-date`.
- `--ia-transition-date` string optional
	- Sets the lifecycle rule action to transition objects to Infrequent Access storage after this date (YYYY-MM-DD). Note you can provide only one of `--ia-transition-days` or `--ia-transition-date`.
- `--abort-multipart-days` number optional
	- Sets the lifecycle rule action to abort incomplete multipart uploads after this number of days.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when adding the lifecycle rule.

### lifecycle remove

Remove an [object lifecycle](https://developers.cloudflare.com/r2/buckets/object-lifecycles/) rule from an R2 bucket.

```txt
wrangler r2 bucket lifecycle remove <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to remove a lifecycle rule from.
- `--name` string required
	- The unique name of the lifecycle rule to remove.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### lifecycle list

List [object lifecycle](https://developers.cloudflare.com/r2/buckets/object-lifecycles/) rules for an R2 bucket.

```txt
wrangler r2 bucket lifecycle list <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to list lifecycle rules for.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### lifecycle set

Set the [object lifecycle](https://developers.cloudflare.com/r2/buckets/object-lifecycles/) configuration for an R2 bucket from a JSON file.

```txt
wrangler r2 bucket lifecycle set <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to set lifecycle configuration for.
- `--file` string required
	- Path to the JSON file containing lifecycle configuration (file must be in format of request body of [put object lifecycle configuration API](https://developers.cloudflare.com/api/resources/r2/subresources/buckets/subresources/lifecycle/methods/update/)).
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when setting object lifecycle configuration.

### lock add

Add a [bucket lock](https://developers.cloudflare.com/r2/buckets/bucket-locks/) rule to an R2 bucket.

```txt
wrangler r2 bucket lock add <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to add a bucket lock rule to.
- `--name` string optional
	- A unique name for the bucket lock rule, used to identify and manage it. For example: `retain-logs-180-days`.
- `--prefix` string optional
	- Prefix condition for the bucket lock rule (leave empty for all prefixes).
- `--retention-days` number optional
	- Sets the number of days to retain objects for. Note you can provide only one of `--retention-days`, `--retention-date`, or `--retention-indefinite`.
- `--retention-date` string optional
	- Sets the number of days to retain objects for. Note you can provide only one of `--retention-days`, `--retention-date`, or `--retention-indefinite`.
- `--retention-indefinite` string optional
	- Sets the retention period to indefinite — meaning the lock will remain in place until explicitly removed. Note you can provide only one of `--retention-days`, `--retention-date`, or `--retention-indefinite`.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when adding the bucket lock rule.

### lock remove

Remove a [bucket lock](https://developers.cloudflare.com/r2/buckets/bucket-locks/) rule from an R2 bucket.

```txt
wrangler r2 bucket lock remove <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to remove a bucket lock rule from.
- `--name` string required
	- The unique name of the bucket lock rule to remove.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### lock list

List [bucket lock](https://developers.cloudflare.com/r2/buckets/bucket-locks/) rules for an R2 bucket.

```txt
wrangler r2 bucket lock list <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to list bucket locks rules for.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).

### lock set

Set the [bucket lock](https://developers.cloudflare.com/r2/buckets/bucket-locks/) configuration for an R2 bucket from a JSON file.

```txt
wrangler r2 bucket lock set <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to set bucket lock configuration for.
- `--file` string required
	- Path to the JSON file containing bucket lock configuration (file must be in format of request body of [put bucket lock configuration API](https://developers.cloudflare.com/api/resources/r2/subresources/buckets/subresources/locks/methods/update/)).
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- `--force` boolean optional
	- Skip confirmation when setting bucket lock configuration.

### notification create

Create an [event notification](https://developers.cloudflare.com/r2/buckets/event-notifications/) rule for an R2 bucket.

```txt
wrangler r2 bucket notification create <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to create an event notification rule for.
- `--event-type` 'object-create'|'object-delete'\[\] required
	- The [type of event(s)](https://developers.cloudflare.com/r2/buckets/event-notifications/#event-types) that will trigger event notifications.
- `--queue` string required
	- The name of the queue that will receive event notification messages.
- `--prefix` string optional
	- The prefix that an object must match to emit event notifications (note: regular expressions are not supported).
- `--suffix` string optional
	- The suffix that an object must match to emit event notifications (note: regular expressions are not supported).
- `--description` string optional
	- A description that can be used to identify the event notification rule after creation.

### notification delete

Remove an event notification rule from a bucket's [event notification](https://developers.cloudflare.com/r2/buckets/event-notifications/) configuration.

```txt
wrangler r2 bucket notification delete <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to delete an event notification rule for.
- `--queue` string required
	- The name of the queue that corresponds to the event notification rule. If no `rule` is provided, all event notification rules associated with the queue will be deleted.
- `--rule` string optional
	- The ID of the event notification rule to delete.

### notification list

List the [event notification](https://developers.cloudflare.com/r2/buckets/event-notifications/) rules for a bucket.

```txt
wrangler r2 bucket notification list <NAME>
```

- `NAME` string required
	- The name of the R2 bucket to get event notification rules for.

### sippy enable

Enable [Sippy](https://developers.cloudflare.com/r2/data-migration/sippy/) incremental migration for a bucket.

```txt
wrangler r2 bucket sippy enable <NAME> [OPTIONS]
```

- `NAME` string required
	- The name of the R2 bucket to enable Sippy.
- `--provider` 'AWS'|'GCS' required
	- The provider of your source object storage bucket.
- `--bucket` string required
	- The name of your source object storage bucket.
- `--r2-key-id` string required
	- Your R2 Access Key ID. Requires read and write access.
- `--r2-secret-access-key` string required
	- Your R2 Secret Access Key. Requires read and write access.
- `--jurisdiction` string optional
	- The jurisdiction where the bucket exists, if a jurisdiction has been specified. Refer to [jurisdictional restrictions](https://developers.cloudflare.com/r2/reference/data-location/#jurisdictional-restrictions).
- **AWS S3 provider-specific options:**
- `--key-id` string optional
	- Your AWS Access Key ID. Requires [read and list access](https://developers.cloudflare.com/r2/data-migration/sippy/#amazon-s3).
- `--secret-access-key` string optional
	- Your AWS Secret Access Key. Requires [read and list access](https://developers.cloudflare.com/r2/data-migration/sippy/#amazon-s3).
- `--region` string optional
	- The AWS region where your S3 bucket is located. For example: `us-west-2`.
- **Google Cloud Storage provider-specific options:**
- `--service-account-key-file` string optional
	- The path to your Google Cloud service account key JSON file. This will read the service account key file and populate `client_email` and `private_key` options. Requires [read and list access](https://developers.cloudflare.com/r2/data-migration/sippy/#google-cloud-storage).
- `--client-email` string optional
	- The client email for your Google Cloud service account key. Requires [read and list access](https://developers.cloudflare.com/r2/data-migration/sippy/#google-cloud-storage).
- `--private-key` string optional
	- The private key for your Google Cloud service account key. Requires [read and list access](https://developers.cloudflare.com/r2/data-migration/sippy/#google-cloud-storage).
- Note that you must provide either `service-account-key-file` or `client_email` and `private_key` for this command to run successfully.

### sippy disable

Disable [Sippy](https://developers.cloudflare.com/r2/data-migration/sippy/) incremental migration for a bucket.

```txt
wrangler r2 bucket sippy disable <NAME>
```

- `NAME` string required
	- The name of the R2 bucket to disable Sippy.

### sippy get

Get the status of [Sippy](https://developers.cloudflare.com/r2/data-migration/sippy/) incremental migration for a bucket.

```txt
wrangler r2 bucket sippy get <NAME>
```

- `NAME` string required
	- The name of the R2 bucket to get the status of Sippy.

## r2 object

Interact with R2 objects.

### get

Fetch an object from an R2 bucket.

```txt
wrangler r2 object get <OBJECT_PATH> [OPTIONS]
```

- `OBJECT_PATH` string required
	- The source object path in the form of `{bucket}/{key}`.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

### put

Create an object in an R2 bucket.

```txt
wrangler r2 object put <OBJECT_PATH> [OPTIONS]
```

- `OBJECT_PATH` string required
	- The destination object path in the form of `{bucket}/{key}`.
- `--file` string optional
	- The path of the file to upload. Note you must provide either `--file` or `--pipe`.
- `--pipe` boolean optional
	- Enables the file to be piped in, rather than specified with the `--file` option. Note you must provide either `--file` or `--pipe`.
- `--content-type` string optional
	- A standard MIME type describing the format of the object data.
- `--content-disposition` string optional
	- Specifies presentational information for the object.
- `--content-encoding` string optional
	- Specifies what content encodings have been applied to the object and thus what decoding mechanisms must be applied to obtain the media-type referenced by the `Content-Type` header field.
- `--content-language` string optional
	- The language the content is in.
- `--cache-control` string optional
	- Specifies caching behavior along the request/reply chain.
- `--expires` string optional
	- The date and time at which the object is no longer cacheable.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

### delete

Delete an object in an R2 bucket.

```txt
wrangler r2 object delete <OBJECT_PATH> [OPTIONS]
```

- `OBJECT_PATH` string required
	- The destination object path in the form of `{bucket}/{key}`.
- `--local` boolean (default: true) optional
	- Interact with locally persisted data.
- `--remote` boolean (default: false) optional
	- Interact with remote storage.
- `--persist-to` string optional
	- Specify directory for locally persisted data.

---

## secret

Manage the secret variables for a Worker.

This action creates a new [version](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#versions) of the Worker and [deploys](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#deployments) it immediately. To only create a new version of the Worker, use the [`wrangler versions secret`](https://developers.cloudflare.com/workers/wrangler/commands/#secret-put) commands.

### put

Create or replace a secret for a Worker.

```txt
wrangler secret put <KEY> [OPTIONS]
```

- `KEY` string required
	- The variable name for this secret to be accessed in the Worker.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from a [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

When running this command, you will be prompted to input the secret's value:

```sh
npx wrangler secret put FOO
```

```sh
? Enter a secret value: › ***
🌀 Creating the secret for script worker-app
✨ Success! Uploaded secret FOO
```

The `put` command can also receive piped input. For example:

```sh
echo "-----BEGIN PRIVATE KEY-----\nM...==\n-----END PRIVATE KEY-----\n" | wrangler secret put PRIVATE_KEY
```

### delete

Delete a secret for a Worker.

```txt
wrangler secret delete <KEY> [OPTIONS]
```

- `KEY` string required
	- The variable name for this secret to be accessed in the Worker.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### list

List the names of all the secrets for a Worker.

```txt
wrangler secret list [OPTIONS]
```

- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of listing the secrets for the current Worker.

```sh
npx wrangler secret list
```

```sh
[
  {
    "name": "FOO",
    "type": "secret_text"
  }
]
```

---

## secret bulk

Upload multiple secrets for a Worker at once.

```txt
wrangler secret bulk [<FILENAME>] [OPTIONS]
```

- `FILENAME` string optional
	- A file containing either [JSON ↗](https://www.json.org/json-en.html) or the [.env ↗](https://www.dotenv.org/docs/security/env) format
	- The JSON file containing key-value pairs to upload as secrets, in the form `{"SECRET_NAME": "secret value", ...}`.
	- The `.env` file containing [key-value pairs to upload as secrets](https://developers.cloudflare.com/workers/configuration/secrets/#local-development-with-secrets), in the form `SECRET_NAME=secret value`.
	- If omitted, Wrangler expects to receive input from `stdin` rather than a file.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of uploading secrets from a JSON file redirected to `stdin`. When complete, the output summary will show the number of secrets uploaded and the number of secrets that failed to upload.

```json
{
  "secret-name-1": "secret-value-1",
  "secret-name-2": "secret-value-2"
}
```

```sh
npx wrangler secret bulk < secrets.json
```

```sh
🌀 Creating the secrets for the Worker "script-name"
✨ Successfully created secret for key: secret-name-1
...
🚨 Error uploading secret for key: secret-name-1
✨ Successfully created secret for key: secret-name-2

Finished processing secrets JSON file:
✨ 1 secrets successfully uploaded
🚨 1 secrets failed to upload
```

## secrets-store secret

With the release of [Secrets Store](https://developers.cloudflare.com/secrets-store/) in open beta, you can use the following commands to manage your account secrets.

### create

Create a secret within a store.

```txt
wrangler secrets-store secret create <STORE_ID> [OPTIONS]
```

- `STORE_ID` string required
	- The secret store public ID. You can find it and copy from the [Secrets Store tab ↗](https://dash.cloudflare.com/?to=/:account/secrets-store/) on the dashboard.
- `--name` string required
	- A descriptive name for the account-level secret. Cannot contain spaces.
- `--value` string test only
	- Value of the secret.
- `--scopes` string required
	- Which services will have access to the account-level secret. Currently, only `workers` is available.
- `--comment` string optional
	- Additional information about the account-level secret.
- `--remote` boolean (default: false) optional
	- Execute the command against the remote Secrets Store. To interact with account-level secrets in production, make sure to append `--remote` to your commands.

The following is an example of using the `create` command to create an account-level secret.

```sh
npx wrangler secrets-store secret create 8f7a1cdced6342c18d223ece462fd88d --name ServiceA_key-1 --scopes workers --remote
```

```sh
✓ Enter a secret value: › ***

🔐 Creating secret... (Name: ServiceA_key-1, Value: REDACTED, Scopes: workers, Comment: undefined)
✓ Select an account: › My account
✅ Created secret! (ID: 13bc7498c6374a4e9d13be091c3c65f1)
```

### update

Update a secret within a store.

```txt
wrangler secrets-store secret update <STORE_ID> [OPTIONS]
```

- `STORE_ID` string required
	- The ID of the secrets store that contains the secret you are updating.
- `--secret-id` string required
	- The ID of the secret to update.
- `--value` string test only
	- Updated value of the secret.
- `--scopes` string required
	- Which services will have access to the account-level secret. Currently, only `workers` is available.
- `--comment` string optional
	- Updated comment for the account-level secret.
- `--remote` boolean (default: false) optional
	- Execute the command against the remote Secrets Store. To interact with account-level secrets in production, make sure to append `--remote` to your commands.

### duplicate

Duplicate a secret within a store. Use this command to create a new secret that holds the same secret value as an existing secret.

```txt
wrangler secrets-store secret duplicate <STORE_ID> [OPTIONS]
```

- `STORE_ID` string required
	- The ID of the secrets store that contains the secret you are duplicating.
- `--secret-id` string required
	- The ID of the secret you are duplicating.
- `--name` string required
	- A name for the new secret. Cannot contain spaces.
- `--scopes` string required
	- Which services will have access to the new account-level secret. Currently, only `workers` is available.
- `--comment` string optional
	- Additional information about the new account-level secret.
- `--remote` boolean (default: false) optional
	- Execute the command against the remote Secrets Store. To interact with account-level secrets in production, make sure to append `--remote` to your commands.

### get

Get information on a secret within a store.

```txt
wrangler secrets-store secret get <STORE_ID> [OPTIONS]
```

- `STORE_ID` string required
	- The ID of the secrets store that contains the secret you want to get.
- `--secret-id` string required
	- The ID of the secret you want to get.
- `--remote` boolean (default: false) optional
	- Execute the command against the remote Secrets Store. To interact with account-level secrets in production, make sure to append `--remote` to your commands.

The following is an example with the expected output:

```sh
npx wrangler secrets-store secret get 8f7a1cdced6342c18d223ece462fd88d --secret-id 13bc7498c6374a4e9d13be091c3c65f1 --remote
```

```sh
🔐 Getting secret... (ID: 13bc7498c6374a4e9d13be091c3c65f1)
✓ Select an account: › My account
| Name                        | ID                                  | StoreID                             | Comment | Scopes  | Status  | Created                | Modified               |
|-----------------------------|-------------------------------------|-------------------------------------|---------|---------|---------|------------------------|------------------------|
| ServiceA_key-1          | 13bc7498c6374a4e9d13be091c3c65f1    | 8f7a1cdced6342c18d223ece462fd88d    |         | workers | active  | 4/9/2025, 10:06:01 PM  | 4/15/2025, 09:13:05 AM |
```

### delete

Delete a secret within a store.

```txt
wrangler secrets-store secret delete <STORE_ID> [OPTIONS]
```

- `STORE_ID` string required
	- The ID of the secrets store that contains the secret you are deleting.
- `--secret-id` string required
	- The ID of the secret you are deleting.
- `--remote` boolean (default: false) optional
	- Execute the command against the remote Secrets Store. To interact with account-level secrets in production, make sure to append `--remote` to your commands.

### list

List secrets within a store.

```txt
wrangler secrets-store secret list <STORE_ID>
```

- `STORE_ID` string required
	- The secret store public ID. You can find it and copy from the [Secrets Store tab ↗](https://dash.cloudflare.com/?to=/:account/secrets-store/) on the dashboard.

## secrets-store store

Use the following commands to manage your store.

### create

Create a store within Secrets Store.

```txt
wrangler secrets-store store create <name>
```

- `name` string required
	- A descriptive name for the account-level secret. Cannot contain spaces.
- `--remote` boolean (default: false) required
	- Execute the command against the remote Secrets Store.

The following is an example of using the `create` command to create a store.

```sh
npx wrangler secrets-store store create default --remote
```

```sh
🔐 Creating store... (Name: default)
✅ Created store! (Name: default, ID: 2e2a82d317134506b58defbe16982d54)
```

### delete

Delete a store within Secrets Store.

```txt
wrangler secrets-store store delete <STORE_ID>
```

- `STORE_ID` string required
	- The secret store public ID. You can find it and copy from the [Secrets Store tab ↗](https://dash.cloudflare.com/?to=/:account/secrets-store/) on the dashboard.
- `--remote` boolean (default: false) required
	- Execute the command against the remote Secrets Store.

The following is an example of using the `delete` command to delete a store.

```sh
npx wrangler secrets-store store delete d2dafaeac9434de2b6d08b292ce08211 --remote
```

```sh
🔐 Deleting store... (Name: d2dafaeac9434de2b6d08b292ce08211)
✅ Deleted store! (ID: d2dafaeac9434de2b6d08b292ce08211)
```

### list

List the stores within an account.

```txt
wrangler secrets-store store list
```

- `--remote` boolean (default: false) required
	- Execute the command against the remote Secrets Store.

The following is an example of using the `list` command to list stores.

```sh
npx wrangler secrets-store store list --remote
```

```sh
🔐 Listing stores...
┌─────────┬──────────────────────────────────┬──────────────────────────────────┬──────────────────────┬──────────────────────┐
│ Name    │ ID                               │ AccountID                        │ Created              │ Modified             │
├─────────┼──────────────────────────────────┼──────────────────────────────────┼──────────────────────┼──────────────────────┤
│ default │ 8876bad33f164462bf0743fe8adf98f4 │ REDACTED │ 4/9/2025, 1:11:48 PM  │ 4/9/2025, 1:11:48 PM │
└─────────┴──────────────────────────────────┴──────────────────────────────────┴──────────────────────┴──────────────────────┘
```

## workflows

Manage and configure [Workflows](https://developers.cloudflare.com/workflows/).

### list

Lists the registered Workflows for this account.

```sh
wrangler workflows list
```

- `--page` number optional
	- Show a specific page from the listing. You can configure page size using "per-page".
- `--per-page` number optional
	- Configure the maximum number of Workflows to show per page.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### instances

Manage and interact with specific instances of a Workflow.

### instances list

List Workflow instances.

```sh
wrangler workflows instances list <WORKFLOW_NAME> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### instances describe

Describe a specific instance of a Workflow, including its current status, any persisted state, and per-step outputs.

```sh
wrangler workflows instances describe <WORKFLOW_NAME> <ID> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.
- `ID` string required
	- The ID of a Workflow instance. You can optionally provide `latest` to refer to the most recently created instance of a Workflow.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

```sh
# Passing \`latest\` instead of an explicit ID will describe the most recently queued instance
wrangler workflows instances describe my-workflow latest
```

```sh
Workflow Name:         my-workflow
Instance Id:           51c73fc8-7fd5-47d9-bd82-9e301506ee72
Version Id:            cedc33a0-11fa-4c26-8a8e-7d28d381a291
Status:                ✅ Completed
Trigger:               🌎 API
Queued:                10/16/2024, 2:00:39 PM
Success:               ✅ Yes
Start:                 10/16/2024, 2:00:39 PM
End:                   10/16/2024, 2:01:40 PM
Duration:              1 minute
# Remaining output truncated
```

### instances terminate

Terminate (permanently stop) a Workflow instance.

```sh
wrangler workflows instances terminate <WORKFLOW_NAME> <ID> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.
- `ID` string required
	- The ID of a Workflow instance.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### instances pause

Pause (until resumed) a Workflow instance.

```sh
wrangler workflows instances pause <WORKFLOW_NAME> <ID> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.
- `ID` string required
	- The ID of a Workflow instance.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### instances resume

Resume a paused Workflow instance.

```sh
wrangler workflows instances resume <WORKFLOW_NAME> <ID> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.
- `ID` string required
	- The ID of a Workflow instance.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### describe

```sh
wrangler workflows describe <WORKFLOW_NAME> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### delete

Delete a Workflow and all its instances.

```sh
wrangler workflows delete <WORKFLOW_NAME> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

```sh
wrangler workflows instances delete my-workflow
```

### trigger

Trigger (create) a Workflow instance.

```sh
wrangler workflows trigger <WORKFLOW_NAME> <PARAMS> [OPTIONS]
```

- `WORKFLOW_NAME` string required
	- The name of a registered Workflow.
- `PARAMS` string optional
	- The parameters to pass to the Workflow as an event. Must be a JSON-encoded string.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

```sh
# Pass optional params to the Workflow.
wrangler workflows trigger my-workflow '{"hello":"world"}'
```

## tail

Start a session to livestream logs from a deployed Worker.

```txt
wrangler tail <WORKER> [OPTIONS]
```

- `WORKER` string required
	- The name of your Worker or the route the Worker is running on.
- `--format` 'json'|'pretty' optional
	- The format of the log entries.
- `--status` 'ok'|'error'|'canceled' optional
	- Filter by invocation status.
- `--header` string optional
	- Filter by HTTP header.
- `--method` string optional
	- Filter by HTTP method.
- `--sampling-rate` number optional
	- Add a fraction of requests to log sampling rate (between `0` and `1`).
- `--search` string optional
	- Filter by a text match in `console.log` messages.
- `--ip` (string|'self')\\\[\] " optional
	- Filter by the IP address the request originates from. Use `"self"` to show only messages from your own IP.
- `--version-id` string optional
	- Filter by Worker version.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

After starting `wrangler tail`, you will receive a live feed of console and exception logs for each request your Worker receives.

If your Worker has a high volume of traffic, the tail might enter sampling mode. This will cause some of your messages to be dropped and a warning to appear in your tail logs. To prevent messages from being dropped, add the options listed above to filter the volume of tail messages.

If sampling persists after using options to filter messages, consider using [instant logs ↗](https://developers.cloudflare.com/logs/instant-logs/).

---

## pages

Configure Cloudflare Pages.

### dev

Develop your full-stack Pages application locally.

```txt
wrangler pages dev [<DIRECTORY>] [OPTIONS]
```

- `DIRECTORY` string optional
	- The directory of static assets to serve.
- `--local` boolean optional (default: true)
	- Run on your local machine.
- `--ip` string optional
	- IP address to listen on, defaults to `localhost`.
- `--port` number optional (default: 8788)
	- The port to listen on (serve from).
- `--config`, `-c` string\[\] optional
	- Path(s) to [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/). If not provided, Wrangler will use the nearest config file based on your current working directory.
	- You can provide additional configuration files in order to run Workers alongside your Pages project, like this: `wrangler pages dev -c ./wrangler.toml -c ../other-worker/wrangler.toml`. The first argument must point to your Pages configuration file, and the subsequent configurations will be accessible via a Service binding from your Pages project.
- `--binding` string\[\] optional
	- Bind an environment variable or secret (for example, `--binding <VARIABLE_NAME>=<VALUE>`).
- `--kv` string\[\] optional
	- Binding name of [KV namespace](https://developers.cloudflare.com/kv/) to bind (for example, `--kv <BINDING_NAME>`).
- `--r2` string\[\] optional
	- Binding name of [R2 bucket](https://developers.cloudflare.com/pages/functions/bindings/#interact-with-your-r2-buckets-locally) to bind (for example, `--r2 <BINDING_NAME>`).
- `--d1` string\[\] optional
	- Binding name of [D1 database](https://developers.cloudflare.com/pages/functions/bindings/#interact-with-your-d1-databases-locally) to bind (for example, `--d1 <BINDING_NAME>`).
- `--do` string\[\] optional
	- Binding name of Durable Object to bind (for example, `--do <BINDING_NAME>=<CLASS>`).
- `--live-reload` boolean optional (default: false)
	- Auto reload HTML pages when change is detected.
- `--compatibility-flag` string\[\] optional
	- Runtime compatibility flags to apply.
- `--compatibility-date` string optional
	- Runtime compatibility date to apply.
- `--show-interactive-dev-session` boolean optional (default: true if the terminal supports interactivity)
	- Show the interactive dev session.
- `--https-key-path` string optional
	- Path to a custom certificate key.
- `--https-cert-path` string optional
	- Path to a custom certificate.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### download config

Download your Pages project config as a [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).

```txt
wrangler pages download config <PROJECT_NAME>
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### project list

List your Pages projects.

```txt
wrangler pages project list
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### project create

Create a new Cloudflare Pages project.

```txt
wrangler pages project create <PROJECT_NAME> [OPTIONS]
```

- `PROJECT_NAME` string required
	- The name of your Pages project.
- `--production-branch` string optional
	- The name of the production branch of your project.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### project delete

Delete a Cloudflare Pages project.

```txt
wrangler pages project delete <PROJECT_NAME> [OPTIONS]
```

- `PROJECT_NAME` string required
	- The name of the Pages project to delete.
- `--yes` boolean optional
	- Answer `"yes"` to confirmation prompt.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### deployment list

List deployments in your Cloudflare Pages project.

```txt
wrangler pages deployment list [--project-name <PROJECT_NAME>]
```

- `--project-name` string optional
	- The name of the project you would like to list deployments for.
- `--environment` 'production'|'preview' optional
	- Environment type to list deployments for.
- `--json` boolean optional
	- Whether to output the list in JSON format.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### deployment tail

Start a session to livestream logs from your deployed Pages Functions.

```txt
wrangler pages deployment tail [<DEPLOYMENT>] [OPTIONS]
```

- `DEPLOYMENT` string optional
	- ID or URL of the deployment to tail. Specify by environment if deployment ID is unknown.
- `--project-name` string optional
	- The name of the project you would like to tail.
- `--environment` 'production'|'preview' optional
	- When not providing a specific deployment ID, specifying environment will grab the latest production or preview deployment.
- `--format` 'json'|'pretty' optional
	- The format of the log entries.
- `--status` 'ok'|'error'|'canceled' optional
	- Filter by invocation status.
- `--header` string optional
	- Filter by HTTP header.
- `--method` string optional
	- Filter by HTTP method.
- `--sampling-rate` number optional
	- Add a percentage of requests to log sampling rate.
- `--search` string optional
	- Filter by a text match in `console.log` messages.
- `--ip` (string|'self')\\\[\] optional
	- Filter by the IP address the request originates from. Use `"self"` to show only messages from your own IP.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

After starting `wrangler pages deployment tail`, you will receive a live stream of console and exception logs for each request your Functions receive.

### deploy

Deploy a directory of static assets as a Pages deployment.

```txt
wrangler pages deploy <BUILD_OUTPUT_DIRECTORY> [OPTIONS]
```

- `BUILD_OUTPUT_DIRECTORY` string optional
	- The [directory](https://developers.cloudflare.com/pages/configuration/build-configuration/#framework-presets) of static files to upload. As of Wrangler 3.45.0, this is only required when your Pages project does not have a Wrangler file. Refer to the [Pages Functions configuration guide](https://developers.cloudflare.com/pages/functions/wrangler-configuration/) for more information.
- `--project-name` string optional
	- The name of the project you want to deploy to.
- `--branch` string optional
	- The name of the branch you want to deploy to.
- `--commit-hash` string optional
	- The SHA to attach to this deployment.
- `--commit-message` string optional
	- The commit message to attach to this deployment.
- `--commit-dirty` boolean optional
	- Whether or not the workspace should be considered dirty for this deployment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### secret put

Create or update a secret for a Pages project.

```txt
wrangler pages secret put <KEY> [OPTIONS]
```

- `KEY` string required
	- The variable name for this secret to be accessed in the Pages project.
- `--project-name` string optional
	- The name of your Pages project.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### secret delete

Delete a secret from a Pages project.

```txt
wrangler pages secret delete <KEY> [OPTIONS]
```

- `KEY` string required
	- The variable name for this secret to be accessed in the Pages project.
- `--project-name` string optional
	- The name of your Pages project.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### secret list

List the names of all the secrets for a Pages project.

```txt
wrangler pages secret list [OPTIONS]
```

- `--project-name` string optional
	- The name of your Pages project.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### secret bulk

Upload multiple secrets for a Pages project at once.

```txt
wrangler pages secret bulk [<FILENAME>] [OPTIONS]
```

- `FILENAME` string optional
	- A file containing either [JSON ↗](https://www.json.org/json-en.html) or the [.env ↗](https://www.dotenv.org/docs/security/env) format
	- The JSON file containing key-value pairs to upload as secrets, in the form `{"SECRET_NAME": "secret value", ...}`.
	- The `.env` file containing [key-value pairs to upload as secrets](https://developers.cloudflare.com/workers/configuration/secrets/#local-development-with-secrets), in the form `SECRET_NAME=secret value`.
	- If omitted, Wrangler expects to receive input from `stdin` rather than a file.
- `--project-name` string optional
	- The name of your Pages project.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### functions build

Compile a folder of Pages Functions into a single Worker.

```txt
wrangler pages functions build [<DIRECTORY>] [OPTIONS]
```

- `DIRECTORY` string optional (default: \`functions\`)
	- The directory of Pages Functions.
- `--outdir` string optional
	- Output directory for the bundled Worker.
- `--fallback-service` string optional (default: \`ASSETS\`)
	- The service to fallback to at the end of the `next` chain. Setting to `''` will fallback to the global `fetch`.
- `--compatibility-date` string optional
	- Date to use for compatibility checks.
- `--compatibility-flags` string\[\] optional
	- Flags to use for compatibility checks.
- `--metafile` string optional
	- Specify a file to write the build metadata from esbuild to. If flag is used without a path string, this defaults to `bundle-meta.json` inside the directory specified by `--outdir`. This can be useful for understanding the bundle size.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## pipelines

Manage your [Pipelines](https://developers.cloudflare.com/pipelines/).

### create

Create a new pipeline

```txt
wrangler pipelines create <name> --r2 <r2-bucket-name> [OPTIONS]
```

- `name` string required
	- The name of the pipeline to create
- `--source` array optional
	- List of allowed sources. Options: `http` or `worker`
- `--require-http-auth` boolean optional
	- Require Cloudflare API token to authenticate with the HTTPS endpoint. Defaults to `false`.
- `--cors-origins` array optional
	- CORS Origin allowlist for HTTP endpoint. Allows `*`. Defaults to an empty array.
- `--batch-max-mb` number optional
	- The maximum size of a batch in megabytes before data is written. Defaults to `100`. Must be between `1` and `100`.
- `--batch-max-rows` number optional
	- The maximum number of rows in a batch before data is written. Defaults to `10000000`. Must be between `1` and `10000000`.
- `--batch-max-seconds` number optional
	- The maximum duration of a batch before data is written in seconds. Defaults to `300`. Must be between `1` and `300`.
- `--r2-bucket` string required
	- The name of the R2 bucket used as the destination to store the data.
- `--r2-bucket-access-key-id` string optional
	- Access key ID used to authenticate with R2. Leave empty for oauth confirmation.
- `--r2-bucket-secret-access-key` string optional
	- Secret access key ID used to authenticate with R2. Leave empty for oauth confirmation.
- `--r2-prefix` string optional
	- Prefix for storing files in the destination bucket.
- `--compression` string optional
	- Type of compression to apply to output files. Choices: `none`, `gzip`, `deflate`
- `--shard-count` number optional
	- Number of pipeline shards. More shards handle higher request volume; fewer shards produce larger output files. Defaults to `2`. Must be between `1` and `15`.

### update

Update an existing pipeline

```txt
wrangler pipelines update <name> [OPTIONS]
```

- `name` string required
	- The name of the pipeline to create
- `--source` array optional
	- List of allowed sources. Options: `http` or `worker`
- `--require-http-auth` boolean optional
	- Require Cloudflare API token to authenticate with the HTTPS endpoint. Defaults to `false`.
- `--cors-origins` array optional
	- CORS Origin allowlist for HTTP endpoint. Allows `*`. Defaults to an empty array.
- `--batch-max-mb` number optional
	- The maximum size of a batch in megabytes before data is written. Defaults to `100`. Must be between `1` and `100`.
- `--batch-max-rows` number optional
	- The maximum number of rows in a batch before data is written. Defaults to `10000000`. Must be between `1` and `10000000`.
- `--batch-max-seconds` number optional
	- The maximum duration of a batch before data is written in seconds. Defaults to `300`. Must be between `1` and `300`.
- `--r2-bucket` string required
	- The name of the R2 bucket used as the destination to store the data.
- `--r2-bucket-access-key-id` string optional
	- Access key ID used to authenticate with R2. Leave empty for oauth confirmation.
- `--r2-bucket-secret-access-key` string optional
	- Secret access key ID used to authenticate with R2. Leave empty for oauth confirmation.
- `--r2-prefix` string optional
	- Prefix for storing files in the destination bucket.
- `--compression` string optional
	- Type of compression to apply to output files. Choices: `none`, `gzip`, `deflate`
- `--shard-count` number optional
	- Number of pipeline shards. More shards handle higher request volume; fewer shards produce larger output files. Defaults to `2`. Must be between `1` and `15`.

### get

Get the configuration for an existing pipeline.

```txt
wrangler pipelines get <name> [OPTIONS]
```

- `name` string required
	- The name of the pipeline to inspect

### delete

Deletes an existing pipeline

```txt
wrangler pipelines delete <name> [OPTIONS]
```

- `name` string required
	- The name of the pipeline to delete

### list

Lists all pipelines in your account.

```txt
wrangler pipelines list [OPTIONS]
```

## queues

Manage your Workers [Queues](https://developers.cloudflare.com/queues/) configurations.

### create

Create a new queue.

```txt
wrangler queues create <name> [OPTIONS]
```

- `name` string required
	- The name of the queue to create.
- `--delivery-delay-secs` number optional
	- How long a published message should be delayed for, in seconds. Must be a positive integer.
- `--message-retention-period-secs` number optional
	- How long a published message is retained in the Queue. Must be a positive integer between 60 and 1209600 (14 days). Defaults to 345600 (4 days).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### update

Update an existing queue.

```txt
wrangler queues update <name> [OPTIONS]
```

- `name` string required
	- The name of the queue to update.
- `--delivery-delay-secs` number optional
	- How long a published message should be delayed for, in seconds. Must be a positive integer.
- `--message-retention-period-secs` number optional
	- How long a published message is retained on the Queue. Must be a positive integer between 60 and 1209600 (14 days). Defaults to 345600 (4 days).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### delete

Delete an existing queue.

```txt
wrangler queues delete <name> [OPTIONS]
```

- `name` string required
	- The name of the queue to delete.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### list

List all queues in the current account.

```txt
wrangler queues list [OPTIONS]
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### info

Get information on individual queues.

```txt
wrangler queues info <name>
```

- `name` string required
	- The name of the queue to inspect.

### consumer

Manage queue consumer configurations.

Add a Worker script as a [queue consumer](https://developers.cloudflare.com/queues/reference/how-queues-works/#consumers).

```txt
wrangler queues consumer add <queue-name> <script-name> [OPTIONS]
```

- `queue-name` string required
	- The name of the queue to add the consumer to.
- `script-name` string required
	- The name of the Workers script to add as a consumer of the named queue.
- `--batch-size` number optional
	- Maximum number of messages per batch. Must be a positive integer.
- `--batch-timeout` number optional
	- Maximum number of seconds to wait to fill a batch with messages. Must be a positive integer.
- `--message-retries` number optional
	- Maximum number of retries for each message. Must be a positive integer.
- `--max-concurrency` number optional
	- The maximum number of concurrent consumer invocations that will be scaled up to handle incoming message volume. Must be a positive integer.
- `--retry-delay-secs` number optional
	- How long a retried message should be delayed for, in seconds. Must be a positive integer.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### consumer remove

Remove a consumer from a queue.

```txt
wrangler queues consumer remove <queue-name> <script-name>
```

- `queue-name` string required
	- The name of the queue to remove the consumer from.
- `script-name` string required
	- The name of the Workers script to remove as the consumer.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### purge

Permanently delete all messages in a queue.

```txt
wrangler queues purge <queue-name>
```

- `queue-name` string required
	- The name of the queue from which messages should be deleted.

### pause-delivery

Pause message delivery from a Queue to consumers (including push consumers, and HTTP pull consumers)

```txt
wrangler queues pause-delivery <queue-name>
```

- `queue-name` string required
	- The name of the queue which delivery should be paused.

### resume-delivery

Resume delivery from a Queue to consumers (including push consumers, and HTTP pull consumers)

```txt
wrangler queues resume-delivery <queue-name>
```

- `queue-name` string required
	- The name of the queue from which delivery should be resumed.

---

## login

Authorize Wrangler with your Cloudflare account using OAuth. Wrangler will attempt to automatically open your web browser to login with your Cloudflare account.

If you prefer to use API tokens for authentication, such as in headless or continuous integration environments, refer to [Running Wrangler in CI/CD](https://developers.cloudflare.com/workers/ci-cd/).

- `--scopes-list` string optional
	- List all the available OAuth scopes with descriptions.
- `--scopes` string optional
	- Allows to choose your set of OAuth scopes. The set of scopes must be entered in a whitespace-separated list, for example, `npx wrangler login --scopes account:read user:read`.
- `--callback-host` string optional
	- Defaults to `localhost`. Sets the IP or hostname where Wrangler should listen for the OAuth callback.
- `--callback-port` string optional
	- Defaults to `8976`. Sets the port where Wrangler should listen for the OAuth callback.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

If Wrangler fails to open a browser, you can copy and paste the URL generated by `wrangler login` in your terminal into a browser and log in.

If you are using Wrangler from a remote machine, but run the login flow from your local browser, you will receive the following error message after logging in:`This site can't be reached`.

To finish the login flow, run `wrangler login` and go through the login flow in the browser:

```sh
⛅️ wrangler 2.1.6
-------------------
Opening a link in your default browser: https://dash.cloudflare.com/oauth2/auth?xyz...
```

The browser login flow will redirect you to a `localhost` URL on your machine.

Leave the login flow active. Open a second terminal session. In that second terminal session, use `curl` or an equivalent request library on the remote machine to fetch this `localhost` URL. Copy and paste the `localhost` URL that was generated during the `wrangler login` flow and run:

```sh
curl <LOCALHOST_URL>
```

---

## logout

Remove Wrangler's authorization for accessing your account. This command will invalidate your current OAuth token.

```txt
wrangler logout
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

If you are using `CLOUDFLARE_API_TOKEN` instead of OAuth, and you can logout by deleting your API token in the Cloudflare dashboard:

1. Log in to the [Cloudflare dashboard ↗](https://dash.cloudflare.com/).
2. Go to **My Profile** > **API Tokens**.
3. Select the three-dot menu on your Wrangler token.
4. Select **Delete**.

---

## whoami

Retrieve your user information and test your authentication configuration.

```txt
wrangler whoami
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## versions

### upload

Upload a new [version](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#versions) of your Worker that is not deployed immediately.

```txt
wrangler versions upload [OPTIONS]
```

- `--tag` string optional
	- Add a version tag. Accepts empty string.
- `--message` string optional
	- Add a version message. Accepts empty string.
- `--preview-alias` string optional
	- Creates an alias to this version.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### deploy

Deploy a previously created [version](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#versions) of your Worker all at once or create a [gradual deployment](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/gradual-deployments/) to incrementally shift traffic to a new version by following an interactive prompt.

```txt
wrangler versions deploy [OPTIONS]
```

- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### list

Retrieve details for the 10 most recent versions. Details include `Version ID`, `Created on`, `Author`, `Source`, and optionally, `Tag` or `Message`.

```txt
wrangler versions list [OPTIONS]
```

- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### secret put

Create or replace a secret for a Worker. Creates a new [version](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#versions) with modified secrets without [deploying](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#deployments) the Worker.

```txt
wrangler versions secret put <KEY> [OPTIONS]
```

- `KEY` string required
	- The variable name for this secret to be accessed in the Worker.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### secret delete

Delete a secret for a Worker. Creates a new [version](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#versions) with modified secrets without [deploying](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#deployments) the Worker.

```txt
wrangler versions secret delete <KEY> [OPTIONS]
```

- `KEY` string required
	- The variable name for this secret to be accessed in the Worker.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### secret bulk

Upload multiple secrets for a Worker at once. Creates a new [version](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#versions) with modified secrets without [deploying](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#deployments) the Worker.

```txt
wrangler versions secret bulk <FILENAME> [OPTIONS]
```

- `FILENAME` string optional
	- A file containing either [JSON ↗](https://www.json.org/json-en.html) or the [.env ↗](https://www.dotenv.org/docs/security/env) format
	- The JSON file containing key-value pairs to upload as secrets, in the form `{"SECRET_NAME": "secret value", ...}`.
	- The `.env` file containing key-value pairs to upload as secrets, in the form `SECRET_NAME=secret value`.
	- If omitted, Wrangler expects to receive input from `stdin` rather than a file.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--env` string optional
	- Perform on a specific environment.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## triggers

### deploy

Apply changes to triggers ([Routes or domains](https://developers.cloudflare.com/workers/configuration/routing/) and [Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)) when using [`wrangler versions upload`](https://developers.cloudflare.com/workers/wrangler/commands/#upload).

```txt
wrangler triggers deploy [OPTIONS]
```

- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## deployments

[Deployments](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#deployments) track the version(s) of your Worker that are actively serving traffic.

### list

Retrieve details for the 10 most recent [deployments](https://developers.cloudflare.com/workers/configuration/versions-and-deployments/#deployments). Details include `Created on`, `Author`, `Source`, an optional `Message`, and metadata about the `Version(s)` in the deployment.

```txt
wrangler deployments list [OPTIONS]
```

- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### status

Retrieve details for the most recent deployment. Details include `Created on`, `Author`, `Source`, an optional `Message`, and metadata about the `Version(s)` in the deployment.

```txt
wrangler deployments status
```

- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

## rollback

```txt
wrangler rollback [<VERSION_ID>] [OPTIONS]
```

- `VERSION_ID` string optional
	- The ID of the version you wish to roll back to. If not supplied, the `rollback` command defaults to the version uploaded before the latest version.
- `--name` string optional
	- Perform on a specific Worker rather than inheriting from the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--message` string optional
	- Add message for rollback. Accepts empty string. When specified, interactive prompts for rollback confirmation and message are skipped.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## dispatch namespace

### list

List all dispatch namespaces.

```txt
wrangler dispatch-namespace list
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### get

Get information about a dispatch namespace.

```txt
wrangler dispatch-namespace get <NAME>
```

- `NAME` string required
	- The name of the dispatch namespace to get details about.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### create

Create a dispatch namespace.

```txt
wrangler dispatch-namespace create <NAME>
```

- `NAME` string required
	- The name of the dispatch namespace to create.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### delete

Delete a dispatch namespace.

```txt
wrangler dispatch-namespace get <NAME>
```

- `NAME` string required
	- The name of the dispatch namespace to delete.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

### rename

Rename a dispatch namespace.

```txt
wrangler dispatch-namespace get <OLD_NAME> <NEW_NAME>
```

- `OLD_NAME` string required
	- The previous name of the dispatch namespace.
- `NEW_NAME` string required
	- The new name of the dispatch namespace.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## mtls-certificate

Manage client certificates used for mTLS connections in subrequests.

These certificates can be used in [`mtls_certificate` bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/mtls), which allow a Worker to present the certificate when establishing a connection with an origin that requires client authentication (mTLS).

### upload

Upload a client certificate.

```txt
wrangler mtls-certificate upload --cert <PATH> --key <PATH> [OPTIONS]
```

- `--cert` string required
	- A path to the TLS certificate to upload. Certificate chains are supported.
- `--key` string required
	- A path to the private key to upload.
- `--name` string optional
	- The name assigned to the mTLS certificate at upload.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `upload` command to upload an mTLS certificate.

```sh
npx wrangler mtls-certificate upload --cert cert.pem --key key.pem --name my-origin-cert
```

```sh
Uploading mTLS Certificate my-origin-cert...
Success! Uploaded mTLS Certificate my-origin-cert
ID: 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d
Issuer: CN=my-secured-origin.com,OU=my-team,O=my-org,L=San Francisco,ST=California,C=US
Expires: 1/01/2025
```

You can then add this certificate as a [binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/) in your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/):

- [wrangler.jsonc](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2602)
- [wrangler.toml](https://developers.cloudflare.com/workers/wrangler/commands/#tab-panel-2603)

```jsonc
{
  "mtls_certificates": [
    {
      "binding": "MY_CERT",
      "certificate_id": "99f5fef1-6cc1-46b8-bd79-44a0d5082b8d"
    }
  ]
}
```

Note that the certificate and private keys must be in separate (typically `.pem`) files when uploading.

### list

List mTLS certificates associated with the current account ID.

```txt
wrangler mtls-certificate list
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `list` command to upload an mTLS certificate.

```sh
npx wrangler mtls-certificate list
```

```sh
ID: 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d
Name: my-origin-cert
Issuer: CN=my-secured-origin.com,OU=my-team,O=my-org,L=San Francisco,ST=California,C=US
Created on: 1/01/2023
Expires: 1/01/2025

ID: c5d004d1-8312-402c-b8ed-6194328d5cbe
Issuer: CN=another-origin.com,OU=my-team,O=my-org,L=San Francisco,ST=California,C=US
Created on: 1/01/2023
Expires: 1/01/2025
```

### delete

Delete a client certificate.

```txt
wrangler mtls-certificate delete {--id <ID|--name <NAME>}
```

- `--id` string
	- The ID of the mTLS certificate.
- `--name` string
	- The name assigned to the mTLS certificate at upload.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `delete` command to delete an mTLS certificate.

```sh
npx wrangler mtls-certificate delete --id 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d
```

```sh
Are you sure you want to delete certificate 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d (my-origin-cert)? [y/n]
yes
Deleting certificate 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d...
Deleted certificate 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d successfully
```

---

## cert

Manage mTLS client certificates and Certificate Authority (CA) chain certificates used for secured connections.

These certificates can be used in Hyperdrive configurations, enabling them to present the certificate when connecting to an origin database that requires client authentication (mTLS) or a custom Certificate Authority (CA).

### upload mtls-certificate

Upload a client certificate.

```txt
wrangler cert upload mtls-certificate --cert <PATH> --key <PATH> [OPTIONS]
```

- `--cert` string required
	- A path to the TLS certificate to upload. Certificate chains are supported.
- `--key` string required
	- A path to the private key to upload.
- `--name` string optional
	- The name assigned to the mTLS certificate at upload.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `upload` command to upload an mTLS certificate.

```sh
npx wrangler cert upload --cert cert.pem --key key.pem --name my-origin-cert
```

```sh
Uploading mTLS Certificate my-origin-cert...
Success! Uploaded mTLS Certificate my-origin-cert
ID: 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d
Issuer: CN=my-secured-origin.com,OU=my-team,O=my-org,L=San Francisco,ST=California,C=US
Expires: 1/01/2025
```

Note that the certificate and private keys must be in separate (typically `.pem`) files when uploading.

### upload certificate-authority

Upload a client certificate.

```txt
wrangler cert upload certificate-authority --ca-cert <PATH> [OPTIONS]
```

- `--ca-cert` string required
	- A path to the Certificate Authority (CA) chain certificate to upload.
- `--name` string optional
	- The name assigned to the mTLS certificate at upload.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `upload` command to upload an CA certificate.

```sh
npx wrangler cert upload certificate-authority --ca-cert server-ca-chain.pem --name SERVER_CA_CHAIN
```

```sh
Uploading CA Certificate SERVER_CA_CHAIN...
Success! Uploaded CA Certificate SERVER_CA_CHAIN
ID: 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d
Issuer: CN=my-secured-origin.com,OU=my-team,O=my-org,L=San Francisco,ST=California,C=US
Expires: 1/01/2025
```

### list

List mTLS certificates associated with the current account ID. This will display both mTLS certificates and CA certificates.

```txt
wrangler cert list
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `list` command to upload an mTLS or CA certificate.

```sh
npx wrangler cert list
```

```sh
ID: 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d
Name: my-origin-cert
Issuer: CN=my-secured-origin.com,OU=my-team,O=my-org,L=San Francisco,ST=California,C=US
Created on: 1/01/2023
Expires: 1/01/2025

ID: c5d004d1-8312-402c-b8ed-6194328d5cbe
Issuer: CN=another-origin.com,OU=my-team,O=my-org,L=San Francisco,ST=California,C=US
Created on: 1/01/2023
Expires: 1/01/2025
```

### delete

Delete a client certificate.

```txt
wrangler cert delete {--id <ID|--name <NAME>}
```

- `--id` string
	- The ID of the mTLS or CA certificate.
- `--name` string
	- The name assigned to the mTLS or CA certificate at upload.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

The following is an example of using the `delete` command to delete an mTLS or CA certificate.

```sh
npx wrangler cert delete --id 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d
```

```sh
Are you sure you want to delete certificate 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d (my-origin-cert)? [y/n]
yes
Deleting certificate 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d...
Deleted certificate 99f5fef1-6cc1-46b8-bd79-44a0d5082b8d successfully
```

---

## types

Generate types based on your Worker configuration, including `Env` types based on your bindings, module rules, and [runtime types](https://developers.cloudflare.com/workers/languages/typescript/) based on the `compatibility_date` and `compatibility_flags` in your [config file](https://developers.cloudflare.com/workers/wrangler/configuration/).

```txt
wrangler types [<PATH>] [OPTIONS]
```

- `PATH` string (default: \`./worker-configuration.d.ts\`)
	- The path to where types for your Worker will be written.
	- The path must have a `d.ts` extension.
- `--env-interface` string (default: \`Env\`)
	- The name of the interface to generate for the environment object.
	- Not valid if the Worker uses the Service Worker syntax.
- `--include-runtime` boolean (default: true)
	- Whether to generate runtime types based on the `compatibility_date` and `compatibility_flags` in your [config file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--include-env` boolean (default: true)
	- Whether to generate `Env` types based on your Worker bindings.
- `--strict-vars` boolean optional (default: true)
	- Control the types that Wrangler generates for `vars` bindings.
	- If `true`, (the default) Wrangler generates literal and union types for bindings (e.g. `myVar: 'my dev variable' | 'my prod variable'`).
	- If `false`, Wrangler generates generic types (e.g. `myVar: string`). This is useful when variables change frequently, especially when working across multiple environments.
- `--config`, `-c` string\[\] optional
	- Path(s) to [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/). If the Worker you are generating types for has service bindings or bindings to Durable Objects, you can also provide the paths to those configuration files so that the generated `Env` type will include RPC types. For example, given a Worker with a service binding, `wrangler types -c wrangler.toml -c ../bound-worker/wrangler.toml` will generate an `Env` type like this:
	```ts
	interface Env {
	  SERVICE_BINDING: Service<import("../bound-worker/src/index").Entrypoint>;
	}
	```

---

## telemetry

Cloudflare collects anonymous usage data to improve Wrangler. You can learn more about this in our [data policy ↗](https://github.com/cloudflare/workers-sdk/tree/main/packages/wrangler/telemetry.md).

You can manage sharing of usage data at any time using these commands.

### disable

Disable telemetry collection for Wrangler.

```txt
wrangler telemetry disable
```

### enable

Enable telemetry collection for Wrangler.

```txt
wrangler telemetry enable
```

### status

Check whether telemetry collection is currently enabled. The return result is specific to the directory where you have run the command.

This will resolve the global status set by `wrangler telemetry disable / enable`, the environment variable [`WRANGLER_SEND_METRICS`](https://developers.cloudflare.com/workers/wrangler/system-environment-variables/#supported-environment-variables), and the [`send_metrics`](https://developers.cloudflare.com/workers/wrangler/configuration/#top-level-only-keys) key in the [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).

```txt
wrangler telemetry status
```

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.

---

## check

### startup

Generate a CPU profile of your Worker's startup phase.

After you run `wrangler check startup`, you can import the profile into Chrome DevTools or open it directly in VSCode to view a flamegraph of your Worker's startup phase. Additionally, when a Worker deployment fails with a startup time error Wrangler will automatically generate a CPU profile for easy investigation.

```sh
wrangler check startup
```

- `--args` string optional
	- To customise the way `wrangler check startup` builds your Worker for analysis, provide the exact arguments you use when deploying your Worker with `wrangler deploy`, or your Pages project with `wrangler pages functions build`. For instance, if you deploy your Worker with `wrangler deploy --no-bundle`, you should use `wrangler check startup --args="--no-bundle"` to profile the startup phase.
- `--worker` string optional
	- If you don't use Wrangler to deploy your Worker, you can use this argument to provide a Worker bundle to analyse. This should be a file path to a serialized multipart upload, with the exact same format as [the API expects](https://developers.cloudflare.com/api/resources/workers/subresources/scripts/methods/update/).
- `--pages` boolean optional
	- If you don't use a Wrangler config file with your Pages project (i.e. a Wrangler config file containing `pages_build_output_dir`), use this flag to force `wrangler check startup` to treat your project as a Pages project.

The following global flags work on every command:

- `--help` boolean
	- Show help.
- `--config` string (not supported by Pages)
	- Path to your [Wrangler configuration file](https://developers.cloudflare.com/workers/wrangler/configuration/).
- `--cwd` string
	- Run as if Wrangler was started in the specified directory instead of the current working directory.
