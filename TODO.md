# Slack → Claude Code & Codex Integration TODO

## Goal
Use Slack, via the existing Nemo bot, as a controlled interface for running Claude Code and Codex on the Mac mini without weakening the current Claude-agent chat flow.

## Principles
- Treat Slack-triggered local code execution as a separate trust boundary from normal Claude chat.
- Keep the existing Claude API assistant path as the default behavior.
- Run long-lived code tasks outside the Slack event handler path.
- Use a bounded concurrency model with backpressure rather than unbounded fire-and-forget workers.
- Restrict execution to approved users, approved channels, and approved working directories.
- Prefer an implementation that is auditable, deterministic, and easy to operate on a single Mac mini.

---

## Phase 1: Design Decisions

### 1. Pick the Codex integration path
- [ ] Choose one approach and document the reason:
  - Codex CLI via subprocess
  - OpenAI API via `openai`
- [ ] Record the initial model / command choice and expected auth mechanism
- [ ] Decide whether Claude Code and Codex should share one execution wrapper or use separate wrappers

### 2. Define execution policy before writing code
- [ ] Decide which Slack users may run `code:` and `codex:` commands
- [ ] Decide which channels may run these commands
- [ ] Decide the allowed working directory strategy:
  - single fixed repo root from config
  - small allowlist of repo roots
  - per-command path argument constrained to an allowlist
- [ ] Decide whether agent-autonomous invocation of these tools is allowed at all
- [ ] If autonomous invocation is allowed later, require a separate explicit enable flag

### 3. Pick the background execution model
- [ ] Choose the job runner design before implementing Slack command routing
- [ ] Prefer a bounded `ThreadPoolExecutor` plus a small in-memory job registry for the first version
- [ ] Define backpressure behavior when the worker pool is full:
  - reject new jobs with a clear Slack message, or
  - queue a very small number of waiting jobs
- [ ] Define per-job state transitions:
  - queued
  - running
  - succeeded
  - failed
  - timed_out
- [ ] Decide whether one user can run multiple concurrent jobs

---

## Phase 2: Safe Execution Layer

### 4. Add a shared subprocess runner
- [ ] Create a shared execution helper for CLI-backed tools
- [ ] Use `subprocess` with:
  - explicit command argv, not shell strings
  - bounded timeout
  - captured stdout/stderr
  - explicit working directory
  - sanitized environment
- [ ] Return structured results:
  - status
  - stdout
  - stderr
  - exit code
  - timed_out
  - elapsed time
- [ ] Truncate very large output and indicate truncation clearly
- [ ] Resolve and validate working directories with canonical paths:
  - expand user/home references
  - resolve symlinks with `realpath`
  - compare the resolved path against approved roots
  - reject paths that escape the allowlist after resolution

### 5. Add Claude Code tool
- [ ] Create `nemo/tools/claude_code_tool.py`
- [ ] Implement a wrapper around the approved Claude Code CLI invocation
- [ ] Validate the requested working directory against config before execution
- [ ] Convert subprocess results into Slack-safe text

### 6. Add Codex tool
- [ ] Create `nemo/tools/codex_tool.py`
- [ ] Implement the chosen path:
  - CLI wrapper if using Codex CLI
  - API client wrapper if using OpenAI API
- [ ] If using the API path, add `openai` to `requirements.txt`
- [ ] Normalize Codex results into the same structured format used by Claude Code

---

## Phase 3: Slack Routing And Delivery

### 7. Route command prefixes in `nemo/app.py`
- [ ] Update `_handle()` in `nemo/app.py` to branch on message prefix:
  - `code: <task>` runs Claude Code
  - `codex: <task>` runs Codex
  - everything else stays on the current Claude API path
- [ ] Keep command-routing logic separate from the normal Claude conversation path
- [ ] Decide how command messages affect conversation history:
  - do not store them in Claude chat history, or
  - store a short summary only

### 8. Prevent Slack handler blocking
- [ ] Acknowledge command requests immediately in Slack
- [ ] Run code tasks in background work rather than inside the synchronous event handler
- [ ] Post the final result back into the originating thread
- [ ] Ensure errors and timeouts are also posted back into the thread

### 9. Add progress updates for long-running jobs
- [ ] Post an immediate acknowledgement reply when a job is accepted
- [ ] Add periodic thread heartbeats for jobs that run longer than a short threshold
- [ ] Include elapsed time in heartbeat messages
- [ ] Stop heartbeats cleanly when the job completes, fails, or times out
- [ ] Ensure heartbeat frequency is low enough to avoid Slack spam

### 10. Handle long output correctly
- [ ] Add a Slack response formatter that:
  - sends normal replies for short output
  - splits longer plain-text output into threaded chunks when reasonable
  - uploads a snippet or file when output is too large for clean message delivery
