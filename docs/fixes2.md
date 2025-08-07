Integrated remediation with repo-specific guidance and targeted fixes for the observed ERROR in enhanced_rag.retrieval.hybrid_searcher.

Where the error originates in your codebase
- File: enhanced_rag/retrieval/hybrid_searcher.py: lines 89–142 show client initialization. The error path logs “Failed to initialize Azure Search client for HybridSearcher” but swallows the exception and does not include the underlying cause. This hides the real error (env/endpoint/key/network/RBAC).
- MultiStageRetriever also initializes classic SDK clients in enhanced_rag/retrieval/multi_stage_pipeline.py: lines 47–111, so failures may also arise there when admin_key/endpoint missing or network blocked.

Repo-tailored root-cause hypotheses and checks
1) Missing/invalid configuration values in config or env
- Risk: In hybrid_searcher._initialize_client(), endpoint/admin_key are required (lines 130–131). If empty/None, it will raise and be suppressed by broad except.
- Confirm:
  - printenv | egrep 'AZURE_SEARCH_ENDPOINT|AZURE_SEARCH_INDEX|AZURE_SEARCH_API_KEY|AZURE_(TENANT|CLIENT|FEDERATED|MANAGED)'
  - Add a one-time debug log to dump non-secret config shape: endpoint host, index, auth mode.
- Fix (copy/paste):
  export AZURE_SEARCH_ENDPOINT="https://<service>.search.windows.net"
  export AZURE_SEARCH_INDEX="codebase-mcp-sota"
  # Prefer AAD; if using key:
  export AZURE_SEARCH_API_KEY="<admin-or-query-key>"

2) Endpoint hostname malformed or region mismatch
- Confirm:
  host="$(echo "$AZURE_SEARCH_ENDPOINT" | sed -E 's@https?://([^/]+)/?.*@\1@')"
  curl -sSI "$AZURE_SEARCH_ENDPOINT/indexes?api-version=2024-07-01" -H "api-key: $AZURE_SEARCH_API_KEY"
  dig +short "$host"
  openssl s_client -connect "$host:443" -servername "$host" </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
- Fix: Ensure https://<service>.search.windows.net and apiVersion 2024-07-01 for vector/hybrid use.

3) Network/Private Endpoint path from container/AKS
- Confirm from same pod:
  kubectl run netshoot --image=nicolaka/netshoot -it --rm -- sh -c 'curl -sSI "$AZURE_SEARCH_ENDPOINT" || true; nslookup $(echo $AZURE_SEARCH_ENDPOINT | sed -E "s@https?://([^/]+)/?.*@\1@"); echo "HTTPS_PROXY=$HTTPS_PROXY NO_PROXY=$NO_PROXY"'
- Private Endpoint expected: yourservice.search.windows.net resolves to 10.x via privatelink.search.windows.net.
- Fix: Link Private DNS, run workload in same VNet/subnet, or set NO_PROXY for *.search.windows.net if PE.

4) RBAC missing for AAD path (DefaultAzureCredential chain)
- Symptoms: Works with admin key via REST, fails with AAD with 403 in data-plane.
- Confirm RBAC:
  az role assignment list --assignee "<principalId-or-appId>" --scope "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<service>" | jq '.[].roleDefinitionName'
- Fix: Assign Search Index Data Reader/Contributor for data-plane; Search Service Contributor for management.

5) API version/SDK inconsistencies
- MultiStageRetriever creates SDK SearchClient (enhanced_rag/retrieval/multi_stage_pipeline.py:99–103). Ensure environment allows SDK path if you rely on it; otherwise prefer the REST-based HybridSearcher path already implemented.
- Fix: Pin azure-search-documents>=11.6.0; or fully route to REST SearchOperations for semantic paths.

High-value code fixes in your repo
1) Make initialization errors observable and structured
- Problem: Current except hides root cause and drops stack trace.
- Fix: Log structured exception with context; preserve traceback.

