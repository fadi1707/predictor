import argparse
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser(description="Bump the artifact patch version.")
    parser.add_argument("--config", default="config/artifact-version.yml")
    args = parser.parse_args()

    path = Path(args.config)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["artifact"]["version"]["patch"] += 1
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    version = data["artifact"]["version"]
    print(f'Next version: {version["major"]}.{version["minor"]}.{version["patch"]}')


if __name__ == "__main__":
    main()
