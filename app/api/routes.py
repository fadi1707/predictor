from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from app.db import *
from app.execution import run_on_target
from app.inventory import discover_target, health_model
from app.job_engine import process_job, resume_job_from_approval
from app.fwc26_predictor import predict_fwc26_winner
from app.klement_model import match_probability, simulate_knockout_tournament
from app.klement_published_forecast import load_klement_2026_forecast
from app.models import *
from app.observability import get_metrics
from app.patch_engine import preview_patch
from app.planner import decompose_goal, recommend_strategies
from app.policy import can_approve, can_queue_job, can_queue_workflow, load_policies
from app.secrets import load_secret_profiles, masked_secret_profile
from app.services_chat import handle_chat
from app.targets import load_targets
from app.workflow_engine import process_workflow, resume_workflow_from_approval
from app.workflow_graph import workflow_graph
from app.diagnostics import workflow_diagnostics
from app.windows_adapter import list_services, service_status, restart_service, windows_health

router=APIRouter()

@router.on_event("startup")
def startup():
    init_db(); log_event("info","api","startup complete")

@router.get("/", response_class=HTMLResponse)
def index():
    return '''<!doctype html><html><head><title>Predictor</title></head><body style="font-family:Arial;max-width:1180px;margin:40px auto;"><h1>Predictor</h1><p>Klement-style FIFA World Cup prediction engine.</p><p><button onclick="load('/api/health/local')">Health</button><button onclick="load('/api/targets')">Targets</button><button onclick="load('/api/metrics')">Metrics</button></p><pre id="o" style="background:#111;color:#ddd;padding:16px;min-height:340px;white-space:pre-wrap;"></pre><script>async function load(u){let r=await fetch(u);o.textContent=JSON.stringify(await r.json(),null,2)}</script></body></html>'''

@router.post("/api/chat")
def chat(req: ChatRequest): return handle_chat(req.text)
@router.post("/api/goals")
def goal(req: GoalRequest):
    if not can_queue_workflow(): raise HTTPException(403,"Current role cannot queue workflows")
    wf=decompose_goal(req.goal,req.target_name); wid=create_workflow(req.goal,req.target_name,wf); return {"workflow_id":wid,"definition":wf}
@router.get("/api/recommend/{target_name}")
def recommend(target_name: str, goal: str): return {"target_name":target_name,"goal":goal,"recommendations":recommend_strategies(target_name,goal)}
@router.get("/api/workflows")
def workflows(limit:int=100): return {"items":list_workflows(limit)}
@router.post("/api/workflows/{workflow_id}/run")
def run_workflow(workflow_id:int): return process_workflow(workflow_id)
@router.get("/api/workflows/{workflow_id}/graph")
def graph(workflow_id:int): return workflow_graph(workflow_id)
@router.post("/api/jobs")
def make_job(req: QueueJobRequest):
    if not can_queue_job(req.job_type): raise HTTPException(403,"Current role cannot queue this job type")
    return {"job_id":create_job(req.job_type,req.target_name,req.payload)}
@router.post("/api/jobs/command")
def make_cmd(req: TargetCommandRequest):
    if not can_queue_job("command"): raise HTTPException(403,"Current role cannot queue command jobs")
    return {"job_id":create_job("command",req.target_name,{"command":req.command})}
@router.post("/api/jobs/{job_id}/run")
def run_job(job_id:int): return process_job(job_id)
@router.get("/api/jobs")
def jobs(limit:int=100): return {"items":list_jobs(limit)}
@router.get("/api/approvals")
def approvals(limit:int=50): return {"items":list_approvals(limit)}
@router.post("/api/approval")
def approve(decision: ApprovalDecision):
    if not can_approve(): raise HTTPException(403,"Current role cannot approve actions")
    a=get_approval(decision.approval_id)
    if not a: raise HTTPException(404,"Approval not found")
    if a["status"]!="pending": raise HTTPException(400,f"Approval already {a['status']}")
    if decision.decision=="reject":
        set_approval_status(decision.approval_id,"rejected"); return {"status":"rejected","approval_id":decision.approval_id}
    set_approval_status(decision.approval_id,"approved")
    m=a["metadata"]
    if m.get("workflow_id"): return {"status":"approved","auto_resumed":True,"resume_result":resume_workflow_from_approval(decision.approval_id)}
    if m.get("job_id"): return {"status":"approved","auto_resumed":True,"resume_result":resume_job_from_approval(decision.approval_id)}
    return {"status":"approved","approval_id":decision.approval_id}
