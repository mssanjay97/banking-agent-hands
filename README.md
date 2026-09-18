# Computer-Use Automation System

A thin vertical slice of a computer-use automation system for legacy banking interfaces.

The system takes a natural-language goal, uses an LLM to discover the required UI workflow against a live browser, records the successful workflow as a parameterized capability artifact, and then replays that artifact deterministically without using the LLM.

The project also demonstrates safety controls, business-outcome handling, failure evidence, surface drift detection, and human handoff within the same browser session.

## Architecture

```text
                         Natural-language goal
                                  |
                                  v
                       +-----------------------+
                       | Browser observation   |
                       | DOM / UI information  |
                       +-----------+-----------+
                                   |
                                   v
                       +-----------------------+
                       | LLM discovery loop    |
                       | observe -> decide ->   |
                       | act                    |
                       +-----------+-----------+
                                   |
                                   v
                       +-----------------------+
                       | Playwright browser    |
                       | action execution      |
                       +-----------+-----------+
                                   |
                                   | repeat
                                   v
                       +-----------------------+
                       | Discovery recorder    |
                       | + parameterization    |
                       +-----------+-----------+
                                   |
                                   v
                       +-----------------------+
                       | Discovery record      |
                       +-----------+-----------+
                                   |
                                   v
                       +-----------------------+
                       | Artifact builder      |
                       +-----------+-----------+
                                   |
                                   v
                       +-----------------------+
                       | Capability artifact   |
                       | inputs / steps /       |
                       | outputs / checkpoint  |
                       +-----------+-----------+
                                   |
                                   v
                       +-----------------------+
                       | Deterministic replay  |
                       | No LLM decisions      |
                       +-----------+-----------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
           SUCCESS          BUSINESS OUTCOME       FAILURE / DRIFT
              |                    |                    |
              v                    v                    v
          outputs             domain result       retry / evidence
                                                        |
                                                        v
                                                 human handoff

```

Components
app/agent/ — browser observation, UI actions, LLM decisions, and discovery loop
app/artifacts/ — artifact schema, discovery recording, parameterization, artifact construction, and surface metadata
app/bank/ — local demo banking application
app/replay/ — deterministic artifact replay, error handling, logging, and failure evidence
app/safety/ — domain, action, and risky-action policy enforcement
app/handoff/ — human intervention request, browser-session handoff, and completion tracking
tests/ — automated tests
evidence/ — saved discovery artifacts, replay logs, failure screenshots, and handoff evidence
Requirements
Python 3.11+
Ollama
Qwen3 4B
Playwright
Chromium

The project was developed and tested on Windows with Python 3.11.

Setup
1. Create and activate the environment
conda create -n computer-use python=3.11
conda activate computer-use
2. Install Python dependencies
pip install -r requirements.txt

For running the test suite:

pip install pytest pytest-asyncio
3. Install the Playwright browser
python -m playwright install chromium
4. Install and start Ollama

Install Ollama from:

https://ollama.com/

Then pull the configured model:

ollama pull qwen3:4b

Verify that the model is available:

ollama list

The application uses the local OpenAI-compatible Ollama endpoint:

http://localhost:11434/v1

No OpenAI API key is required.

The configured model is:

qwen3:4b
Demo Application

The repository contains a local fake banking application so the system can be demonstrated without real credentials, financial accounts, or personally identifiable information.

Start it with:

python -m uvicorn app.bank.server:app --host 127.0.0.1 --port 3000

Keep this terminal running while executing the agent, discovery, replay, and handoff demos.

The application will be available at:

http://127.0.0.1:3000

The member search page is:

http://127.0.0.1:3000/members

Example demo member IDs:

12345
67890
54321
Discovery Demo

The discovery flow uses the LLM to interact with the live browser.

Example goal:

Find member 12345 and retrieve their savings balance.

The agent observes the browser, chooses one action at a time, executes it, observes the updated page, and continues until the requested information is available.

Run the agent with:

python -m app.agent.loop `
  --goal "Find member 12345 and retrieve their savings balance." `
  --start-url "http://127.0.0.1:3000/members" `
  --capability-id "member-savings-balance" `
  --artifact-version "1" `
  --surface-type "web" `
  --surface-vendor "demo-bank" `
  --surface-tenant "demo" `
  --surface-version "1"

This opens a visible Chromium browser and runs the LLM-driven discovery loop against the local banking application.

The agent will:

Observe the current page.
Ask the LLM for the next action.
Validate the generated action.
Execute the action in the browser.
Re-observe the updated page.
Continue until the requested value is extracted and the completion target is reached.

The successful workflow is recorded and converted into a reusable capability artifact.

Discovery output is saved under:

evidence/discovery/

The discovery record contains:

capability ID
artifact version
goal
starting URL
surface metadata
discovered parameters
recorded browser actions
Parameterization

The discovery recorder converts runtime-specific values into reusable parameters.

For example, if discovery uses:

12345

as the member ID, the reusable workflow records:

{{member_id}}

instead of keeping the runtime value as part of the reusable action.

Example recorded action:

{
  "action": "fill",
  "target": {
    "role": "textbox",
    "name": "Member ID"
  },
  "value": "{{member_id}}"
}

Parameterization is generic and is not tied specifically to member IDs.

The recorder can replace parameter values both when they occur as complete values and when they occur inside larger strings.

For example:

Member 12345 account

can become:

Member {{member_id}} account

The parameterized discovery record is then passed to the artifact builder.

Capability Artifact

The artifact builder converts the discovery record into a structured capability artifact.

The artifact contains:

versioned surface metadata
typed inputs
ordered actions
interaction targets
typed outputs
checkpoint definition
business outcomes
original goal

Conceptually:

Discovery record
       |
       +-- parameters
       +-- actions
       +-- goal
       +-- surface
       |
       v
Artifact builder
       |
       v
Capability artifact

Example artifact structure:

{
  "id": "member-savings-balance",
  "version": "1",
  "surface": {
    "type": "web",
    "vendor": "demo-bank",
    "tenant": "demo",
    "version": "1"
  },
  "inputs": {
    "member_id": {
      "type": "string",
      "required": true
    }
  },
  "steps": [
    {
      "action": "fill",
      "target": {
        "role": "textbox",
        "name": "Member ID"
      },
      "value": "{{member_id}}"
    }
  ],
  "outputs": {
    "savings_balance": {
      "type": "string"
    }
  }
}
Deterministic Replay Demo

After discovery, the saved artifact can be replayed without making new LLM decisions.

Run:

python -m app.replay.engine `
  --artifact evidence/discovery/member-savings-balance_v1.artifact.json `
  --input member_id=12345 `
  --surface-type web `
  --surface-vendor demo-bank `
  --surface-tenant demo `
  --surface-version 1 `
  --allowed-domain 127.0.0.1 `
  --allowed-domain localhost

The replay engine:

Loads the saved artifact.
Validates the required runtime inputs.
Validates the target surface.
Resolves parameter placeholders.
Executes the recorded actions in order.
Detects expected business outcomes.
Extracts the declared output.
Verifies the completion checkpoint.
Returns a structured result.

Example successful result:

{
  "status": "SUCCESS",
  "outputs": {
    "savings_balance": "$9,320.10"
  }
}

The replay does not ask the LLM what action to perform.

A different member can be supplied using the same artifact:

python -m app.replay.engine `
  --artifact evidence/discovery/member-savings-balance_v1.artifact.json `
  --input member_id=67890 `
  --surface-type web `
  --surface-vendor demo-bank `
  --surface-tenant demo `
  --surface-version 1 `
  --allowed-domain 127.0.0.1 `
  --allowed-domain localhost

The workflow is reused without rediscovery.

Business Outcomes

Expected application-level outcomes are represented separately from technical failures.

For example, replaying with a nonexistent member:

99999

can produce:

{
  "status": "BUSINESS_OUTCOME",
  "error": "MEMBER_NOT_FOUND",
  "outputs": {}
}

This is different from a broken locator, browser failure, or application failure.

The distinction allows expected domain results to be handled separately from automation failures.

Error Handling

Replay distinguishes between:

SUCCESS
BUSINESS_OUTCOME
DRIFT_DETECTED
HARD_FAILURE
Recoverable errors

Transient browser/action errors are retried before being classified as a hard failure.

After the configured retry limit is reached, the replay becomes a hard failure and captures browser evidence.

Hard failures

Hard failures can include:

an action that cannot be completed after retries
inability to resolve a required target
failure to verify the final checkpoint

Failure screenshots are stored under:

evidence/failures/

Replay events are recorded in:

evidence/replay/replay.jsonl

Sensitive action values such as form inputs are redacted from replay logs.

Surface Drift

Artifacts contain surface metadata including:

surface type
vendor
tenant
version
base URL

