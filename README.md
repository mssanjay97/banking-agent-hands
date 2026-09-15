# Computer-Use Automation System

A thin vertical slice of a computer-use automation system for legacy banking interfaces.

The system takes a natural-language goal, uses an LLM to discover the required UI workflow against a live browser, records the successful workflow as a structured capability artifact, and then replays that artifact deterministically without using the LLM.

The project also demonstrates safety controls, business-outcome handling, failure evidence, surface drift detection, and human handoff within the same browser session.

## Architecture

~~~text
Natural-language goal
        |
        v
Browser observation
        |
        v
LLM decision loop
   observe -> decide -> act
        |
        v
Successful workflow
        |
        v
Structured capability artifact
        |
        v
Deterministic replay
        |
        +------> SUCCESS + outputs
        |
        +------> Business outcome
        |
        +------> Recoverable error -> retry
        |
        +------> Hard failure -> evidence
        |
        +------> Surface drift
        |
        +------> Human handoff
~~~

### Components

- `app/agent/` — browser observation, UI actions, LLM decisions, and agent loop
- `app/artifacts/` — artifact schema, discovery recording, artifact construction, and surface metadata
- `app/bank/` — local demo banking application
- `app/replay/` — deterministic artifact replay, error handling, logging, and failure evidence
- `app/safety/` — domain, action, and risky-action policy enforcement
- `app/handoff/` — human intervention request, browser-session handoff, and completion tracking
- `tests/` — automated tests
- `evidence/` — saved discovery artifacts, replay logs, failure screenshots, and handoff evidence

## Requirements

- Python 3.11+
- Ollama
- Qwen3 4B
- Playwright
- Chromium

The project was developed and tested on Windows with Python 3.11.

## Setup

### 1. Create and activate the environment

~~~powershell
conda create -n computer-use python=3.11
conda activate computer-use
~~~

### 2. Install Python dependencies

~~~powershell
pip install -r requirements.txt
~~~

For running the test suite:

~~~powershell
pip install pytest pytest-asyncio
~~~

### 3. Install the Playwright browser

~~~powershell
python -m playwright install chromium
~~~

### 4. Install and start Ollama

Install Ollama from:

https://ollama.com/

Then pull the model:

~~~powershell
ollama pull qwen3:4b
~~~

Verify that Ollama is running:

~~~powershell
ollama list
~~~

The application uses the local OpenAI-compatible Ollama endpoint:

~~~text
http://localhost:11434/v1
~~~

No OpenAI API key is required.

The configured model is:

~~~text
qwen3:4b
~~~

## Demo Application

The repository contains a local fake banking application so the system can be demonstrated without real credentials, financial accounts, or personally identifiable information.

Start it with:

~~~powershell
python -m uvicorn app.bank.server:app --host 127.0.0.1 --port 3000
~~~

Keep this terminal running while executing the agent, discovery, replay, and handoff demos.

The application will be available at:

~~~text
http://127.0.0.1:3000
~~~

The member search page is:

~~~text
http://127.0.0.1:3000/members
~~~

Example demo member IDs:

~~~text
12345
67890
54321
~~~

## Discovery Demo

The discovery flow uses the LLM to interact with the live browser.

Example goal:

~~~text
Find member 12345 and retrieve their savings balance.
~~~

The agent observes the browser, chooses one action at a time, executes it, observes the updated state, and continues until the requested information is available.

Run the agent:

~~~powershell
python -m app.agent.loop
~~~

This opens a visible Chromium browser and runs the LLM-driven discovery loop against the local banking application.

The agent will:

Observe the current page.
Ask the LLM for the next action.
Execute the action in the browser.
Re-observe the updated page.
Continue until the requested value is extracted.

The successful workflow is recorded and converted into a reusable artifact.

The successful discovery workflow is saved to:

evidence/discovery/discovery_actions.json

The artifact contains:

- versioned surface metadata
- typed inputs
- ordered actions
- robust interaction targets
- typed outputs
- checkpoint definition
- business outcomes

The member ID is stored as a parameter:

~~~text
{{member_id}}
~~~

rather than persisting the actual runtime input as part of the reusable workflow.

## Deterministic Replay Demo

After discovery, the saved artifact can be replayed without making new LLM decisions.

Run:

~~~powershell
python -m app.replay.engine
~~~

The replay engine:

1. Loads the saved artifact.
2. Validates the target surface.
3. Resolves runtime input parameters.
4. Executes the recorded actions in order.
5. Verifies the checkpoint.
6. Extracts the declared output.
7. Returns a structured result.

Example successful result:

~~~text
{
    "status": "SUCCESS",
    "outputs": {
        "savings_balance": "$9,320.10"
    }
}
~~~

The replay does not ask the LLM what action to perform.

## Business Outcomes

Expected application-level outcomes are represented separately from technical failures.

For example, replaying with a nonexistent member:

~~~text
99999
~~~

produces:

