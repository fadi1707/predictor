from app.db import get_workflow
def workflow_graph(workflow_id):
    wf=get_workflow(workflow_id)
    if not wf: return {"nodes":[],"edges":[],"error":f"workflow {workflow_id} not found"}
    steps=wf["definition"]["steps"]; nodes=[]; edges=[]
    for i,s in enumerate(steps):
        nodes.append({"id":f"step-{i}","label":s.get("description",f"step {i}"),"kind":s.get("kind","command"),"status":"current" if i==wf["current_step"] else "pending" if i>wf["current_step"] else "done"})
        if i>0: edges.append({"from":f"step-{i-1}","to":f"step-{i}"})
        if s.get("on_failure")=="subworkflow":
            nodes.append({"id":f"subworkflow-{i}","label":s.get("subworkflow_goal"),"kind":"subworkflow","status":"conditional"})
            edges.append({"from":f"step-{i}","to":f"subworkflow-{i}","condition":"on_failure"})
    return {"workflow_id":workflow_id,"nodes":nodes,"edges":edges}
