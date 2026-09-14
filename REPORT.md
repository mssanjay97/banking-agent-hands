# Architecture

The system is a thin vertical slice for giving an AI agent operational “hands” over a banking back-office web application. The flow is goal → observation → LLM decision → browser action → recorded artifact → deterministic replay.

The agent uses Playwright to observe the live browser surface and an Ollama-hosted Qwen3 model to choose the next action. The observation layer exposes accessible names, roles, IDs, selectors, values, and relevant page data without requiring a workflow-specific hardcoded sequence.

A local FastAPI banking application provides a safe live surface for the demonstration. The discovery phase interacts with this application through a real Chromium browser and records the successful actions. The resulting capability artifact is independent of the LLM transcript and can later be executed without an LLM.

The replay engine loads the artifact, resolves input parameters, performs the declared actions, verifies checkpoints, extracts declared outputs, and produces a structured result. Replay failures generate structured logs and screenshots. The handoff layer can pause automation, provide the human with the current browser state and reason for intervention, and resume the same browser session after the human completes the required action.

# Artifact schema

The capability artifact is a typed, serializable JSON document defined with Pydantic models. It contains a stable artifact ID and version, the target surface, typed inputs and outputs, ordered actions, a checkpoint, and declared business outcomes.

Each action contains an action type and structured target information. Targets can use accessible role/name information, IDs, or CSS selectors. Input values can be parameterized using placeholders such as `{{member_id}}`, allowing the same artifact to be reused for different members without rediscovery.

The artifact also declares the expected checkpoint and business outcomes. For the banking example, the successful checkpoint is the presence of the savings-balance field, while a missing member is represented as the `MEMBER_NOT_FOUND` business outcome.

This separates reusable operational knowledge from the raw LLM interaction history and makes the artifact reviewable, versionable, and deterministic.

# Determinism & error handling

Discovery uses the LLM because the system needs to determine how to accomplish a natural-language goal on an unfamiliar surface. Replay deliberately does not use the LLM. It follows the saved artifact exactly and only substitutes declared input parameters.

Before execution, replay validates the artifact's surface metadata, including vendor, tenant, and version. This allows the system to detect surface drift before executing against an incompatible application version.

Actions have bounded retries for recoverable browser failures. If an action continues to fail, replay produces a structured `HARD_FAILURE` result and captures a screenshot as evidence. Expected business outcomes are handled separately from technical failures. For example, an unknown member produces `BUSINESS_OUTCOME` rather than being treated as a browser error.

Successful replay returns declared outputs such as `savings_balance` together with a `SUCCESS` status. Replay logs redact fill values so input parameters are not persisted as raw values.

# Heterogeneity & multi-tenant

The artifact separates the capability from the underlying surface through the `Surface` model, which identifies the surface type, vendor, tenant, base URL, and version.

The current implementation focuses on a web surface, but the abstraction is intended to allow additional adapters for legacy web applications or desktop applications without changing the capability model. Targeting also combines semantic information such as accessible role/name with more specific selectors when necessary.

Artifacts can therefore be specialized by tenant or vendor version while preserving the same higher-level capability. Version validation provides an initial drift boundary: if the runtime surface version differs from the artifact's expected version, replay stops rather than blindly executing potentially stale actions.

# Escalation & handoff

The system includes a minimal but functional human-in-the-loop mechanism for situations where automation cannot safely or reliably continue.

When escalation occurs, the system captures the current browser state, creates a handoff request containing the goal, current step, reason, URL, page title, screenshot, and recovery guidance, and pauses automation.

The human operates the same live browser session rather than recreating the workflow elsewhere. After the human completes the required interaction, the handoff is marked complete and automation resumes from the existing browser state. Human intervention is recorded in evidence so the transition is observable.

This intentionally implements control transfer rather than attempting to build a full co-browsing or remote-desktop system.

# Safety

The safety layer provides configurable controls for allowed domains and action types. Navigation outside the configured domain allowlist is blocked, unsupported actions are rejected, and actions classified as risky require human confirmation rather than being executed automatically.

The demonstration uses a synthetic local banking application and fake member data, avoiding real banking credentials or customer information.

Replay logs redact values supplied through fill actions. Failure evidence contains browser screenshots only for the controlled demonstration surface. The design therefore avoids making raw secrets or unnecessary sensitive input part of the reusable artifact.

# Cuts

The implementation intentionally prioritizes a complete vertical slice over production-scale infrastructure. It does not include Kubernetes, distributed queues, multi-service orchestration, a full remote browser-control interface, or a production authentication system.

The supported live surface is currently a web application, with the architecture leaving room for additional surface adapters. The human handoff is intentionally minimal: it transfers control through the same browser session and records the intervention rather than implementing full collaborative browsing.

The system demonstrates the core engineering loop required by the assignment: an LLM discovers a workflow on a live surface, the workflow becomes a structured reusable artifact, the artifact can be replayed deterministically with parameters and outputs, failures produce evidence, safety controls constrain execution, and a human can take over and return control to automation.