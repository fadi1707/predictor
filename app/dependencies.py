import os, yaml
DEFAULT={"services":{"nginx":{"depends_on":[]},"my-api":{"depends_on":["db","redis"]},"db":{"depends_on":[]},"redis":{"depends_on":[]}}}
def load_graph():
    p="config/dependencies.yaml"
    if os.path.exists(p):
        with open(p,"r") as f: return yaml.safe_load(f) or DEFAULT
    return DEFAULT
def dependencies_for(name):
    return load_graph().get("services",{}).get(name,{}).get("depends_on",[])
