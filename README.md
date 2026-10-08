# Cloud Incident Triage Agent

A small, **read-only** AI agent built with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/) that triages cloud alerts. Given an alert, it classifies severity, looks up a matching runbook, and suggests next steps. It never changes any infrastructure.

This is the capstone project of my **AgentOps on GCP** learning series: I build the agent first, then add the operations layer around it (observability, evaluation, security, cost control) and write about what I learn.

> All data in this repo is **synthetic**. No employer, client or personal data is used.

## How it works

```
Alert text ──► triage_agent (Gemini via Vertex AI)
                 ├─ tool: classify_severity  → critical / high / low
                 └─ tool: lookup_runbook     → runbook steps for known alert types
               ──► severity + likely cause + numbered next steps
```

## Repository structure

```
.
├── triage_agent/            # the agent folder ADK runs and deploys
│   ├── __init__.py
│   ├── agent.py             # defines root_agent (model, instructions, tools)
│   ├── tools.py             # classify_severity, lookup_runbook (synthetic data)
│   ├── requirements.txt
│   └── .env                 # local settings, NOT committed
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.10 or later
- [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install)
- A Google Cloud project with billing enabled
- Git

## 1. Google Cloud setup (one time)

1. Create a Google Cloud project and link a billing account.
2. **Set a budget alert** (Billing → Budgets & alerts), for example at 50%, 90% and 100%.
3. Log in and enable the required APIs:

```bash
gcloud auth login
gcloud auth application-default login      # credentials used by local code
gcloud config set project YOUR_PROJECT_ID

gcloud services enable aiplatform.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com
```

## 2. Local setup

```bash
git clone https://github.com/YOUR_USERNAME/agentops-triage-agent.git
cd agentops-triage-agent

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r triage_agent/requirements.txt
```

Create `triage_agent/.env` (this file is git-ignored):

```
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=global
```

> **Model and location:** set the model name in `triage_agent/agent.py`. Newer Gemini models may not be served in every regional location. If you see a `404 NOT_FOUND` for the model, use `GOOGLE_CLOUD_LOCATION=global` or choose a model your project can access (check Vertex AI Model Garden).

## 3. Run locally

Run all commands from the **repo root** (the folder that contains `triage_agent/`).

```bash
adk run triage_agent            # chat in the terminal
adk web --port 8000             # browser UI at http://localhost:8000
```

`adk web` is for development and debugging only, not production.

Example prompts:

- `ALERT: checkout service returning 5xx errors, latency 4s`
- `ALERT: disk 100% on batch-worker`
- `ALERT: unknown sensor noise` (expected: the agent says no runbook matches)

In the web UI, open the trace/events view to see each tool call the agent made.

## 4. Deploy to Cloud Run

```bash
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=us-central1       # Cloud Run region

adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$GOOGLE_CLOUD_LOCATION \
  --service_name=triage-agent \
  triage_agent \
  -- --no-allow-unauthenticated
```

The service is **private** (`--no-allow-unauthenticated`), so every call needs an identity token.

After deploying, make sure the Cloud Run service has:

- Environment variables `GOOGLE_GENAI_USE_VERTEXAI=1`, `GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID` and `GOOGLE_CLOUD_LOCATION=global` (the model location, separate from the Cloud Run region).
- A service account with the **Vertex AI User** role (`roles/aiplatform.user`).

## 5. Call the deployed agent

The ADK server has no endpoint at `/`. Create a session first, then send your message to `/run`.

```bash
URL="https://YOUR_SERVICE_URL"                 # printed at the end of the deploy
TOKEN=$(gcloud auth print-identity-token)      # expires after about an hour
```

**a) Confirm the app name** (the folder name, `triage_agent`, not the service name):

```bash
curl -H "Authorization: Bearer $TOKEN" $URL/list-apps
```

**b) Create a session:**

```bash
curl -X POST "$URL/apps/triage_agent/users/demo-user/sessions/s1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**c) Send an alert:**

```bash
curl -X POST "$URL/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "triage_agent",
    "user_id": "demo-user",
    "session_id": "s1",
    "new_message": {
      "role": "user",
      "parts": [{"text": "ALERT: disk 100% on batch-worker"}]
    }
  }'
```

The response is a JSON list of events: tool calls, tool results, and the final answer. To print only the final text (requires `jq`):

```bash
... | jq '.[-1].content.parts[0].text'
```

Use a new session id (`s2`, `s3`, ...) for a fresh conversation.

**Optional: browse the API in a browser** through an authenticated local proxy:

```bash
gcloud run services proxy triage-agent --region us-central1
# then open http://localhost:8080/docs
```

## Clean up (avoid surprise costs)

```bash
gcloud run services delete triage-agent --region us-central1
```