- [ ] Include command metadata in the reply:
  - tool used
  - working directory
  - exit status
  - timeout if applicable

---

## Phase 4: Config And Guardrails

### 11. Expand config
- [ ] Add env vars for:
  - allowed Slack user IDs
  - allowed Slack channel IDs
  - default working directory
  - allowed working directory roots
  - command timeout
  - max returned output size
  - max concurrent jobs
  - optional heartbeat interval
  - optional feature flag for autonomous agent tool use
- [ ] Add `OPENAI_API_KEY` only if the Codex API path is chosen
- [ ] Fail closed when command-execution config is missing or invalid

### 12. Add security controls
- [ ] Reject commands from unauthorized users
- [ ] Reject commands in unauthorized channels
- [ ] Reject working directories outside approved roots
- [ ] Use resolved canonical paths for all working-directory authorization checks
- [ ] Limit concurrent code-execution jobs
- [ ] Avoid passing unnecessary secrets into subprocess environments
- [ ] Log who ran what, where, and whether it succeeded

---

## Phase 5: Optional Agent Tool Registration

### 13. Do not expose code-execution tools to Claude by default
- [ ] Leave `claude_code` and `codex` out of `nemo/tools/__init__.py` for the first version
- [ ] If autonomous tool use is later enabled:
  - gate it behind a config flag
  - require the same authz and working-directory checks
  - add clear audit logging around every invocation
  - allow it only after the manual prefix flow has met a stability gate:
    - at least 2 weeks of manual use
    - no unexpected executions
    - no authz bypasses
    - no timeout handling escapes

---

## Phase 6: Operations On The Mac Mini

### 14. Add `launchd` persistence
- [ ] Create `~/Library/LaunchAgents/com.nemo.bot.plist`
- [ ] Point it to the venv Python and `run.py`
- [ ] Set `KeepAlive` and `RunAtLoad` to true
- [ ] Set `PATH` so required CLIs are resolvable
- [ ] Configure stdout/stderr log locations

### 15. Verify operational behavior
- [ ] Load the agent with `launchctl`
- [ ] Confirm the bot starts on login / restart
- [ ] Confirm the bot restarts after failure
- [ ] Confirm the execution environment can resolve required CLIs and env vars
- [ ] Confirm the bot reconnects cleanly after a temporary network drop
- [ ] Confirm the Mac mini power settings do not allow sleep to interrupt the bot or long-running jobs

---

## Phase 7: Testing And Validation

### 16. Add a safe test strategy before live rollout
- [ ] Test command routing without using the production Slack workspace by default
- [ ] Prefer either:
  - a separate Slack workspace for development, or
  - a mock Slack posting layer for local tests
- [ ] Add unit tests for:
  - prefix routing
  - authz checks
  - canonical-path validation
  - output truncation / formatting
  - timeout handling
- [ ] Add an integration-style test path for background jobs and threaded result posting
- [ ] Run a manual staging checklist before enabling command execution in the primary workspace

---

## Suggested Delivery Order
- [ ] First: decide Codex path and execution policy
- [ ] Second: choose the bounded background execution model and backpressure behavior
- [ ] Third: build the shared execution wrapper
- [ ] Fourth: add prefix routing plus background execution
- [ ] Fifth: add progress heartbeats and Slack output formatting
- [ ] Sixth: add config guardrails, authz, and canonical-path checks
- [ ] Seventh: validate in a safe test environment
- [ ] Eighth: set up `launchd` and Mac mini power/network behavior
- [ ] Ninth: consider autonomous agent tool registration only after the defined stability gate is met

## Acceptance Criteria
- [ ] Normal Nemo chat still works unchanged for non-command messages
- [ ] `code:` requests run only for approved users/channels and approved directories
- [ ] `codex:` requests run only for approved users/channels and approved directories
- [ ] Long-running jobs do not block Slack event handling
- [ ] Long-running jobs provide low-noise progress updates in-thread
- [ ] Results are posted back to the correct thread with usable formatting
- [ ] Timeouts, non-zero exits, and internal exceptions are visible to the user
- [ ] Working-directory checks are based on resolved canonical paths, not naive string matching
- [ ] The bot survives Mac mini restarts and process crashes
- [ ] The bot reconnects cleanly after short network interruptions

## Notes
- The bot already uses Socket Mode, so no inbound port or ngrok is required.
- The current Slack handler in `nemo/app.py` is synchronous, so background execution is a real implementation requirement.
- A bounded worker model is required; unbounded background threads are not acceptable.
- The current conversation store is in-memory and keyed by channel, so command-routing behavior should be kept separate from Claude chat history unless intentionally summarized.
- Working-directory authorization must use canonical resolved paths to avoid traversal and symlink escape bugs.
- Registering local code-execution tools in the Claude tool loop is a separate security decision, not a default extension of the current tool set.
