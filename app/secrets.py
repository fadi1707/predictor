import os, yaml
DEFAULT={"profiles":{"demo-ssh":{"type":"ssh_key","key_path":"~/.ssh/id_rsa"}}}
def load_secret_profiles():
    p="config/secrets.yaml"
    if os.path.exists(p):
        with open(p,"r") as f: return yaml.safe_load(f) or DEFAULT
    return DEFAULT
def get_secret_profile(name, provider="file"):
    if provider == "env":
        key=os.getenv("AIOPS_SECRET_"+name.upper().replace("-","_")+"_KEY_PATH")
        return {"type":"ssh_key","key_path":key} if key else None
    return load_secret_profiles().get("profiles",{}).get(name)
def masked_secret_profile(name):
    p=get_secret_profile(name)
    if not p: return None
    q=dict(p)
    if "key_path" in q: q["key_path"]="***"
    return q
