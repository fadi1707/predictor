import argparse
import os
import shutil
import stat
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCLUDE_DIRS = ["app", "config", "scripts", "data", "source_pdfs"]
DEFAULT_INCLUDE_FILES = [
    "README.md",
    "README_WINDOWS.md",
    "README_PY314_FIX.md",
    "requirements.txt",
    ".env.example",
    "artifact-metadata.json",
]


def ignore(directory, names):
    ignored = set()
    for name in names:
        if name == "__pycache__" or name.startswith(".pytest_cache"):
            ignored.add(name)
        if name.endswith((".pyc", ".pyo")):
            ignored.add(name)
    return ignored


def copy_path(src, dest):
    if src.is_dir():
        shutil.copytree(src, dest, ignore=ignore)
    elif src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def make_zip(package_dir, zip_path):
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package_dir.parent))


def remove_tree(path):
    def retry_with_write_access(function, item, exc_info):
        try:
            os.chmod(item, stat.S_IWRITE)
            function(item)
        except PermissionError:
            time.sleep(0.25)
            function(item)

    if path.exists():
        shutil.rmtree(path, onerror=retry_with_write_access)


def main():
    parser = argparse.ArgumentParser(description="Package the predictor engine.")
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--dist", default="dist")
    args = parser.parse_args()

    dist = ROOT / args.dist
    package_dir = dist / args.artifact_name
    zip_path = dist / f"{args.artifact_name}.zip"

    remove_tree(package_dir)
    package_dir.mkdir(parents=True)

    for dirname in DEFAULT_INCLUDE_DIRS:
        copy_path(ROOT / dirname, package_dir / dirname)

    for filename in DEFAULT_INCLUDE_FILES:
        copy_path(ROOT / filename, package_dir / filename)

    make_zip(package_dir, zip_path)
    print(zip_path)


if __name__ == "__main__":
    main()