Patch 1: enhance logging in HybridSearcher
- File: enhanced_rag/retrieval/hybrid_searcher.py: around lines 139–142

[python.diff()]()
- python.diff():
  # Before
  except Exception as e:
      logger.error("Failed to initialize Azure Search client for HybridSearcher")
      self.search_client = None

  # After (structured logging with endpoint host, index, and cause)
  except Exception as e:
      try:
          ep = (endpoint or "").split("://")[-1]
      except Exception:
          ep = None
      logger.error(
          "Failed to initialize Azure Search client for HybridSearcher",
          exc_info=True,
          extra={
              "endpoint_host": ep,
              "index_name": index_name,
              "has_admin_key": bool(admin_key),
              "component": "enhanced_rag.retrieval.hybrid_searcher",
          },
      )
      self.search_client = None
      self._rest_client = None
      self.rest_ops = None

2) Add a health ping post-initialization to fail fast with actionable error
- After creating rest_ops, call a lightweight search stats request with timeout to verify reachability and auth.

Patch 2: post-init ping
- File: enhanced_rag/retrieval/hybrid_searcher.py: after line 138

[python.init_ping()]()
- python.init_ping():
  # Verify connectivity and auth with a lightweight call
  try:
      # servicestats is management; perform a minimal data-plane query to validate index access
      _ = self.rest_ops.search(self._index_name, query="*", top=1, includeTotalCount=False)
  except Exception as ping_err:
      logger.error(
          "Azure Search post-init ping failed",
          exc_info=True,
          extra={
              "endpoint_host": self._endpoint.split('://')[-1] if hasattr(self, "_endpoint") else None,
              "index_name": self._index_name,
              "component": "enhanced_rag.retrieval.hybrid_searcher",
          },
      )
      # Surface failure to upstream; keep rest_ops None to trigger fallbacks
      self.rest_ops = None
      raise

3) Fix MultiStageRetriever client initialization robustness and observability
- It still creates SDK clients (AzureKeyCredential + SearchClient) without api_version or retry options, and logs only a warning.
- If your runtime prefers REST path, degrade gracefully when SDK client creation fails; also log endpoint/index context.

Patch 3: structured logs and apiVersion
- File: enhanced_rag/retrieval/multi_stage_pipeline.py: lines 97–110

[python.diff2()]()
- python.diff2():
  try:
      clients[key] = SearchClient(
          endpoint=endpoint,
          index_name=index_name,
          credential=credential,
          api_version="2024-07-01"
      )
  except Exception as e:
      logger.warning(
          "Failed to initialize client for %s: %s",
          index_name,
          e,
          extra={
              "endpoint_host": (endpoint or "").split("://")[-1],
              "index_name": index_name,
              "component": "enhanced_rag.retrieval.multi_stage_pipeline",
          },
      )

4) Add defensive checks where rest_ops might be None post-failure
- HybridSearcher.search already guards with try/except on each phase; keep as-is but ensure early exit when self.rest_ops is None to avoid retries on dead client.

Patch 4: fast-fail if no rest_ops
- File: enhanced_rag/retrieval/hybrid_searcher.py: at start of async def search()

[python.diff3()]()
- python.diff3():
  if not self.rest_ops:
      logger.error(
          "REST SearchOperations not initialized; hybrid search unavailable",
          extra={"endpoint_host": getattr(self, "_endpoint", None), "index_name": getattr(self, "_index_name", None)}
      )
      return []

Operational runbook tailored to this code
0–5 min: visibility
- Enable structured logs:
  export AZURE_LOG_LEVEL=info
  Ensure your logging config prints exc_info.
- Reproduce the init path by creating the pipeline or HybridSearcher directly to trigger _initialize_client.

5–12 min: configuration validation
- echo "ENDPOINT=$AZURE_SEARCH_ENDPOINT INDEX=$AZURE_SEARCH_INDEX KEY_LEN=$(printf %s "$AZURE_SEARCH_API_KEY" | wc -c)"
- If using AAD instead of key, verify DefaultAzureCredential context vars or MI/WIF mount are present.

