from app.db import create_inventory, latest_inventory
from app.execution import run_on_target
from app.windows_adapter import is_windows, windows_health

CMDS={
    "uname":"uname -a",
    "systemctl":"systemctl list-units --type=service --no-pager --no-legend | head -n 20",
    "docker":"docker ps --format '{{.Names}}\\t{{.Status}}' 2>/dev/null | head -n 20",
    "k8s":"kubectl get pods -A --no-headers 2>/dev/null | head -n 20",
    "disk":"df -h / | tail -n 1",
    "memory":"free -m | head -n 2"
}

def discover_target(target):
    if target == "local-win" or (target == "local" and is_windows()):
        payload = {"windows": windows_health()}
        create_inventory(target, payload)
        return payload

    p={k:run_on_target(target,c,30) for k,c in CMDS.items()}
    create_inventory(target,p)
    return p

def health_model(target):
    inv=latest_inventory(target)
    if not inv:
        return {"target_name":target,"status":"unknown","issues":["no inventory yet"]}
    payload=inv["payload"]
    issues=[]

    if "windows" in payload:
        win = payload["windows"]
        for key in ("os", "computer", "disk", "memory"):
            if not win.get(key,{}).get("ok",False):
                issues.append(f"windows {key} check failed")
    else:
        for s in ("uname","disk","memory"):
            if not payload.get(s,{}).get("ok",False):
                issues.append(f"{s} check failed")

    return {"target_name":target,"status":"healthy" if not issues else "degraded","issues":issues,"inventory_id":inv["id"]}
