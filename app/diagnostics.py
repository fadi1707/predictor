from app.db import get_workflow, list_validation_runs, list_incidents

def workflow_diagnostics(workflow_id: int) -> dict:
    wf = get_workflow(workflow_id)
    validations = [v for v in list_validation_runs(500) if v.get("owner_type") == "workflow" and v.get("owner_id") == workflow_id]
    incidents = [i for i in list_incidents(500) if i.get("owner_type") == "workflow" and i.get("owner_id") == workflow_id]
    return {
        "workflow": wf,
        "validation_count": len(validations),
        "incident_count": len(incidents),
        "validations": validations,
        "incidents": incidents,
    }