12–20 min: endpoint/DNS/TLS and network
- curl -sSI "$AZURE_SEARCH_ENDPOINT/indexes?api-version=2024-07-01" -H "api-key: $AZURE_SEARCH_API_KEY" || true
- In cluster: run netshoot pod check as above. If Private Endpoint, ensure private DNS mapping resolves to 10.x.

20–25 min: RBAC and API version
- az role assignment list … (data-plane roles).
- Ensure 2024-07-01 is supported by your service/SKU/region; otherwise set the highest supported version in both REST ops and SearchClient.

25–30 min: dependency readiness and fallback
- Confirm index exists: az search index show -g <rg> --service-name <svc> -n "$AZURE_SEARCH_INDEX"
- Confirm embeddings/storage endpoints are healthy if you rely on vector paths.
- If still failing, feature-flag fallback: set retrieval.enable_vector_search=false in config or add an env flag to short-circuit HybridSearcher.search to return [] and rely on keyword path in MultiStageRetriever._execute_keyword_search and _execute_semantic_search.

Minimal, correct initialization examples (runnable outside your app)
Python – REST/SDK, retries, telemetry
- Dependencies:
  pip install "azure-search-documents>=11.6.0" "azure-identity>=1.17.1"
- Code:

[python.init_example()]()
- python.init_example():
  import os, sys, logging, time
  from azure.search.documents import SearchClient
  from azure.core.credentials import AzureKeyCredential
  from azure.identity import DefaultAzureCredential
  from azure.core.pipeline.policies import RetryPolicy
  from azure.core.exceptions import HttpResponseError, ClientAuthenticationError, ServiceRequestError

  logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
  log = logging.getLogger("init-check")

  ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
  INDEX = os.environ["AZURE_SEARCH_INDEX"]
  API_KEY = os.environ.get("AZURE_SEARCH_API_KEY")

  cred = AzureKeyCredential(API_KEY) if API_KEY else DefaultAzureCredential(exclude_interactive_browser_credential=True)
  client = SearchClient(endpoint=ENDPOINT, index_name=INDEX, credential=cred, api_version="2024-07-01",
                        retry_policy=RetryPolicy(total_retries=5, retry_backoff_factor=0.8, retry_on_status_codes=[429,500,502,503,504]))

  for attempt in range(1,5):
      try:
          n = client.get_document_count()
          log.info({"endpoint": ENDPOINT.split("://")[-1], "index": INDEX, "count": n, "attempt": attempt})
          break
      except (HttpResponseError, ClientAuthenticationError, ServiceRequestError) as e:
          log.warning({"attempt": attempt, "type": type(e).__name__, "msg": str(e)})
          if attempt == 4:
              log.exception("Initialization failed")
              sys.exit(1)
          time.sleep(min(6, 0.5 * (2 ** (attempt-1))))

TypeScript – Node
- Dependencies:
  npm i @azure/search-documents@^12 @azure/identity@^4 pino@^9
- Code:

[node.init_example.ts()]()
- node.init_example.ts():
  import pino from "pino";
  import { SearchClient, AzureKeyCredential } from "@azure/search-documents";
  import { DefaultAzureCredential } from "@azure/identity";

  const log = pino({ level: process.env.LOG_LEVEL || "info" });
  const endpoint = (process.env.AZURE_SEARCH_ENDPOINT || "").replace(/\/+$/,"");
  const indexName = process.env.AZURE_SEARCH_INDEX || "";
  const apiKey = process.env.AZURE_SEARCH_API_KEY;

  const cred = apiKey ? new AzureKeyCredential(apiKey) : new DefaultAzureCredential({ excludeInteractiveBrowserCredential: true });
  const client = new SearchClient(endpoint, indexName, cred, {
    apiVersion: "2024-07-01",
    retryOptions: { maxRetries: 5, retryDelayInMs: 500, maxRetryDelayInMs: 6000, mode: "Exponential" },
  });

  (async () => {
    for (let attempt=1; attempt<=4; attempt++) {
      try {
        const n = await client.getDocumentCount();
        log.info({ endpoint, indexName, count: n, attempt }, "initialized");
        return;
      } catch (err: any) {
        const status = err?.statusCode || err?.response?.status;
        log.warn({ attempt, status, err: err?.message }, "init failed, retrying");
        if (attempt === 4) {
          log.error({ err }, "init failed");
          process.exit(1);
        }
        await new Promise(r => setTimeout(r, Math.min(6000, 500 * 2 ** (attempt-1))));
      }
    }
  })();

