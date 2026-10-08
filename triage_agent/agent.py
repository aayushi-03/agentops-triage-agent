from google.adk.agents import Agent
from .tools import lookup_runbook, classify_severity

root_agent = Agent(
    name="triage_agent",
    model="gemini-3.5-flash",   # check Vertex AI for the current Flash model name
    description="Triages cloud alerts and suggests next steps from runbooks.",
    instruction=(
        "You are a read-only incident triage assistant. For each alert: "
        "1) classify severity with classify_severity, "
        "2) look up the matching runbook with lookup_runbook, "
        "3) reply with severity, likely cause, and numbered next steps. "
        "You only suggest actions. Never claim to have changed anything. "
        "If no runbook matches, say so."
    ),
    tools=[lookup_runbook, classify_severity],
)