Replay validates the runtime surface against the surface associated with the artifact before executing the workflow.

A mismatch is reported as:

DRIFT_DETECTED

rather than silently executing the artifact against an incompatible interface.

Surface metadata is currently supplied as configuration.

The prototype does not attempt to autonomously infer arbitrary vendor, tenant, or version information from the website.

Completion Checkpoint

A successful discovery records a completion target.

The checkpoint is stored in the capability artifact and verified during replay after the recorded actions have executed.

For example, a checkpoint can require a particular semantic element to be present:

{
  "type": "element_present",
  "target": {
    "role": "heading",
    "name": "Savings Balance"
  }
}

If the expected completion target cannot be found, replay does not report a false success.

Human Handoff

When automation cannot safely continue, the system can pause the existing browser session and request human intervention.

The handoff captures:

goal
current step
reason for escalation
current URL
page title
browser screenshot
recovery instructions

The human operates the same browser session.

After the human completes the required interaction, automation resumes using the updated browser state.

Handoff evidence is stored under:

evidence/handoff/

Human actions are recorded separately from automated actions.

Completing a human handoff

When the agent pauses for human intervention:

Perform the requested action manually in the open browser session.
From a second terminal, run:
python -m app.handoff.complete

The waiting automation can then resume using the same browser session.

Safety

The safety layer provides configurable controls for:

allowed domains
allowed action types
risky actions

Navigation outside the configured domain allowlist is blocked.

Unsupported actions are blocked.

Risky actions can require human confirmation rather than being executed automatically.

The demo application does not use real financial accounts or credentials.

Live and Test Modes
Live Mode

The default demonstration uses:

a real Chromium browser
a live local web application
a locally running LLM
actual browser interaction
LLM-driven action selection

This demonstrates the complete computer-use discovery loop.

Test Mode

The automated test suite uses controlled fixtures and mocks where appropriate.

Run:

pytest -q

The test suite covers core components including:

browser interaction
LLM action generation
safety policy
human handoff behavior
Evidence

The repository keeps reviewer-visible evidence for the main workflow:

evidence/
├── discovery/
├── replay/
├── failures/
└── handoff/

This can include:

discovered workflow records
capability artifacts
deterministic replay logs
failure screenshots
human handoff screenshots
human intervention records

The evidence directory makes the automation behavior inspectable rather than relying only on console output.

Project Structure
computer-use-automation/
|
├── app/
│   |
│   ├── agent/
│   │   ├── actions.py
│   │   ├── browser.py
│   │   ├── llm.py
│   │   └── loop.py
│   │
│   ├── artifacts/
│   │   ├── builder.py
│   │   ├── discovery_recorder.py
│   │   ├── schema.py
│   │   └── surface.py
│   │
│   ├── bank/
│   │   ├── data.py
│   │   └── server.py
│   │
│   ├── replay/
│   │   ├── engine.py
│   │   ├── errors.py
│   │   ├── evidence.py
│   │   └── logging.py
│   │
│   ├── safety/
│   │   └── policy.py
│   │
│   └── handoff/
│       ├── actions.py
│       ├── complete.py
│       ├── controller.py
│       └── manager.py
│
├── tests/
│
├── evidence/
│   ├── discovery/
│   ├── replay/
│   ├── failures/
│   └── handoff/
│
├── requirements.txt
├── pytest.ini
├── README.md
└── REPORT.md
Testing

Run the automated test suite:

pytest -q

The suite covers:

browser observation
browser actions
LLM action generation
safety policy
human handoff

The LLM-related test requires the configured local Ollama model to be available.

Design Constraints

This project intentionally focuses on a thin but complete vertical slice rather than introducing unnecessary infrastructure.

It does not require:

Kubernetes
distributed queues
microservices
production banking integrations
real credentials
real financial transactions

The important architectural boundary is:

LLM-driven discovery
        |
        v
Parameterized capability artifact
        |
        v
Deterministic execution

The goal is to demonstrate how an expensive, non-deterministic computer-use discovery process can produce a reusable capability that is subsequently executed without repeated LLM reasoning.

Current Limitations

The current implementation is a prototype focused on a web-based vertical slice.

Surface metadata

Surface metadata such as vendor, tenant, and version is supplied as configuration and validated during replay. It is not automatically inferred from arbitrary websites.

Web-only replay

Replay currently targets web surfaces through Playwright.

UI drift

