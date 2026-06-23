from __future__ import annotations
import difflib
import os
from app.config import settings
from app.db import create_rollback
from app.execution import workspace_backup

def _safe_workspace_path(file_path: str) -> str:
    root = os.path.abspath(settings.approved_workspace)
    target = os.path.abspath(file_path)
    if not target.startswith(root):
        raise ValueError("file path is outside approved workspace")
    return target

def preview_patch(file_path: str, replace_from: str, replace_to: str) -> dict:
    target = _safe_workspace_path(file_path)
    if not os.path.exists(target):
        return {"ok": False, "error": "file not found", "file_path": target}

    with open(target, "r", encoding="utf-8") as f:
        old = f.read()

    new = old.replace(replace_from, replace_to)
    if old == new:
        return {"ok": True, "changed": False, "file_path": target, "diff": "", "message": "no matching text found"}

    diff = "\n".join(difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=f"{target}:before",
        tofile=f"{target}:after",
        lineterm=""
    ))

    return {"ok": True, "changed": True, "file_path": target, "diff": diff}

def apply_patch(owner_type: str, owner_id: int, target_name: str, file_path: str, replace_from: str, replace_to: str) -> dict:
    preview = preview_patch(file_path, replace_from, replace_to)
    if not preview.get("ok"):
        return preview
    if not preview.get("changed"):
        return preview

    target = preview["file_path"]
    backup = workspace_backup(owner_id, target)
    if not backup.get("ok"):
        return backup

    with open(target, "r", encoding="utf-8") as f:
        old = f.read()
    new = old.replace(replace_from, replace_to)
    with open(target, "w", encoding="utf-8") as f:
        f.write(new)

    create_rollback(
        owner_type,
        owner_id,
        target_name,
        target,
        backup["backup_path"],
        chain=[{"action": "semantic_replace", "replace_from": replace_from, "replace_to": replace_to}],
    )

    return {"ok": True, "changed": True, "file_path": target, "backup_path": backup["backup_path"], "diff": preview["diff"]}
