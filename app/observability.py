import psutil
def get_metrics():
    return {"cpu_percent":psutil.cpu_percent(interval=0.1),"memory_percent":psutil.virtual_memory().percent,"disk_percent":psutil.disk_usage('/').percent}
def detect_anomalies(m):
    out=[]
    if m["disk_percent"]>90: out.append({"type":"disk_high","message":f"disk usage high: {m['disk_percent']}%"})
    if m["memory_percent"]>90: out.append({"type":"memory_high","message":f"memory usage high: {m['memory_percent']}%"})
    if m["cpu_percent"]>95: out.append({"type":"cpu_high","message":f"cpu usage high: {m['cpu_percent']}%"})
    return out
