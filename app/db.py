import json, os, sqlite3, time
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "assistant.db")

def conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def jrow(row, fields):
    if row is None: return None
    d = dict(row)
    for f in fields:
        if f in d:
            d[f[:-5] if f.endswith("_json") else f] = json.loads(d.pop(f))
    return d

def init_db():
    c = conn()
    cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS approvals (id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT, command_text TEXT, metadata_json TEXT DEFAULT '{}', status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT, source TEXT, message TEXT, metadata_json TEXT DEFAULT '{}', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, job_type TEXT, target_name TEXT DEFAULT 'local', payload_json TEXT, status TEXT DEFAULT 'queued', current_step INTEGER DEFAULT 0, summary TEXT DEFAULT '', lease_owner TEXT DEFAULT '', lease_expires_at INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS workflows (id INTEGER PRIMARY KEY AUTOINCREMENT, goal TEXT, target_name TEXT DEFAULT 'local', definition_json TEXT, status TEXT DEFAULT 'queued', current_step INTEGER DEFAULT 0, lease_owner TEXT DEFAULT '', lease_expires_at INTEGER DEFAULT 0, summary TEXT DEFAULT '', parent_workflow_id INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS validation_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_type TEXT DEFAULT 'job', owner_id INTEGER, step_index INTEGER, status TEXT, payload_json TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_type TEXT DEFAULT 'job', owner_id INTEGER, target_name TEXT DEFAULT 'local', signature TEXT DEFAULT '', level TEXT, summary TEXT, payload_json TEXT DEFAULT '{}', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, target_name TEXT, payload_json TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS rollbacks (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_type TEXT DEFAULT 'job', owner_id INTEGER, target_name TEXT DEFAULT 'local', rel_path TEXT, backup_path TEXT, chain_json TEXT DEFAULT '[]', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS strategy_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, target_name TEXT, goal_signature TEXT, strategy TEXT, score INTEGER DEFAULT 0, payload_json TEXT DEFAULT '{}', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    c.commit(); c.close()

def insert_chat(role, content):
    c=conn(); c.execute("INSERT INTO chat_history(role, content) VALUES (?,?)",(role,content)); c.commit(); c.close()
def list_chat(limit=50):
    c=conn(); rows=c.execute("SELECT * FROM chat_history ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [dict(r) for r in rows][::-1]
def log_event(level, source, message, metadata=None):
    c=conn(); c.execute("INSERT INTO events(level,source,message,metadata_json) VALUES (?,?,?,?)",(level,source,message,json.dumps(metadata or {}))); c.commit(); c.close()
def list_events(limit=100):
    c=conn(); rows=c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["metadata_json"]) for r in rows]

def create_approval(action_type, command_text, metadata=None):
    c=conn(); cur=c.execute("INSERT INTO approvals(action_type,command_text,metadata_json,status) VALUES (?,?,?,'pending')",(action_type,command_text,json.dumps(metadata or {}))); c.commit(); i=cur.lastrowid; c.close(); return int(i)
def get_approval(i):
    c=conn(); r=c.execute("SELECT * FROM approvals WHERE id=?",(i,)).fetchone(); c.close(); return jrow(r,["metadata_json"])
def set_approval_status(i,status):
    c=conn(); c.execute("UPDATE approvals SET status=? WHERE id=?",(status,i)); c.commit(); c.close()
def list_approvals(limit=50):
    c=conn(); rows=c.execute("SELECT * FROM approvals ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["metadata_json"]) for r in rows]

def create_job(job_type,target_name,payload,status="queued"):
    c=conn(); cur=c.execute("INSERT INTO jobs(job_type,target_name,payload_json,status) VALUES (?,?,?,?)",(job_type,target_name,json.dumps(payload),status)); c.commit(); i=cur.lastrowid; c.close(); return int(i)
def get_job(i):
    c=conn(); r=c.execute("SELECT * FROM jobs WHERE id=?",(i,)).fetchone(); c.close(); return jrow(r,["payload_json"])
def list_jobs(limit=100):
    c=conn(); rows=c.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["payload_json"]) for r in rows]
def lease_next_job(worker, seconds=60):
    now=int(time.time()); exp=now+seconds; c=conn(); cur=c.cursor()
    r=cur.execute("SELECT id FROM jobs WHERE status='queued' AND (lease_expires_at=0 OR lease_expires_at<?) ORDER BY id ASC LIMIT 1",(now,)).fetchone()
    if not r: c.close(); return None
    cur.execute("UPDATE jobs SET status='running', lease_owner=?, lease_expires_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(worker,exp,r["id"]))
    c.commit(); c.close(); return get_job(r["id"])
def set_job_state(i,status,current_step=None,summary=None,lease_owner=None,lease_expires_at=None):
    j=get_job(i); c=conn()
    c.execute("UPDATE jobs SET status=?, current_step=?, summary=?, lease_owner=?, lease_expires_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(status, j["current_step"] if current_step is None else current_step, j["summary"] if summary is None else summary, j.get("lease_owner","") if lease_owner is None else lease_owner, j.get("lease_expires_at",0) if lease_expires_at is None else lease_expires_at, i))
    c.commit(); c.close()

def create_workflow(goal,target_name,definition,status="queued",parent_workflow_id=0):
    c=conn(); cur=c.execute("INSERT INTO workflows(goal,target_name,definition_json,status,parent_workflow_id) VALUES (?,?,?,?,?)",(goal,target_name,json.dumps(definition),status,parent_workflow_id)); c.commit(); i=cur.lastrowid; c.close(); return int(i)
def get_workflow(i):
    c=conn(); r=c.execute("SELECT * FROM workflows WHERE id=?",(i,)).fetchone(); c.close(); return jrow(r,["definition_json"])
def list_workflows(limit=100):
    c=conn(); rows=c.execute("SELECT * FROM workflows ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["definition_json"]) for r in rows]
def lease_next_workflow(worker,seconds=60):
    now=int(time.time()); exp=now+seconds; c=conn(); cur=c.cursor()
    r=cur.execute("SELECT id FROM workflows WHERE status='queued' AND (lease_expires_at=0 OR lease_expires_at<?) ORDER BY id ASC LIMIT 1",(now,)).fetchone()
    if not r: c.close(); return None
    cur.execute("UPDATE workflows SET status='running', lease_owner=?, lease_expires_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(worker,exp,r["id"]))
    c.commit(); c.close(); return get_workflow(r["id"])
def set_workflow_state(i,status,current_step=None,summary=None,lease_owner=None,lease_expires_at=None):
    w=get_workflow(i); c=conn()
    c.execute("UPDATE workflows SET status=?, current_step=?, summary=?, lease_owner=?, lease_expires_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",(status, w["current_step"] if current_step is None else current_step, w["summary"] if summary is None else summary, w.get("lease_owner","") if lease_owner is None else lease_owner, w.get("lease_expires_at",0) if lease_expires_at is None else lease_expires_at, i))
    c.commit(); c.close()

def insert_validation_run(owner_type,owner_id,step_index,status,payload):
    c=conn(); c.execute("INSERT INTO validation_runs(owner_type,owner_id,step_index,status,payload_json) VALUES (?,?,?,?,?)",(owner_type,owner_id,step_index,status,json.dumps(payload))); c.commit(); c.close()
def list_validation_runs(limit=100):
    c=conn(); rows=c.execute("SELECT * FROM validation_runs ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["payload_json"]) for r in rows]
def create_incident(owner_type,owner_id,target_name,signature,level,summary,payload=None):
    c=conn(); c.execute("INSERT INTO incidents(owner_type,owner_id,target_name,signature,level,summary,payload_json) VALUES (?,?,?,?,?,?,?)",(owner_type,owner_id,target_name,signature,level,summary,json.dumps(payload or {}))); c.commit(); c.close()
def list_incidents(limit=100):
    c=conn(); rows=c.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["payload_json"]) for r in rows]
def recent_incidents_for_target(target,limit=20):
    c=conn(); rows=c.execute("SELECT * FROM incidents WHERE target_name=? ORDER BY id DESC LIMIT ?",(target,limit)).fetchall(); c.close(); return [jrow(r,["payload_json"]) for r in rows]

def create_inventory(target,payload):
    c=conn(); c.execute("INSERT INTO inventory(target_name,payload_json) VALUES (?,?)",(target,json.dumps(payload))); c.commit(); c.close()
def latest_inventory(target):
    c=conn(); r=c.execute("SELECT * FROM inventory WHERE target_name=? ORDER BY id DESC LIMIT 1",(target,)).fetchone(); c.close(); return jrow(r,["payload_json"])
def list_inventory(limit=100):
    c=conn(); rows=c.execute("SELECT * FROM inventory ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["payload_json"]) for r in rows]
def create_rollback(owner_type,owner_id,target,rel_path,backup_path,chain=None):
    c=conn(); c.execute("INSERT INTO rollbacks(owner_type,owner_id,target_name,rel_path,backup_path,chain_json) VALUES (?,?,?,?,?,?)",(owner_type,owner_id,target,rel_path,backup_path,json.dumps(chain or []))); c.commit(); c.close()
def get_rollback(i):
    c=conn(); r=c.execute("SELECT * FROM rollbacks WHERE id=?",(i,)).fetchone(); c.close(); return jrow(r,["chain_json"])
def list_rollbacks(limit=100):
    c=conn(); rows=c.execute("SELECT * FROM rollbacks ORDER BY id DESC LIMIT ?",(limit,)).fetchall(); c.close(); return [jrow(r,["chain_json"]) for r in rows]
def list_strategy_scores(target,sig,limit=10):
    c=conn(); rows=c.execute("SELECT * FROM strategy_scores WHERE target_name=? AND goal_signature=? ORDER BY score DESC,id DESC LIMIT ?",(target,sig,limit)).fetchall(); c.close(); return [jrow(r,["payload_json"]) for r in rows]
