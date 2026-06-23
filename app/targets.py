import os, yaml
DEFAULT={"targets":{"local":{"type":"local","tags":["local"]},"demo-ssh":{"type":"ssh","host":"127.0.0.1","user":"root","port":22,"secret_profile":"demo-ssh","tags":["ssh"]}}}
def load_targets():
    p="config/targets.yaml"
    if os.path.exists(p):
        with open(p,"r") as f: return yaml.safe_load(f) or DEFAULT
    return DEFAULT
def get_target(name):
    return load_targets().get("targets",{}).get(name)
