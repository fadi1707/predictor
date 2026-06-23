import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"


def venv_python() -> Path:
    if platform.system().lower() == "windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_virtualenv() -> Path:
    python = venv_python()
    if not python.exists():
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    return python


def install_app(python: Path) -> None:
    run([str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    run([str(python), "-m", "pip", "install", "-r", "requirements.txt"])

    for directory in ("workspace", "workspace/.rollbacks", "data"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)

    demo_file = ROOT / "workspace" / "demo.txt"
    demo_file.touch(exist_ok=True)

    env_file = ROOT / ".env"
    example_env_file = ROOT / ".env.example"
    if not env_file.exists() and example_env_file.exists():
        shutil.copyfile(example_env_file, env_file)


def start_app(python: Path) -> None:
    system = platform.system().lower()
    default_host = "127.0.0.1" if system == "windows" else "0.0.0.0"
    host = os.environ.get("APP_HOST", default_host)
    port = os.environ.get("APP_PORT", "8080")

    print(f"Starting AI Ops Assistant on {host}:{port} ({system})", flush=True)
    run([str(python), "-m", "uvicorn", "app.main:app", "--host", host, "--port", port])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install and start AI Ops Assistant for the current OS.")
    parser.add_argument("--install-only", action="store_true", help="Install dependencies and prepare folders without starting the app.")
    parser.add_argument("--start-only", action="store_true", help="Start the app without running dependency installation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.install_only and args.start_only:
        raise SystemExit("--install-only and --start-only cannot be used together.")

    system = platform.system().lower()
    if system not in {"windows", "linux"}:
        raise SystemExit(f"Unsupported deployment OS: {platform.system()}. Supported systems: Windows, Linux.")

    print(f"Detected deployment OS: {platform.system()}", flush=True)
    python = ensure_virtualenv()

    if not args.start_only:
        install_app(python)

    if not args.install_only:
        start_app(python)


if __name__ == "__main__":
    main()
