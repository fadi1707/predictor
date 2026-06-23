from __future__ import annotations
import platform
import subprocess
from typing import Any

def is_windows() -> bool:
    return platform.system().lower() == "windows"

def run_powershell(command: str, timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "command": command,
            "shell": "powershell",
        }
    except Exception as exc:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
            "command": command,
            "shell": "powershell",
        }

def windows_health() -> dict[str, Any]:
    return {
        "os": run_powershell("(Get-CimInstance Win32_OperatingSystem).Caption"),
        "computer": run_powershell("$env:COMPUTERNAME"),
        "disk": run_powershell("Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free | ConvertTo-Json"),
        "memory": run_powershell("Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json"),
        "top_processes": run_powershell("Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 10 ProcessName,Id,CPU,WorkingSet | ConvertTo-Json"),
    }

def list_services() -> dict[str, Any]:
    return run_powershell("Get-Service | Select-Object -First 50 Name,Status,DisplayName | ConvertTo-Json")

def service_status(service_name: str) -> dict[str, Any]:
    return run_powershell(f"Get-Service -Name '{service_name}' | Select-Object Name,Status,DisplayName | ConvertTo-Json")

def restart_service(service_name: str) -> dict[str, Any]:
    return run_powershell(f"Restart-Service -Name '{service_name}' -Force; Get-Service -Name '{service_name}' | Select-Object Name,Status,DisplayName | ConvertTo-Json")
