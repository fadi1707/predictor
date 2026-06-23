import argparse
import json
import os
from pathlib import Path

import yaml


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)["artifact"]


def base_version(config):
    version = config["version"]
    return f'{version["major"]}.{version["minor"]}.{version["patch"]}'


def github_output(values):
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description="Resolve branch-aware artifact version metadata.")
    parser.add_argument("--config", default="config/artifact-version.yml")
    parser.add_argument("--ref-name", default=os.environ.get("GITHUB_REF_NAME", "local"))
    parser.add_argument("--ref-type", default=os.environ.get("GITHUB_REF_TYPE", "branch"))
    parser.add_argument("--run-number", default=os.environ.get("GITHUB_RUN_NUMBER", "0"))
    parser.add_argument("--sha", default=os.environ.get("GITHUB_SHA", "local"))
    parser.add_argument("--out", default="artifact-metadata.json")
    args = parser.parse_args()

    config = load_config(args.config)
    release_branch = config["release_branch"]
    is_release_branch = args.ref_type == "branch" and args.ref_name == release_branch
    base = base_version(config)
    short_sha = args.sha[:12]

    if is_release_branch:
        version = base
        build_kind = "RELEASE"
        release_enabled = "true"
        release_tag = f'{config["tag_prefix"]}{version}'
    else:
        version = f'{base}-{config["snapshot_suffix"]}.{args.run_number}+{short_sha}'
        build_kind = "SNAPSHOT"
        release_enabled = "false"
        release_tag = ""

    artifact_name = f'{config["name"]}-{version}'
    metadata = {
        "name": config["name"],
        "version": version,
        "build_kind": build_kind,
        "artifact_name": artifact_name,
        "release_branch": release_branch,
        "git_ref": args.ref_name,
        "git_sha": args.sha,
        "run_number": args.run_number,
    }
    Path(args.out).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    github_output(
        {
            "app_name": config["name"],
            "version": version,
            "build_kind": build_kind,
            "artifact_name": artifact_name,
            "release_enabled": release_enabled,
            "release_tag": release_tag,
            "is_release_branch": str(is_release_branch).lower(),
        }
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
