import time
from app.config import settings
from app.db import create_job, init_db, log_event
from app.job_engine import lease_and_process_next
from app.observability import detect_anomalies, get_metrics
from app.workflow_engine import lease_and_process_next_workflow

def run_worker():
    init_db(); log_event("info","worker","worker started",{"worker_name":settings.worker_name})
    while True:
        for issue in detect_anomalies(get_metrics()):
            log_event("warning","worker","observed anomaly",issue)
            if settings.auto_remediate and issue["type"]=="disk_high":
                create_job("command","local",{"command":"du -ah ./workspace | sort -hr | head -n 20"})
        wf=lease_and_process_next_workflow(settings.worker_name)
        if wf: log_event("info","worker","processed workflow",{"result":wf})
        job=lease_and_process_next(settings.worker_name)
        if job: log_event("info","worker","processed job",{"result":job})
        time.sleep(settings.worker_interval_seconds)
if __name__=="__main__":
    run_worker()
