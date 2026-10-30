"""Validate the owned forms and declared AI Git trailers, without network writes."""

import argparse
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[2]
AI_KEYS = {"ai-tool", "ai-model-requested"}


def check_form(form):
    if not isinstance(form, dict) or not form.get("name") or not form.get("description"):
        raise ValueError("Form needs name and description")
    body = form.get("body")
    if not isinstance(body, list) or not body:
        raise ValueError("Form needs a nonempty body")
    fields = {}
    for field in body:
        if not isinstance(field, dict):
            raise ValueError("Form body entries must be mappings")
        kind = field.get("type")
        if kind not in {"input", "textarea", "dropdown", "checkboxes", "markdown"}:
            raise ValueError(f"Unsupported form type: {kind}")
        if kind == "markdown":
            continue
        key = field.get("id")
        if not isinstance(key, str) or not key or key in fields:
            raise ValueError("Missing or duplicate field id")
        attrs = field.get("attributes", {})
        if not attrs.get("label"):
            raise ValueError(f"Field {key} needs a label")
        if kind == "dropdown" and not attrs.get("options"):
            raise ValueError(f"Dropdown {key} needs options")
        fields[key] = field
    for key in ("owner", "problem", "acceptance"):
        if fields.get(key, {}).get("validations", {}).get("required") is not True:
            raise ValueError(f"Required issue field missing: {key}")
    if "agents" not in fields:
        raise ValueError("Agent attribution field missing")


def check_trailers(message):
    # Git owns trailer parsing, including continuation and repeated contributor keys.
    parsed = subprocess.run(
        ["git", "interpret-trailers", "--parse"], input=message,
        text=True, capture_output=True, check=True,
    ).stdout
    values = {key: [] for key in AI_KEYS}
    for line in parsed.splitlines():
        key, _, value = line.partition(":")
        if key.lower() in values:
            values[key.lower()].append(value.strip())
    if not any(values.values()):
        return
    if any(not value for group in values.values() for value in group):
        raise ValueError("AI trailers cannot be blank; use unknown when needed")
    if len(values["ai-tool"]) != len(values["ai-model-requested"]):
        raise ValueError("AI-Tool and AI-Model-Requested must be paired")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", help="Validate trailers declared on this revision")
    args = parser.parse_args()
    for name in ("bug", "task"):
        path = ROOT / ".github" / "ISSUE_TEMPLATE" / f"{name}.yml"
        check_form(yaml.safe_load(path.read_text(encoding="utf-8")))
    if args.commit:
        message = subprocess.run(
            ["git", "show", "-s", "--format=%B", args.commit, "--"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout
        check_trailers(message)
    print("GitHub workflow structure: PASS")


if __name__ == "__main__":
    main()
