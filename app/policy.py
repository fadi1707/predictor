import os, yaml
from app.config import settings

DEFAULT = {
  "roles": {
    "viewer": {"allowed_job_types": ["inventory"], "allowed_workflows": [], "can_approve": False},
    "operator": {"allowed_job_types": ["inventory","command","playbook"], "allowed_workflows": ["goal"], "can_approve": True},
    "admin": {"allowed_job_types": ["inventory","command","playbook"], "allowed_workflows": ["goal"], "can_approve": True}
  },
  "targets": {
    "local": {"allowed_actions": ["read","validate","restart","patch","package"]},
    "local-win": {"allowed_actions": ["read","validate","restart","patch"]},
    "demo-ssh": {"allowed_actions": ["read","validate"]}
  }
}

BLOCKED = {
    "rm -rf /","mkfs","dd if=","shutdown","reboot","poweroff",
    ":(){:|:&};:","userdel ","groupdel ","format ","del /s /q c:\\",
    "remove-item -recurse -force c:\\"
}

HIGH = {
    " systemctl restart ":"restart",
    " systemctl stop ":"restart",
    " docker restart ":"restart",
    " docker stop ":"restart",
    " kubectl rollout restart ":"restart",
    " kubectl delete ":"restart",
    " restart-service ":"restart",
    " stop-service ":"restart",
    " apt ":"package",
    " yum ":"package",
    " dnf ":"package"
}

def load_policies():
    p="config/policies.yaml"
    if os.path.exists(p):
        with open(p,"r") as f:
            return yaml.safe_load(f) or DEFAULT
    return DEFAULT

def role_policy(role):
    d=load_policies()
    return d.get("roles",{}).get(role,d["roles"]["viewer"])

def can_queue_job(t, role=None):
    return t in role_policy(role or settings.current_role).get("allowed_job_types",[])

def can_queue_workflow(role=None):
    return "goal" in role_policy(role or settings.current_role).get("allowed_workflows",[])

def can_approve(role=None):
    return bool(role_policy(role or settings.current_role).get("can_approve",False))

def target_allows_action(target, action):
    return action in load_policies().get("targets",{}).get(target,{"allowed_actions":["read","validate"]}).get("allowed_actions",[])

def infer_action(command):
    low=f" {command.lower()} "
    for token, action in HIGH.items():
        if token in low:
            return action
    if any(x in low for x in [
        " status "," get ","cat "," grep ","journalctl","df -h","uname",
        "hostname","whoami","dir","get-service","get-process","get-psdrive"
    ]):
        return "read"
    return "validate"

def assess_command(command, target_name="local"):
    low=f" {command.lower()} "
    for b in BLOCKED:
        if b in low:
            return {"allowed":False,"risk":"blocked","reason":f"blocked term detected: {b}"}
    action=infer_action(command)
    if not target_allows_action(target_name, action):
        return {"allowed":False,"risk":"blocked","reason":f"target {target_name} does not allow action {action}","action":action}
    high=action in {"restart","package"}
    return {"allowed":True,"risk":"high" if high else "low","requires_approval":high,"action":action}
