from app.db import latest_inventory, recent_incidents_for_target, list_strategy_scores
from app.dependencies import dependencies_for

def goal_signature(goal):
    t=goal.lower()
    if "restore" in t and "nginx" in t: return "restore_nginx"
    if "restart deployment" in t: return "restart_deployment"
    if "patch file" in t: return "patch_file"
    return "summary"

def recommend_strategies(target, goal):
    sig=goal_signature(goal)
    scored=list_strategy_scores(target,sig)
    if scored: return [{"strategy":s["strategy"],"score":s["score"],"source":"history"} for s in scored]
    if recent_incidents_for_target(target): return [{"strategy":"diagnose_then_repair","score":50,"source":"recent_incidents"}]
    if latest_inventory(target): return [{"strategy":"inventory_informed_plan","score":40,"source":"inventory"}]
    return [{"strategy":"basic_plan","score":10,"source":"default"}]

def decompose_goal(goal, target_name="local"):
    text=goal.strip().lower()
    rec=recommend_strategies(target_name,goal)
    steps=[]
    if text.startswith("restore ") and "nginx" in text:
        for dep in dependencies_for("nginx"):
            steps.append({"kind":"validation","description":f"Validate dependency {dep}","command":f"systemctl is-active {dep}","expect_stdout":"active","on_failure":"stop"})
        steps += [
          {"kind":"command","description":"Inspect nginx","command":"systemctl status nginx --no-pager --full"},
          {"kind":"validation","description":"Check nginx active","command":"systemctl is-active nginx","expect_stdout":"active","on_failure":"continue"},
          {"kind":"command","description":"Restart nginx","command":"systemctl restart nginx","requires_approval":True},
          {"kind":"validation","description":"Verify nginx active after restart","command":"systemctl is-active nginx","expect_stdout":"active","on_failure":"subworkflow","subworkflow_goal":"collect nginx diagnostics"},
        ]
        return {"name":"goal_restore_nginx","target_name":target_name,"recommendations":rec,"steps":steps}
    if text.startswith("restart deployment "):
        dep=goal.split("restart deployment ",1)[1].strip()
        for d in dependencies_for(dep):
            steps.append({"kind":"validation","description":f"Validate dependency {d}","command":f"systemctl is-active {d}","expect_stdout":"active","on_failure":"stop"})
        steps += [
          {"kind":"command","description":"Inspect pods","command":"kubectl get pods -n default --no-headers"},
          {"kind":"command","description":f"Rollout restart deployment/{dep}","command":f"kubectl rollout restart deployment/{dep} -n default","requires_approval":True},
          {"kind":"validation","description":f"Validate deployment {dep}","command":f"kubectl get deployment {dep} -n default -o jsonpath='{{.status.readyReplicas}}/{{.status.replicas}}'","expect_regex":r"^(\\d+)/(\\1)$","on_failure":"stop"},
        ]
        return {"name":"goal_restart_deployment","target_name":target_name,"recommendations":rec,"steps":steps}
    if text.startswith("patch file "):
        rest=goal.split("patch file ",1)[1]; fpart,rpart=rest.split(" replace ",1); frm,to=rpart.split(" with ",1)
        return {"name":"goal_patch_file","target_name":target_name,"recommendations":rec,"steps":[
          {"kind":"backup_file","description":f"Backup {fpart.strip()}","file_path":fpart.strip()},
          {"kind":"patch_file","description":f"Patch {fpart.strip()}","file_path":fpart.strip(),"replace_from":frm,"replace_to":to},
        ]}
    if "collect nginx diagnostics" in text:
        return {"name":"goal_collect_nginx_diagnostics","target_name":target_name,"recommendations":rec,"steps":[
          {"kind":"command","description":"Collect nginx journal","command":"journalctl -u nginx -n 50 --no-pager"},
          {"kind":"command","description":"Collect disk state","command":"df -h / | tail -n 1"},
        ]}
    return {"name":"goal_summary","target_name":target_name,"recommendations":rec,"steps":[{"kind":"command","description":"Show summary","command":"uname -a && df -h / | tail -n 1"}]}