Kubernetes config snippets
- Inject envs from Secret (key mode):
  apiVersion: apps/v1
  kind: Deployment
  spec:
    template:
      spec:
        containers:
        - name: app
          env:
          - name: AZURE_SEARCH_ENDPOINT
            value: "https://<service>.search.windows.net"
          - name: AZURE_SEARCH_INDEX
            value: "codebase-mcp-sota"
          - name: AZURE_SEARCH_API_KEY
            valueFrom:
              secretKeyRef:
                name: search-secrets
                key: api-key

- Workload Identity (AAD, no secrets):
  apiVersion: v1
  kind: ServiceAccount
  metadata:
    name: rag-app
    namespace: prod
    annotations:
      azure.workload.identity/client-id: "<USER_ASSIGNED_MI_CLIENT_ID>"

  # Ensure RBAC role assignment on the Search service scope.

Preflight validation checklist
- Config: endpoint=https://<service>.search.windows.net; index exists; select exactly one auth mode (key or AAD).
- Access:
  - Key path: curl -fsS "$AZURE_SEARCH_ENDPOINT/indexes?api-version=2024-07-01" -H "api-key: $AZURE_SEARCH_API_KEY" >/dev/null
  - AAD path: principal has Search Index Data Reader/Contributor; token acquisition works in pod (MI/WIF).
- Network: DNS resolves; for PE, private IP; outbound 443 allowed; proxy/NO_PROXY set.
- SDK/API: pinned versions; apiVersion=2024-07-01.
- Dependencies: embedding endpoint/storage reachable before enabling vector path.

Post-fix verification
- Startup log now includes structured error or “initialized” with endpoint_host/index_name.
- getDocumentCount works; representative hybrid or keyword search returns 200 with results.
- Metrics: retrieval errors drop; no 401/403/timeout spikes.

Concise fixes for likely misconfigurations
- Endpoint correction:
  export AZURE_SEARCH_ENDPOINT="https://<service>.search.windows.net"
- Provide index:
  export AZURE_SEARCH_INDEX="codebase-mcp-sota"
- Provide admin key securely (temporary for validation):
  export AZURE_SEARCH_API_KEY="$(az search admin-key show -g <rg> --service-name <svc> --query primaryKey -o tsv)"
- Assign RBAC for AAD:
  az role assignment create --assignee "<principalId-or-appId>" --role "Search Index Data Contributor" --scope "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<service>"

Incident-resolution in ≤30 minutes using this repo
- Flip on structured logging, reproduce init to capture the true failure.
- Validate envs, endpoint DNS/TLS, and perform curl/az rest from the same runtime.
- For PE, confirm private DNS; fix NO_PROXY or DNS link.
- If AAD path: assign data-plane role; if key path: validate key via az rest and rotate if needed.
- Ensure apiVersion pin and SDK versions.
- If still blocked, temporarily set retrieval.enable_vector_search=false so pipeline relies on keyword/semantic paths via MultiStageRetriever while you continue network/RBAC investigation.

This completion embeds targeted code-level logging improvements, operational diagnostics tied to your HybridSearcher and MultiStageRetriever, secure configuration paths, and minimal client init examples to unblock initialization failures rapidly and provide durable observability for future incidents.
