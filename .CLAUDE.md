# CLAUDE.md

This file guides Claude Code and subagents working in this repository. It defines coding standards, protected areas, workflows, and expectations for planning, testing, and documentation.

## Project overview
- Stack: React + TypeScript (Vite) frontend, Cloudflare Worker backend.
- Entry points:
  - Frontend: `src/main.tsx`, `src/App.tsx`
  - Worker: `worker/index.ts`
- Build/Run:
  - Dev: `npm run dev`
  - Build: `npm run build`
  - Preview: `npm run preview`
  - Deploy: `npm run deploy`
- Code quality:
  - Lint: `npm run lint`
  - Typecheck: TypeScript as part of build
  - Tests: TODO add test command if present

## Protected paths and rules
Never write to or delete the following without explicit human approval:
- `.env`, `.env.*`, `.git/`, `.github/`
- Lock files: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`
- Secrets/keys/certs directories: `secrets/`, `keys/`, `certs/`
- Infra: `deployment/infra/` (if present)
- CI: `.github/workflows/`

Additional rules:
- Always use absolute file paths for Edit/Write.
- Large logs and artifacts must be written under `.claude/state/` and referenced by path, not inlined.

## Coding standards
- Language: TypeScript for app and worker code.
- Style:
  - Prefer small, pure functions; clear names; single responsibility.
  - Avoid duplicated code; extract shared utilities.
  - Handle errors explicitly; avoid silent failures.
  - Validate inputs; encode outputs when relevant (security).
- Imports:
  - Use explicit, minimal imports; avoid unused symbols.
  - Prefer relative imports within feature folders.
- Async:
  - Use `async/await`; handle rejections; add timeouts for network/IO.
- Performance:
  - Avoid N+1 patterns; batch calls when possible.
  - Be mindful of Cloudflare Worker constraints (cold starts, KV/cache access patterns).

## Testing standards
- Add or update tests for new behavior and bug fixes.
- Include negative cases and edge cases.
- Keep tests deterministic; avoid sleeping; use fakes/mocks where appropriate.
- Minimal acceptance for change:
  - Tests pass locally for impacted area(s).
  - No flakiness introduced.

## Documentation standards
- Update README and relevant docs when behavior changes.
- Keep code comments concise and accurate.
- For significant changes:
  - Include “What changed” and “Why” in PR description.
  - Add migration notes or rollbacks if applicable.

## Commit and PR guidance
- Commit messages: imperative mood, concise subject, optional body with rationale.
- PR checklist:
  - [ ] Tests updated/added
  - [ ] Docs updated (if behavior changed)
  - [ ] Security implications reviewed
  - [ ] No edits to protected paths without approval

## Security checklist (quick)
- No secrets or tokens in code or config.
- Avoid `eval`, dynamic `Function`, unsafe deserialization.
- Validate all external inputs; sanitize outputs when reflected.
- For HTTP:
  - Use safe URL handling; prevent SSRF (no arbitrary fetch of user-controlled URLs).
- File system/path:
  - No path traversal; validate/normalize joins.

## Frontend conventions
- Components:
  - Keep components small; extract hooks for logic.
  - Use React StrictMode-compatible patterns.
- State:
  - Prefer local state or lightweight context; avoid heavy global singletons.
- API calls:
  - Use `/api/*` endpoints; handle loading/error states; debounce as needed.

## Cloudflare Worker conventions
- Route `/api/` to the Worker; serve static assets otherwise.
- Always return structured JSON for API responses.
- Include input validation; return meaningful HTTP status codes.

## Orchestrator expectations (subagent)
Use the orchestrator for multi-file/multi-step tasks requiring planning and delegation.

- MUST:
  - Create `.claude/state/plan.md` with objective, acceptance criteria, risks, rollback.
  - Create `.claude/state/todo.md` with steps, owners (subagent), and outputs.
  - Pause for approval before cross-module refactors, migrations, config changes, dependency upgrades, or any protected path touches.
- Delegate chain (typical):
  1) dependency-mapper → scope blast radius and tests
  2) code-reviewer (+ security-screener in parallel) → preflight issues
  3) minimal implementation edits
  4) test-runner → focused tests, then wider
  5) doc-writer → README/CHANGELOG/docs updates
- Context:
  - Keep heavy logs under `.claude/state/` and link by path.
  - Summarize long outputs with file:line citations.

## Subagent expectations

### dependency-mapper
- Purpose: fast, minimal blast-radius analysis.
- Inputs: symbol/file/diff; produce JSON with entities, edges, files, hotspots, testsToRun, and a short summary.
- Use absolute paths and include file:line anchors.
- Store large grep outputs under `.claude/state/depmap/`.

### code-reviewer
- Purpose: immediate review after changes.
- Review only modified files and directly related code.
- Output prioritized findings with file:line and concrete fix snippets:
  - Critical: must fix
  - Warnings: should fix
  - Suggestions: nice-to-have
- Reference CLAUDE.md rules in recommendations.

### test-runner
- Purpose: run impacted tests and propose minimal fixes.
- Log to `.claude/state/tests.json`.
- Summarize failure signatures; iterate up to 2 fixes before asking for approval to broaden scope.

### security-screener
- Purpose: parallel scan for risky patterns and secrets in modified files.
- Output critical findings with file:line and remediation advice.
- Never echo secrets; advise rotation.

### doc-writer
- Purpose: update docs in lockstep with code changes.
- Propose concrete patches/snippets; preserve anchors and links.

## Tools and hooks
- Tools to prefer:
  - Grep/Glob for fast file discovery; `rg` if available.
  - Bash for git diff, basic scripting (never destructive without explicit ask).
- Hooks (recommended):
  - PreToolUse (Edit|Write): block protected paths (exit code 2 with reason).
  - PostToolUse (Edit|Write|MultiEdit): run formatter/lint on changed files.
  - SessionStart: inject CLAUDE.md highlights into context.
  - PreCompact: trigger summarization when near context limit.

## Routing cues for subagent selection
- Orchestrator: “plan”, “orchestrate”, “multi-file”, “refactor across modules”, “end-to-end”, “first…then…”, “migration”, “config/dependency upgrade”, protected paths.
- dependency-mapper: “find usages”, “who calls X”, “what files impacted”, “blast radius”.
- code-reviewer: “review this diff”, “anything risky here?”, “ready to ship?”.
- test-runner: “run tests for this change”, “fix failing tests”.
- security-screener: “scan for secrets”, “security risks in this change”.
- doc-writer: “update docs/README/CHANGELOG”.

## Examples (quick)

Run focused review after edits:
- code-reviewer: check only files in `git diff`, cite file:line, suggest concrete fix snippets.

Before refactor:
- dependency-mapper: map callers/imports; list `testsToRun`.
- orchestrator: propose plan + todo, pause for approval with rollback steps.

After implementation:
- test-runner: run impacted tests; add/update tests as needed.
- doc-writer: update README/CHANGELOG.

## Contact and approvals
- For any change touching protected paths or high-risk categories, request human approval with:
  - Short summary of intent
  - Diff preview of key files
  - Rollback steps (commands/files)
  - Risk assessment (1–2 bullets)
