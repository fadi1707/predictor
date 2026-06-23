# Python 3.14 install fix

The original v7.1 package pinned:

```text
pydantic==2.9.2
```

That version is too old for Python 3.14 environments and may force pip to build `pydantic-core` from source.

This patched package changes it to:

```text
pydantic>=2.13.0
```

Pydantic 2.12+ added Python 3.14 support, and newer versions avoid the old build problem on many systems.

## Recommended clean reinstall

From inside the project folder:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Then run:

```bash
./scripts/run.sh
```

Worker:

```bash
./scripts/run_worker.sh
```

## If it still tries to compile native packages

Install build tools:

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y build-essential python3-dev
```

But the cleaner option is to use Python 3.12 or 3.13 for now:

```bash
python3.12 -m venv .venv
```
