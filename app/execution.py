import os, shutil, subprocess, paramiko
from app.config import settings
from app.secrets import get_secret_profile
from app.targets import get_target

def run_local(command, timeout=60):
    try:
        r=subprocess.run(command,shell=True,capture_output=True,text=True,timeout=timeout)
        return {"ok":r.returncode==0,"returncode":r.returncode,"stdout":r.stdout.strip(),"stderr":r.stderr.strip(),"command":command}
    except Exception as e:
        return {"ok":False,"returncode":-1,"stdout":"","stderr":str(e),"command":command}

def run_ssh(target_name, command, timeout=60):
    t=get_target(target_name)
    if not t: return {"ok":False,"stdout":"","stderr":f"unknown target {target_name}","returncode":-1}
    prof=get_secret_profile(t.get("secret_profile",target_name), settings.secret_provider)
    try:
        ssh=paramiko.SSHClient(); ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kw={"hostname":t["host"],"port":int(t.get("port",22)),"username":t.get("user","root"),"timeout":timeout}
        if prof and prof.get("type")=="ssh_key": kw["key_filename"]=os.path.expanduser(prof.get("key_path","~/.ssh/id_rsa"))
        ssh.connect(**kw)
        _,out,err=ssh.exec_command(command,timeout=timeout)
        so=out.read().decode(); se=err.read().decode(); ssh.close()
        return {"ok":se=="","stdout":so.strip(),"stderr":se.strip(),"returncode":0 if se=="" else 1,"command":command,"target":target_name}
    except Exception as e:
        return {"ok":False,"stdout":"","stderr":str(e),"returncode":-1,"command":command,"target":target_name}

def run_on_target(target_name, command, timeout=60):
    t=get_target(target_name)
    if not t: return {"ok":False,"stdout":"","stderr":f"unknown target {target_name}","returncode":-1}
    return run_local(command, timeout) if t["type"]=="local" else run_ssh(target_name, command, timeout)

def workspace_backup(owner_id, rel_path):
    root=os.path.abspath(settings.approved_workspace); target=os.path.abspath(rel_path)
    if not target.startswith(root): return {"ok":False,"error":"path outside approved workspace"}
    bdir=os.path.join(root,".rollbacks"); os.makedirs(bdir,exist_ok=True)
    bpath=os.path.join(bdir, os.path.basename(target)+f".owner{owner_id}.bak")
    shutil.copy2(target,bpath)
    return {"ok":True,"target":target,"backup_path":bpath}