Artifacts depend on their recorded interaction targets remaining resolvable. Significant UI changes can therefore cause replay failure or drift detection.

Demonstration environment

The included banking application is a local fake banking environment intended for safe demonstration and testing.

Lightweight artifact format

The artifact schema is intentionally compact and designed to demonstrate the architecture rather than provide a production-grade workflow specification.

Future Extensions

Potential extensions include:

richer selector fallback strategies
stronger UI drift detection
automatic surface identification
artifact compatibility scoring
support for additional browser surfaces
desktop application automation
richer typed input validation
artifact signing and integrity verification
capability version management
artifact migration between UI versions
stronger risky-action approval workflows
more sophisticated business outcome definitions
replay performance metrics
capability reuse and execution analytics
End-to-End Demo Order

Run the complete flow in this order.

Terminal 1 — Start the banking app
python -m uvicorn app.bank.server:app --host 127.0.0.1 --port 3000

Keep this terminal running.

Terminal 2 — Run the LLM-driven discovery
python -m app.agent.loop `
  --goal "Find member 12345 and retrieve their savings balance." `
  --start-url "http://127.0.0.1:3000/members" `
  --capability-id "member-savings-balance" `
  --artifact-version "1" `
  --surface-type "web" `
  --surface-vendor "demo-bank" `
  --surface-tenant "demo" `
  --surface-version "1"

This performs the live discovery run and produces the reusable capability artifact under:

evidence/discovery/
Terminal 2 — Run deterministic replay
python -m app.replay.engine `
  --artifact evidence/discovery/member-savings-balance_v1.artifact.json `
  --input member_id=12345 `
  --surface-type web `
  --surface-vendor demo-bank `
  --surface-tenant demo `
  --surface-version 1 `
  --allowed-domain 127.0.0.1 `
  --allowed-domain localhost

Replay executes the saved artifact without LLM decision-making and returns the declared output.

Optional — Replay with a different member
python -m app.replay.engine `
  --artifact evidence/discovery/member-savings-balance_v1.artifact.json `
  --input member_id=67890 `
  --surface-type web `
  --surface-vendor demo-bank `
  --surface-tenant demo `
  --surface-version 1 `
  --allowed-domain 127.0.0.1 `
  --allowed-domain localhost

The same artifact is reused with a different runtime input.

Optional — Complete a human handoff

If the agent pauses for intervention, perform the required action in the open browser and run from another terminal:

python -m app.handoff.complete

The waiting automation then resumes using the same browser session.

Optional — Run tests
pytest -q

Evidence from the runs is stored under:

evidence/
├── discovery/
├── replay/
├── failures/
└── handoff/

The primary reviewer-facing commands are:

# Start local banking application
python -m uvicorn app.bank.server:app --host 127.0.0.1 --port 3000

# Run LLM-driven discovery
python -m app.agent.loop `
  --goal "Find member 12345 and retrieve their savings balance." `
  --start-url "http://127.0.0.1:3000/members" `
  --capability-id "member-savings-balance" `
  --artifact-version "1" `
  --surface-type "web" `
  --surface-vendor "demo-bank" `
  --surface-tenant "demo" `
  --surface-version "1"

# Replay the generated artifact
python -m app.replay.engine `
  --artifact evidence/discovery/member-savings-balance_v1.artifact.json `
  --input member_id=12345 `
  --surface-type web `
  --surface-vendor demo-bank `
  --surface-tenant demo `
  --surface-version 1 `
  --allowed-domain 127.0.0.1 `
  --allowed-domain localhost

# Complete a human handoff when required
python -m app.handoff.complete

# Run tests
pytest -q
Core Design Principle

The central design principle of this project is:

Use an LLM where reasoning is valuable, then remove the LLM from the repeated execution path.

The LLM is used to discover how a workflow can be performed on an unfamiliar interface.

The resulting interaction is transformed into a parameterized, versioned capability artifact.

Replay then executes that artifact deterministically, validates the target surface, handles recoverable failures, detects business outcomes and drift, verifies completion, and produces evidence.

                 ONE-TIME DISCOVERY
                    LLM + Browser
                          |
                          v
                Parameterized Artifact
                          |
                          v
                 REPEATED EXECUTION
                       No LLM
                          |
             +------------+------------+
             |            |            |
             v            v            v
          SUCCESS     BUSINESS      FAILURE
                       OUTCOME       / DRIFT

The separation between LLM-driven discovery and deterministic replay is the foundation of the system.