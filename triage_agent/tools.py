RUNBOOKS = {
    "high_cpu": "1) Check recent deploys. 2) Check autoscaling limits. 3) Inspect top processes in logs. 4) Scale out or roll back.",
    "disk_full": "1) Identify largest directories. 2) Rotate or clear old logs. 3) Expand the disk if growth is expected.",
    "http_5xx": "1) Check latest release. 2) Check dependency health. 3) Review error logs by endpoint. 4) Roll back if errors started after a deploy.",
}

def lookup_runbook(alert_type: str) -> dict:
    """Returns the runbook steps for a known alert type (high_cpu, disk_full, http_5xx)."""
    steps = RUNBOOKS.get(alert_type.lower().strip())
    if steps:
        return {"status": "found", "alert_type": alert_type, "steps": steps}
    return {"status": "not_found", "known_types": list(RUNBOOKS)}

def classify_severity(alert_text: str) -> dict:
    """Classifies an alert as critical, high, or low based on its text."""
    text = alert_text.lower()
    if any(w in text for w in ["outage", "down", "data loss", "100%"]):
        level = "critical"
    elif any(w in text for w in ["error", "5xx", "latency", "90%"]):
        level = "high"
    else:
        level = "low"
    return {"severity": level}
