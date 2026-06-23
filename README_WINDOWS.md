# AI Ops Assistant v7.2 - Windows 11 Guide

v7.2 can run directly on Windows 11.

## Install

```cmd
scripts\install_win.bat
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_win.ps1
```

## Run

```cmd
scripts\run_win.bat
```

Worker:

```cmd
scripts\run_worker_win.bat
```

Open:

```text
http://127.0.0.1:8080/
```

## Windows-native endpoints

```text
/api/windows/health
/api/windows/services
/api/windows/services/{service}/status
/api/windows/services/{service}/restart
```

## Safer Windows test prompts

```text
run on local-win hostname
run on local-win whoami
run on local-win dir
goal patch file ./workspace/demo.txt replace OLD with NEW
```

Linux workflows like `systemctl` still need Linux, WSL, or SSH targets. Shocking that Windows did not adopt systemd just to make our lives easier.
