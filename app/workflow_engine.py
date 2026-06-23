import re
from app.config import settings
from app.db import create_approval, create_incident, create_rollback, create_workflow, get_approval, get_workflow, insert_validation_run, lease_next_workflow, log_event, set_workflow_state
from app.execution import run_on_target, workspace_backup
from app.planner import decompose_goal
from app.policy import assess_command

def valid(result, expect_stdout=None, expect_regex=None):
    ok=result.get("ok",False); out=result.get("stdout","")
    if expect_stdout is not None: ok = ok and out.strip()==expect_stdout
    if expect_regex is not None: ok = ok and bool(re.search(expect_regex,out))
    return {"status":"success" if ok else "failed","result":result}

def process_workflow(wid):
    wf=get_workflow(wid)
    if not wf: return {"ok":False,"error":f"workflow {wid} not found"}
    steps=wf["definition"]["steps"]; target=wf["target_name"]; idx=wf["current_step"]
    while idx < len(steps):
        s=steps[idx]; kind=s["kind"]
        if kind=="backup_file":
            b=workspace_backup(wid,s["file_path"])
            if not b["ok"]:
                set_workflow_state(wid,"failed",idx,b["error"]," ",0); create_incident("workflow",wid,target,"backup_failed","warning","backup failed",b); return {"ok":False,"error":b["error"]}
            create_rollback("workflow",wid,target,b["target"],b["backup_path"],[{"action":"backup_file","file_path":s["file_path"]}])
            set_workflow_state(wid,"running",idx+1,f"completed step {idx+1}"); idx+=1; continue
        if kind=="patch_file":
            from app.patch_engine import apply_patch
            result = apply_patch("workflow", wid, target, s["file_path"], s["replace_from"], s["replace_to"])
            status = "success" if result.get("ok") else "failed"
            insert_validation_run("workflow", wid, idx, status, {"patch_step": s, "result": result})
            if not result.get("ok"):
                set_workflow_state(wid, "failed", idx, result.get("error", "patch failed"), "", 0)
                create_incident("workflow", wid, target, "patch_failed", "warning", "patch failed", result)
                return {"ok": False, "error": result.get("error", "patch failed")}
            set_workflow_state(wid, "running", idx + 1, f"completed step {idx+1}")
            idx += 1
            continue
        cmd=s["command"]; pol=assess_command(cmd,target)
        if not pol["allowed"]:
            set_workflow_state(wid,"failed",idx,pol["reason"],"",0); create_incident("workflow",wid,target,"blocked_command","warning","blocked command",{"command":cmd,"reason":pol["reason"]}); return {"ok":False,"error":pol["reason"]}
        if s.get("requires_approval") or (pol.get("requires_approval") and settings.autonomy_mode=="approval"):
            aid=create_approval("workflow_step",cmd,{"workflow_id":wid,"step_index":idx,"target_name":target,"auto_resume":True,"action":pol.get("action"),"risk":pol.get("risk")})
            set_workflow_state(wid,"waiting_for_approval",idx,f"waiting for approval {aid}","",0)
            return {"ok":True,"workflow_id":wid,"status":"waiting_for_approval","approval_id":aid}
        res=run_on_target(target,cmd); vr=valid(res,s.get("expect_stdout"),s.get("expect_regex"))
        insert_validation_run("workflow",wid,idx,vr["status"],{"step":s,"validation":vr})
        if vr["status"]=="failed":
            action=s.get("on_failure","stop")
            if action=="continue":
                idx+=1; set_workflow_state(wid,"running",idx,f"continued after failed validation at step {idx}"); continue
            if action=="subworkflow" and s.get("subworkflow_goal"):
                sub=decompose_goal(s["subworkflow_goal"],target); sid=create_workflow(s["subworkflow_goal"],target,sub,parent_workflow_id=wid)
                set_workflow_state(wid,"failed",idx,f"subworkflow {sid} created after failure","",0)
                create_incident("workflow",wid,target,"subworkflow_created","warning",f"Created subworkflow {sid}",{"result":res})
                return {"ok":False,"workflow_id":wid,"status":"subworkflow_created","subworkflow_id":sid}
            set_workflow_state(wid,"failed",idx,f"failed at step {idx+1}","",0)
            create_incident("workflow",wid,target,"workflow_validation_failed","warning",f"Validation failed at step {idx+1}",{"result":res})
            return {"ok":False,"status":"failed","result":res}
        idx+=1; set_workflow_state(wid,"running",idx,f"completed step {idx}")
    set_workflow_state(wid,"completed",len(steps),"workflow completed","",0); log_event("info","workflow_engine","workflow completed",{"workflow_id":wid})
    return {"ok":True,"workflow_id":wid,"status":"completed"}

def resume_workflow_from_approval(aid):
    a=get_approval(aid); meta=a["metadata"]; wid=meta.get("workflow_id"); idx=meta.get("step_index",0); target=meta.get("target_name","local")
    res=run_on_target(target,a["command_text"])
    insert_validation_run("workflow",wid,idx,"success" if res.get("ok") else "failed",{"approved_command_result":res})
    if not res.get("ok"):
        set_workflow_state(wid,"failed",idx,"approved command failed","",0); return {"ok":False,"result":res}
    set_workflow_state(wid,"running",idx+1,"resumed after approval")
    return process_workflow(wid)

def lease_and_process_next_workflow(worker):
    wf=lease_next_workflow(worker)
    if not wf: return None
    return process_workflow(wf["id"])
