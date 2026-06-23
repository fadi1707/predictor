from app.config import settings
from app.db import create_job, create_workflow, insert_chat
from app.planner import decompose_goal
from app.policy import can_queue_job, can_queue_workflow
from app.services_ollama import ollama_generate

def handle_chat(text):
    insert_chat("user",text); low=text.strip().lower()
    if low.startswith("goal "):
        if not can_queue_workflow(): return {"mode":"denied","response":"Current role cannot queue workflows."}
        goal=text.split("goal ",1)[1]; wf=decompose_goal(goal,"local"); wid=create_workflow(goal,"local",wf)
        resp={"mode":"workflow","response":f"Queued workflow for goal: {goal}","workflow_id":wid}; insert_chat("assistant",resp["response"]); return resp
    if low.startswith("run on "):
        if not can_queue_job("command"): return {"mode":"denied","response":"Current role cannot queue command jobs."}
        rest=text.split("run on ",1)[1]; target,cmd=rest.split(" ",1); jid=create_job("command",target,{"command":cmd})
        resp={"mode":"job","response":f"Queued command job on {target}","job_id":jid}; insert_chat("assistant",resp["response"]); return resp
    if settings.ollama_enabled:
        try:
            r=ollama_generate(text,"You are a local AI operations assistant. Be practical and bounded.")
            insert_chat("assistant",r); return {"mode":"ollama","response":r}
        except Exception as e:
            return {"mode":"fallback","response":f"Ollama failed: {e}"}
    return {"mode":"control","response":"Try: goal restore nginx and verify health, goal restart deployment my-api, or run on demo-ssh hostname."}