@router.get("/api/validation_runs")
def validations(limit:int=100): return {"items":list_validation_runs(limit)}
@router.get("/api/incidents")
def incidents(limit:int=100): return {"items":list_incidents(limit)}
@router.get("/api/events")
def events(limit:int=100): return {"items":list_events(limit)}
@router.get("/api/chat_history")
def history(limit:int=50): return {"items":list_chat(limit)}
@router.get("/api/metrics")
def metrics(): return get_metrics()
@router.get("/api/targets")
def targets(): return load_targets()
@router.get("/api/policies")
def policies(): return load_policies()
@router.get("/api/secrets")
def secrets():
    p=load_secret_profiles(); return {"profiles":{n:masked_secret_profile(n) for n in p.get("profiles",{})}}
@router.get("/api/inventory")
def inventory(limit:int=100): return {"items":list_inventory(limit)}
@router.post("/api/discover/{target_name}")
def discover(target_name:str): return {"target_name":target_name,"inventory":discover_target(target_name)}
@router.get("/api/health/{target_name}")
def health(target_name:str): return health_model(target_name)
@router.get("/api/rollbacks")
def rollbacks(limit:int=100): return {"items":list_rollbacks(limit)}
@router.post("/api/rollback/restore")
def restore(req: RestoreRollbackRequest):
    import shutil
    rb=get_rollback(req.rollback_id)
    if not rb: raise HTTPException(404,"Rollback not found")
    shutil.copy2(rb["backup_path"],rb["rel_path"]); return {"ok":True,"rollback":rb}
@router.post("/api/run_on_target")
def run_target(req: TargetCommandRequest): return run_on_target(req.target_name, req.command)

@router.post("/api/klement/match")
def klement_match(req: KlementMatchRequest):
    try:
        return match_probability(req.team_a, req.team_b)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@router.post("/api/klement/tournament")
def klement_tournament(req: KlementTournamentRequest):
    try:
        return simulate_knockout_tournament(req.teams, req.simulations, req.seed)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@router.get("/api/klement/fwc26/winner")
def klement_fwc26_winner(mode: str = "published", simulations: int = 10000, seed: int | None = None):
    try:
        if mode == "published":
            return load_klement_2026_forecast()
        if mode != "simulation":
            raise ValueError("mode must be 'published' or 'simulation'")
        req = FWC26WinnerRequest(simulations=simulations, seed=seed)
        return predict_fwc26_winner(req.simulations, req.seed)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@router.post("/api/klement/fwc26/winner")
def klement_fwc26_winner_post(req: FWC26WinnerRequest):
    try:
        if req.mode == "published":
            return load_klement_2026_forecast()
        return predict_fwc26_winner(req.simulations, req.seed)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/api/windows/health")
def windows_native_health():
    return windows_health()

@router.get("/api/windows/services")
def windows_services():
    return list_services()

@router.get("/api/windows/services/{service_name}/status")
def windows_service_status(service_name: str):
    return service_status(service_name)

@router.post("/api/windows/services/{service_name}/restart")
def windows_service_restart(service_name: str):
    if not can_approve():
        raise HTTPException(403, "Current role cannot approve/restart services")
    return restart_service(service_name)

@router.get("/api/patch/preview")
def patch_preview(file_path: str, replace_from: str, replace_to: str):
    return preview_patch(file_path, replace_from, replace_to)

@router.get("/api/workflows/{workflow_id}/diagnostics")
def workflow_diag(workflow_id: int):
    return workflow_diagnostics(workflow_id)