~~~text
{
    "status": "BUSINESS_OUTCOME",
    "error": "MEMBER_NOT_FOUND",
    "outputs": {}
}
~~~

This is different from a broken locator or application failure.

## Error Handling

Replay distinguishes between:

- `SUCCESS`
- `BUSINESS_OUTCOME`
- `DRIFT_DETECTED`
- `HARD_FAILURE`

Recoverable action errors are retried.

After the configured retry limit is reached, the replay becomes a hard failure and captures browser evidence.

Failure screenshots are stored under:

~~~text
evidence/failures/
~~~

Replay events are recorded in:

~~~text
evidence/replay/replay.jsonl
~~~

Sensitive action values such as form inputs are redacted from replay logs.

## Surface Drift

Artifacts contain surface metadata including:

- surface type
- vendor
- tenant
- version

Replay validates these values before executing the artifact.

A surface-version mismatch is reported as:

~~~text
DRIFT_DETECTED
~~~

rather than silently executing against an incompatible interface.

## Human Handoff

When automation cannot safely continue, the system can pause the existing browser session and request human intervention.

The handoff captures:

- goal
- current step
- reason for escalation
- current URL
- page title
- browser screenshot
- recovery instructions

The human operates the same browser session.

After the human completes the required interaction, automation resumes and continues from the updated browser state.

Handoff evidence is stored under:

~~~text
evidence/handoff/
~~~

Human actions are recorded separately from automated actions.

### Completing a human handoff

When the agent pauses for human intervention:

1. Perform the requested action manually in the open browser session.
2. From a second terminal, run:

~~~powershell
python -m app.handoff.complete
~~~
## Safety

The safety layer provides configurable controls for:

- allowed domains
- allowed action types
- risky actions

Navigation outside the configured domain allowlist is blocked.

Unsupported actions are blocked.

Risky actions such as money transfers require human confirmation rather than being executed automatically.

The demo application does not use real financial accounts or credentials.

## Live and No-Live Modes

### Live Mode

The default demo uses:

- a real browser
- a live local web application
- a locally running LLM
- actual browser interaction

This demonstrates the full computer-use loop.

### No-Live / Test Mode

The automated test suite runs the browser headlessly where appropriate and uses controlled test fixtures and mocks for components such as human handoff.

Run:

~~~powershell
pytest -q
~~~

Expected result:

~~~text
8 passed
~~~

The LLM test requires the configured local Ollama model to be available.

## Evidence

The repository includes generated evidence for the main workflow:

~~~text
evidence/
├── discovery/
├── replay/
├── failures/
└── handoff/
~~~

This includes:

- discovered workflow artifacts
- deterministic replay logs
- failure screenshots
- human handoff screenshots
- human intervention records

## Project Structure

~~~text
computer-use-automation/
├── app/
│   ├── agent/
│   ├── artifacts/
│   ├── bank/
│   ├── replay/
│   ├── safety/
│   └── handoff/
├── tests/
├── evidence/
│   ├── discovery/
│   ├── replay/
│   ├── failures/
│   └── handoff/
├── requirements.txt
├── pytest.ini
├── README.md
└── REPORT.md
~~~

## Testing

Run the complete automated test suite:

~~~powershell
pytest -q
~~~

The suite covers:

- browser observation
- browser actions
- LLM action generation
- safety policy
- human handoff

Current result:

~~~text
8 passed
~~~

## Design Constraints

This project intentionally focuses on a thin but complete vertical slice rather than introducing unnecessary infrastructure.

It does not require:

- Kubernetes
- distributed queues
- microservices
- production banking integrations
- real credentials
- real financial transactions

The important boundary is:

~~~text
LLM-driven discovery
        |
        v
reviewable capability artifact
        |
        v
deterministic execution
~~~

This separates the expensive and non-deterministic reasoning phase from repeatable execution.


## End-to-end demo order

Run the complete flow in this order:

**Terminal 1 — start the banking app**

~~~powershell
python -m uvicorn app.bank.server:app --host 127.0.0.1 --port 3000
~~~


Terminal 2 — run the LLM-driven agent

~~~powershell
python -m app.agent.loop
~~~

This performs the live discovery run and produces the reusable capability artifact under evidence/discovery/.

Terminal 2 — run deterministic replay

~~~powershell
python -m app.replay.engine
~~~

Replay executes the saved artifact without LLM decision-making and returns the declared output.

Optional — complete a human handoff

If the agent pauses for intervention, perform the required action in the open browser and run from another terminal:

~~~powershell
python -m app.handoff.complete
~~~

The waiting automation then resumes using the same browser session.

Evidence from the runs is stored under:

evidence/
├── discovery/
├── replay/
├── failures/
└── handoff/


So the important reviewer-facing commands become:

~~~powershell

# Start app
python -m uvicorn app.bank.server:app --host 127.0.0.1 --port 3000

# Run agent / discovery
python -m app.agent.loop

# Replay artifact
python -m app.replay.engine

# Complete human handoff when needed
python -m app.handoff.complete

# Verify tests
pytest -q

~~~