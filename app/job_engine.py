from app.config import settings
from app.db import create_approval, create_incident, get_approval, get_job, insert_validation_run, lease_next_job, set_job_state
from app.execution import run_on_target
from app.policy import assess_command

def process_job(jid):
    j=get_job(jid)
    if not j: return {"ok":False,"error":f"job {jid} not found"}
    target=j["target_name"]; cmd=j["payload"].get("command","uname -a")
    pol=assess_command(cmd,target)
    if not pol["allowed"]:
        set_job_state(jid,"failed",summary=pol["reason"],lease_owner="",lease_expires_at=0); create_incident("job",jid,target,"blocked_command","warning","blocked command",{"command":cmd}); return {"ok":False,"error":pol["reason"]}
    if pol.get("requires_approval") and settings.autonomy_mode=="approval":
        aid=create_approval("job_step",cmd,{"job_id":jid,"target_name":target,"auto_resume":True})
        set_job_state(jid,"waiting_for_approval",summary=f"waiting for approval {aid}",lease_owner="",lease_expires_at=0)
        return {"ok":True,"status":"waiting_for_approval","approval_id":aid}
    res=run_on_target(target,cmd); status="success" if res.get("ok") else "failed"
    insert_validation_run("job",jid,0,status,{"result":res})
    set_job_state(jid,"completed" if res.get("ok") else "failed",1,status,"",0)
    return {"ok":res.get("ok"),"job_id":jid,"result":res}
def resume_job_from_approval(aid):
    a=get_approval(aid); meta=a["metadata"]; jid=meta.get("job_id"); target=meta.get("target_name","local")
    res=run_on_target(target,a["command_text"])
    insert_validation_run("job",jid,0,"success" if res.get("ok") else "failed",{"approved_command_result":res})
    set_job_state(jid,"completed" if res.get("ok") else "failed",1,"approved command executed","",0)
    return {"ok":res.get("ok"),"job_id":jid,"result":res}
def lease_and_process_next(worker):
    j=lease_next_job(worker)
    if not j: return None
    return process_job(j["id"])
