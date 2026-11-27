"""Inspect the inventory inside the strategy catalogue without reading price or outcome payloads."""

import argparse
from collections import Counter, defaultdict
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = "planning/research/"
CATALOGUE = RESEARCH + "STRATEGY-CATALOGUE-20261107.json"
HASH = re.compile(r"[0-9a-f]{64}")
DOCUMENT = re.compile(r"([A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:md|json|py|cjs|mjs))\b")
METADATA_NAMES = {
    "manifest.json", "source-admission-v11.json", "source-observation-proof.json",
    "raw-seal.json", "completed.json", "range-protocol.md", "registration.md", "config.json",
}
DATASET_FIELDS = {
    "asset", "source", "target", "grain", "window", "clock", "availability",
    "exposure", "quality", "locator", "kind",
}
STUDY_FIELDS = {"method", "scope", "kind", "cost", "unit", "risk", "verdict", "limitation", "reopen", "docs"}


def _research_file(rel_path):
    """Resolve a tracked research document at its canonical path or under planning/research/archive/."""
    rel_str = rel_path.as_posix() if hasattr(rel_path, "as_posix") else str(rel_path)
    primary = ROOT / rel_str
    if primary.is_file():
        return primary
    if rel_str.startswith(RESEARCH):
        archived = ROOT / RESEARCH / "archive" / rel_str[len(RESEARCH):]
        if archived.is_file():
            return archived
    return primary


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def by_key(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        require(isinstance(value, str) and value and value not in result, f"missing or duplicate {key}: {value}")
        result[value] = row
    return result


def git_paths(revision, prefixes):
    listing = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "-z", revision, "--", *prefixes], cwd=ROOT
    )
    return set(listing.decode("utf-8").strip("\0").split("\0")) - {""}


def relative(value, allow_dot=False):
    path = PurePosixPath(value)
    require(not path.is_absolute() and "\\" not in value and ":" not in value and ".." not in path.parts
            and (allow_dot or path != PurePosixPath(".")), f"unsafe locator: {value}")
    require(path.as_posix() == value, f"noncanonical locator: {value}")
    return path


def safe_path(root, entry, allow_dot=False):
    path = root / relative(entry, allow_dot)
    require(path.resolve().is_relative_to(root), f"locator leaves private root: {entry}")
    return path


def validate_quality(row):
    for quality in by_key(row.get("quality_counts", []), "metric").values():
        n, d = quality["numerator"], quality["denominator"]
        require(type(n) is int and type(d) is int and 0 <= n <= d and d > 0,
                f"invalid denominator: {row['id']}/{quality['metric']}")


def legacy_links(value, role=None):
    """Extract paths only when an existing field names a document's role."""
    if isinstance(value, dict):
        for field, child in value.items():
            child_role = role
            if field.endswith("_locator") or field.endswith("_evidence") or field.endswith("_protocol"):
                child_role = ("protocol" if "protocol" in field else
                              "source_binding" if any(x in field for x in ("source", "admission", "data"))
                              else "evidence_reference")
            yield from legacy_links(child, child_role)
    elif isinstance(value, list):
        for child in value:
            yield from legacy_links(child, role)
    elif isinstance(value, str) and role:
        for name in DOCUMENT.findall(value):
            yield RESEARCH + name, role


def tracked_role(path, links):
    locator = PurePosixPath(path)
    name = locator.stem.lower()
    suffix = locator.suffix.lower()
    roles = {link["role"] for link in links}
    if "metadata" in roles:
        return "catalogue_metadata", "catalogue_relation"
    if roles.intersection({"index", "catalogue_guide"}):
        return "navigation", "catalogue_relation"
    if suffix in {".py", ".cjs", ".mjs", ".ps1"}:
        return "research_code_or_fixture", "file_format"
    if suffix in {".png", ".jpg", ".webp"} or path.startswith(RESEARCH + "fxreplay-capture/"):
        return "capture", "capture_directory_or_image_format"
    if path.startswith((RESEARCH + "ai-architecture-review-20261023/", "planning/trader/research/webgpt-native-v2/")):
        return "non_trading_system_research", "known_directory_scope"

    # Explicit links say what a document supports. Ambiguous generic links do not.
    role_map = (
        ({"outcome", "outcome_reference", "diagnosis", "baseline"}, "evidence_report_or_sidecar"),
        ({"protocol", "protocol_reference"}, "protocol_or_freeze"),
        ({"dataset_evidence", "dataset_reference", "source_binding", "source"}, "source_or_data_admission"),
        ({"decision", "decision_reference"}, "decision_record"),
        ({"control"}, "control_or_fixture"),
    )
    for keys, role in role_map:
        matches = [link for link in links if link["role"] in keys]
        if matches:
            basis = "index_label" if all(link["depth"] == "index_role" for link in matches) else "catalogue_relation"
            return role, basis

    conventions = (
        (r"(?:^|[-_])(?:erratum|correction|archive|recovery)(?:[-_]|$)", "correction_or_archive"),
        (r"(?:^|[-_])(?:protocol|freeze|registration|prespec|card)(?:[-_]|$)", "protocol_or_freeze"),
        (r"(?:^|[-_])(?:results?|summary|metrics|verification|audit|receipt|dossier|review|evidence)(?:[-_]|$)",
         "evidence_report_or_sidecar"),
        (r"(?:^|[-_])(?:source|manifest|admission|data|seal|coverage|quality)(?:[-_]|$)", "source_or_data_admission"),
        (r"(?:^|[-_])(?:decision|verdict|postmortem)(?:[-_]|$)", "decision_record"),
        (r"(?:^|[-_])(?:fixture|control|benchmark)(?:[-_]|$)", "control_or_fixture"),
        (r"(?:^|[-_])(?:run|state|resume|operations|runtime|status|ledger|smoke)(?:[-_]|$)",
         "run_or_operations_metadata"),
    )
    for pattern, role in conventions:
        if re.search(pattern, name):
            return role, "filename_convention_provisional"
    if path.startswith("planning/trader/research/foundation-validation/"):
        return "foundation_validation_artifact", "known_directory_scope"
    if suffix == ".sha256":
        return "integrity_metadata", "file_format"
    if suffix in {".md", ".txt"}:
        return "other_document", "file_format_only"
    return "unknown", "insufficient_metadata"


def classify_tracked(catalogue, inventory, paths):
    linked = defaultdict(list)
    missing_legacy = set()
    annotations = by_key(inventory.get("artifact_role_annotations", []), "path")
    require(annotations.keys() <= paths, "artifact role annotation target is outside the inventory")
    sources = {row["source"] for row in annotations.values()}
    require(all(relative(source).suffix in {".md", ".py"} for source in sources),
            "artifact role annotation must cite a document or source consumer")
    require(sources <= git_paths(inventory["tracked_base"], sorted(sources)),
            "artifact role annotation source is not tracked")
    require(all(row["role"] and row["note"] for row in annotations.values()), "incomplete artifact role annotation")

    def link(path, owner, role, depth):
        linked[path].append({"key": owner, "role": role, "depth": depth})

    for row in inventory["datasets"]:
        link(RESEARCH + row["locator"], row["id"], "dataset_evidence", "semantic")
    for row in inventory["studies"]:
        for role, filename in row["docs"].items():
            link(RESEARCH + filename, row["id"], role, "semantic")
    for row in inventory["legacy_exposure"]:
        for name in row["observations"]:
            link(RESEARCH + name, row["asset"], "exposure_evidence", "semantic")
    link(CATALOGUE, "strategy-catalogue", "metadata", "semantic")
    for role, filename in (("index", "README.md"), ("catalogue_guide", "STRATEGY-CATALOGUE-20261107.md")):
        link(RESEARCH + filename, "strategy-catalogue", role, "semantic")

    require(set(linked) <= paths, f"tracked evidence locators missing: {sorted(set(linked) - paths)}")
    for key in ("records", "registered_setup_studies", "registered_component_studies", "frequency_only_studies"):
        for row in catalogue[key]:
            for path, role in set(legacy_links(row)):
                if path in paths:
                    link(path, row["id"], role, "legacy_catalogue")
                else:
                    missing_legacy.add((row["id"], path))

    readme = (ROOT / RESEARCH / "README.md").read_text(encoding="utf-8-sig")
    index_roles = (
        (r"^(?:kết quả|results?)\b", "outcome_reference"),
        (r"^(?:protocol|đăng ký|card)\b", "protocol_reference"),
        (r"^(?:quyết định|decision)\b", "decision_reference"),
        (r"^(?:dữ liệu|nguồn dữ liệu|source admission)\b", "dataset_reference"),
    )
    for label, target in re.findall(r"\[([^\]\n]+)\]\(([^\s)]+)\)", readme):
        path = RESEARCH + unquote(target.split("#")[0]).removeprefix("./")
        if path not in paths:
            continue
        role = next((value for pattern, value in index_roles if re.search(pattern, label, re.I)), None)
        link(path, "research-readme", role or "index_reference", "index_role" if role else "navigation")

    result = []
    for path in sorted(paths):
        links = sorted(linked[path], key=lambda row: (row["depth"], row["key"], row["role"]))
        depths = {row["depth"] for row in links}
        depth = next((d for d in ("semantic", "legacy_catalogue", "index_role", "navigation") if d in depths), "unbound")
        annotation = annotations.get(path)
        if annotation is None:
            role, basis = tracked_role(path, links)
        else:
            role = annotation["role"]
            basis = "document_heading" if annotation["source"] == path else "documented_role_annotation"
        row = {"path": path, "status": depth, "links": links, "artifact_role": role, "role_basis": basis}
        if annotation is not None:
            row["role_evidence"] = {"source": annotation["source"], "note": annotation["note"]}
        row["unknown"] = ("Dataset/run contract incomplete" if depth != "semantic" else None)
        if role == "unknown":
            row["unknown"] = "Insufficient evidence for artifact role and dataset/run lineage"
        result.append(row)
    return result, [{"key": key, "locator": name} for key, name in sorted(missing_legacy)]


ARTIFACT_LOCATORS = ("manifest.json", "protocol.md", "README.md")
CAMPAIGN = "challenge-discovery4-20261108/execution-v1"
TOKEN = re.compile(r"(?<![\w./-])(?:[A-Za-z]:/)?[\w.-]+(?:/[\w.-]+)*/?(?![\w/-])")
LOCAL_LINK = re.compile(r"\[([^\]\n]+)\]\(([^\s)]+)\)")
REFERENCE_ROLE = re.compile(r"\b(protocol|manifest|registration|freeze|đăng ký|giao thức|lịch đã khóa)\b", re.I)
LOCATOR_CUE = re.compile(r"\b(job|artifact|receipt|private|root|folder|manifest|lưu|thư mục|kho)\b", re.I)


def tracked_markdown_lines(revision):
    """Read only lines in tracked Markdown that can contain a locator."""
    process = subprocess.run(
        ["git", "grep", "-n", "-I", "--no-color", "-E", r"[-_/]|protocol|manifest|registration", revision,
         "--", ":(glob)planning/research/**/*.md", ":(glob)planning/trader/research/**/*.md"],
        cwd=ROOT, capture_output=True, check=False,
    )
    require(process.returncode in (0, 1), process.stderr.decode("utf-8", errors="replace"))
    for line in process.stdout.decode("utf-8", errors="replace").splitlines():
        match = re.match(r"^[0-9a-f]{40}:([^:]+):(\d+):(.*)$", line)
        if match:
            document, line_number, value = match.groups()
            yield document, int(line_number), value


def private_reference(token, known, by_name, allow_bare=False):
    """Resolve exact components. A shortened name must have one scoped match."""
    parts = token.rstrip("/.").split("/")
    if "." in parts or ".." in parts:
        return None
    root_named = "ai-engine-jobs" in parts
    if root_named:
        parts = parts[parts.index("ai-engine-jobs") + 1:]
    if not parts or parts[0].lower() in {"http:", "https:"}:
        return None
    if parts[:2] == CAMPAIGN.split("/") and len(parts) >= 3:
        return "/".join(parts[:3]), "scoped_path", ()
    if root_named:
        # Do not resolve another job's execution-v1 to the campaign above.
        if parts[0].startswith("prop-"):
            return parts[0], "scoped_path", ()
        return None
    if parts[0] == "execution-v1" and len(parts) >= 2:
        candidates = tuple(by_name.get(parts[1], ()))
        expected = CAMPAIGN + "/" + parts[1]
        if len(candidates) > 1:
            return parts[1], "ambiguous_short_locator", candidates
        return (expected, "short_execution_path", ()) if expected in known else None

    first = parts[0]
    path_like = len(parts) > 1 or token.endswith("/")
    if not allow_bare and (not path_like or "-" not in first):
        return None
    candidates = tuple(by_name.get(first, ()))
    if len(candidates) > 1:
        return first, "ambiguous_short_locator", candidates
    return (candidates[0], "unique_short_locator", ()) if candidates else None


def document_relations(revision, paths, private_paths):
    by_name = defaultdict(list)
    for path in sorted(private_paths):
        by_name[PurePosixPath(path).name].append(path)
    private_links = defaultdict(set)
    missing = defaultdict(set)
    ambiguous = set()
    relations = set()
    for document, line, text in tracked_markdown_lines(revision):
        value = text.replace("\\", "/")
        where = f"{document}:{line}"
        code_spans = [(match.start(1), match.end(1)) for match in re.finditer(r"\x60([^\x60]+)\x60", value)]
        for match in TOKEN.finditer(value):
            token = match.group()
            if value[max(0, match.start() - 3):match.start()] == "://":
                continue
            quoted = any(start == match.start() and match.end() == end for start, end in code_spans)
            found = private_reference(token, private_paths, by_name,
                                      allow_bare=quoted and bool(LOCATOR_CUE.search(value[:match.start()])))
            if found is None:
                continue
            name, basis, candidates = found
            if candidates:
                ambiguous.add((name, where, candidates))
            elif name in private_paths:
                private_links[name].add((where, basis))
            elif basis == "scoped_path":
                missing[name].add(where)

        for label, target in LOCAL_LINK.findall(value):
            relation = REFERENCE_ROLE.search(label)
            if relation is None:
                continue
            target = unquote(target.split("#", 1)[0])
            if not target or ":" in target or target.startswith("/"):
                continue
            candidate = posixpath.normpath(posixpath.join(posixpath.dirname(document), target))
            if candidate in paths and candidate != document and candidate.endswith((".md", ".json")):
                relations.add((document, candidate, relation[0].lower(), line))
        # Some reports use plain code spans rather than Markdown links.
        for match in re.finditer(r"(protocol|manifest|registration|freeze)\s*:?\s*\x60([A-Za-z0-9_.-]+\.(?:md|json))\x60", value, re.I):
            candidate = posixpath.join(posixpath.dirname(document), match[2])
            if candidate in paths and candidate != document:
                relations.add((document, candidate, match[1].lower(), line))

    return (
        private_links, missing,
        [{"basename": name, "document": where, "candidates": list(candidates)}
         for name, where, candidates in sorted(ambiguous)],
        [{"source": source, "target": target, "label": label, "line": line,
          "binding": "document_reference_only"} for source, target, label, line in sorted(relations)],
    )


def verify_document_manifests(inventory, private_root, tracked_paths):
    """Read only exact hash-pinned manifests with a reviewed flat digest-map producer."""
    manifests = {}
    for row in by_key(inventory.get("document_manifest_bindings", []), "path").values():
        path = relative(row["path"])
        doc = relative(row["document"])
        require(path.name == "manifest.json" and doc.as_posix() in tracked_paths and doc.suffix == ".md"
                and HASH.fullmatch(row["sha256"]), f"invalid documented metadata pin: {path}")
        require(row["sha256"] in _research_file(doc).read_text(encoding="utf-8-sig"),
                f"manifest hash is not cited in its tracked report: {path}")
        entries = row["entries"]
        require(set(entries) == {"run_input", "output"} and all(entries.values()), f"invalid manifest roles: {path}")
        names = [name for group in entries.values() for name in group]
        require(len(names) == len(set(names)) and all(relative(name).name == name for name in names),
                f"invalid manifest projection: {path}")
        state = "not_checked"
        locators = []
        if private_root is not None:
            file = safe_path(private_root, row["path"])
            if file.is_file():
                require(file.stat().st_size <= 65536, f"documented metadata size limit: {path}")
                wire = file.read_bytes()
                require(sha256(wire).hexdigest() == row["sha256"], f"documented metadata SHA256 mismatch: {path}")
                value = json.loads(wire)
                require(isinstance(value, dict) and set(value) == set(names)
                        and all(isinstance(digest, str) and HASH.fullmatch(digest)
                                                       for digest in value.values()),
                        f"unexpected documented manifest schema: {path}")
                state = "metadata_hash_verified"
                for role, group in entries.items():
                    for name in group:
                        relative_file = (path.parent / name).as_posix()
                        locators.append({"role": role, "path": relative_file, "declared_sha256": value[name],
                                         "present": safe_path(private_root, relative_file).is_file(),
                                         "content_verified": False})
            else:
                state = "metadata_unavailable"
        manifests[path.parent.as_posix()] = {"path": row["path"], "document": row["document"],
                                            "status": state, "declared_artifact_bindings": locators}
    return manifests


def verify_private(inventory, private_root, datasets, studies, tracked_paths):
    bindings = by_key(inventory["metadata_bindings"], "key")
    partition_rows = by_key(inventory["partitions"], "id")
    by_key(inventory["payload_refs"], "path")
    reference_paths = set()
    private_links = defaultdict(set)
    checked = {}
    availability = []
    for row in bindings.values():
        path = relative(row["path"])
        require(path.name in METADATA_NAMES and path.suffix in {".json", ".md"},
                f"binding is outside approved metadata formats: {path}")
        require(row["path"] not in reference_paths and row["owner"] in datasets.keys() | studies.keys()
                and HASH.fullmatch(row["sha256"]), f"duplicate or invalid binding {row['key']}")
        reference_paths.add(row["path"])
        if private_root is None:
            continue
        file = safe_path(private_root, row["path"])
        if not file.is_file():
            checked[row["key"]] = ("metadata_unavailable", None)
            continue
        require(file.stat().st_size <= 1024 * 1024, f"metadata size limit: {file}")
        wire = file.read_bytes()
        require(sha256(wire).hexdigest() == row["sha256"], f"metadata SHA256 mismatch: {file}")
        checked[row["key"]] = ("metadata_hash_verified", json.loads(wire) if file.suffix == ".json" else None)

    for row in partition_rows.values():
        dataset, key = row["dataset"], row["key"]
        require(dataset in datasets and key in bindings and bindings[key]["owner"] == dataset,
                f"partition binding orphan: {row['id']}")
        stamp = checked.get(key, (None, None))[1]
        if dataset == "us500-v11-m1":
            require(row["year"] in range(2018, 2024) and re.fullmatch(r"q[1-4]-(ask|bid)", row["logical"])
                    and row["id"] == f"{dataset}/{row['year']}/{row['logical']}",
                    f"invalid source partition identity: {row['id']}")
            require(type(row["rows"]) is int and row["rows"] > 0 and row["first"] <= row["last"],
                    f"invalid minute partition coverage: {row['id']}")
            if stamp is not None:
                matches = [seal for seal in stamp["output_seals"] if seal["request"] == row["logical"]]
                require(len(matches) == 1 and stamp["year"] == row["year"]
                        and all(row[field] == matches[0][field] for field in ("rows", "first", "last", "sha256")),
                        f"partition differs from proof: {row['id']}")
        elif dataset == "eurusd-catalogue-raw" and stamp is not None:
            require(stamp["sha256"] == row["sha256"] and stamp["dates"] == [row["first_day"], row["last_day"]],
                    f"partition differs from raw seal: {row['id']}")

    for row in inventory["payload_refs"]:
        metadata_key = row.get("metadata_key")
        if metadata_key:
            require(metadata_key in bindings and bindings[metadata_key]["owner"] == row["owner"],
                    f"study payload orphan: {row['path']}")
            stamp = checked.get(metadata_key, (None, None))[1]
            if stamp is not None:
                require(stamp["result_sha256"] == row["sha256"] and stamp["rows"] == row["rows"],
                        f"annual outcome differs from run seal: {row['path']}")

    for row in [*partition_rows.values(), *inventory["payload_refs"]]:
        path = relative(row["path"])
        owner = row.get("dataset") or row["owner"]
        require(owner in datasets.keys() | studies.keys() and HASH.fullmatch(row["sha256"])
                and row["path"] not in reference_paths, f"duplicate or invalid opaque reference: {path}")
        reference_paths.add(row["path"])
        state = "not_checked" if private_root is None else (
            "present_payload_unopened" if safe_path(private_root, row["path"]).is_file() else "payload_unavailable")
        availability.append({"path": row["path"], "key": row.get("id", owner), "status": state})

    for row in studies.values():
        if "private_dir" in row:
            private_links[relative(row["private_dir"]).as_posix()].add(row["id"])

    directory_paths = set()
    unavailable_scopes = []
    for entry in inventory["private_directory_scope"]:
        if private_root is None:
            unavailable_scopes.append(entry["prefix"])
            continue
        directory = safe_path(private_root, entry["prefix"], allow_dot=True)
        if not directory.is_dir():
            unavailable_scopes.append(entry["prefix"])
            continue
        for child in directory.iterdir():
            if not child.name.startswith(entry["name_prefix"]) or not child.is_dir():
                continue
            path = child.relative_to(private_root).as_posix()
            require(path not in directory_paths, f"duplicate private directory in scopes: {path}")
            directory_paths.add(path)

    documented, missing, ambiguous, relations = document_relations(
        inventory["tracked_base"], tracked_paths, directory_paths
    )
    document_manifests = verify_document_manifests(inventory, private_root, tracked_paths)
    directories = []
    for path in sorted(directory_paths):
        refs = sorted(documented.get(path, ()))
        manifest = document_manifests.get(path)
        owners = private_links[path].copy()
        own_bindings = [row for row in bindings.values() if row["path"].startswith(path + "/")]
        owners.update(row["owner"] for row in own_bindings)
        local_locators = [name for name in ARTIFACT_LOCATORS
                          if safe_path(private_root, f"{path}/{name}").is_file()]
        verified = [row["path"] for row in own_bindings
                    if checked[row["key"]][0] == "metadata_hash_verified"]
        if manifest and manifest["status"] == "metadata_hash_verified":
            verified.append(manifest["path"])

        binding_basis = set()
        if any(checked.get(row["key"], (None,))[0] == "metadata_hash_verified"
               for row in partition_rows.values() if row["path"].startswith(path + "/")):
            binding_basis.add("sealed_source_partition_locators")
        if any(checked.get(row.get("metadata_key"), (None,))[0] == "metadata_hash_verified"
               for row in inventory["payload_refs"] if row["path"].startswith(path + "/")):
            binding_basis.add("sealed_annual_output_locators")
        if manifest and manifest["declared_artifact_bindings"]:
            binding_basis.add("manifest_declared_run_input_output_locators")
        documents = {where for where, _ in refs}
        if manifest:
            documents.add(manifest["document"])
        if owners:
            state = "bound_metadata_or_locator"
            role = "study_or_evidence_folder" if owners & studies.keys() else "source_data_folder"
            basis = "catalogue_relation"
        elif documents:
            state, role, basis = "documented_locator", "documented_private_artifacts", "tracked_document_locator"
        elif local_locators:
            state = "artifact_locator_present"
            role, basis = "unverified_private_artifact_locator", "exact_root_filename_stat"
        else:
            state, role, basis = "directory_only", "unknown_directory_contents", "directory_entry_only"

        directories.append({
            "path": path, "keys": sorted(owners), "documents": sorted(documents),
            "status": state, "artifact_role": role, "role_basis": basis,
            "root_artifact_locators": local_locators,
            "document_references": [{"source": where, "basis": ref_basis} for where, ref_basis in refs],
            "verified_metadata": sorted(verified), "source_run_binding_basis": sorted(binding_basis),
            "run_manifest": manifest,
        })

    return {
        "coverage": dict(Counter(row["status"] for row in directories)),
        "coverage_axes": {
            "root_manifest_present": sum("manifest.json" in row["root_artifact_locators"] for row in directories),
            "root_protocol_present": sum("protocol.md" in row["root_artifact_locators"] for row in directories),
            "root_readme_present": sum("README.md" in row["root_artifact_locators"] for row in directories),
            "document_linked": sum(bool(row["documents"]) for row in directories),
            "metadata_hash_verified": sum(bool(row["verified_metadata"]) for row in directories),
            "source_run_locator_bound": sum(bool(row["source_run_binding_basis"]) for row in directories),
        },
        "directories": directories,
        "unavailable_scopes": unavailable_scopes,
        "documented_locators_not_in_directory_inventory": {
            path: sorted(locators) for path, locators in sorted(missing.items())
        },
        "ambiguous_short_locators": ambiguous,
        "document_relations": relations,
        "document_manifests": list(document_manifests.values()),
        "metadata": [{"key": key, "path": row["path"], "status": checked.get(key, ("not_checked", None))[0]}
                     for key, row in bindings.items()],
        "opaque_refs": availability,
        "study_directory_refs": [{"path": path, "keys": sorted(keys),
                                  "status": ("not_checked" if private_root is None else
                                             "directory_present" if path in directory_paths else "directory_unavailable")}
                                 for path, keys in sorted(private_links.items()) if keys],
    }


def legacy_corpus(inventory, paths):
    meta = inventory["legacy_corpus_meta"]
    path = RESEARCH + meta["source"]
    require(path in paths, "legacy corpus metadata locator is not tracked")
    wire = _research_file(path).read_bytes().replace(b"\r\n", b"\n")
    require(sha256(wire).hexdigest() == meta["sha256"], "legacy corpus card hash mismatch")
    card = json.loads(wire)
    profiles = by_key(card["profiles"], meta["identity_field"])
    require(len(profiles) == meta["profile_count"]
            and len({row["rank"] for row in profiles.values()}) == len(profiles)
            and all(HASH.fullmatch(key) for key in profiles)
            and sum(row["aliases"] for row in profiles.values()) == meta["alias_counts_total"]
            and card["cells"] == meta["benchmark_cells"]
            and card["selection_uses_later"] is False, "legacy corpus metadata census mismatch")
    fields = ("rank", "file", "sha256", "aliases", "pattern", "oscillator", "native_asset",
              "native_timeframe", "benchmark_timeframe", "assets", "volume_required")
    return {**meta, "profiles": [{field: row[field] for field in fields} for row in profiles.values()]}


def fee_recipes(inventory, paths, records, studies):
    table = inventory["eurusd_catalogue13_recipes"]
    path = RESEARCH + table["source"]
    require(table["study"] in studies and path in paths, "Catalogue13 cost attribution orphan")
    wire = _research_file(path).read_bytes().replace(b"\r\n", b"\n")
    require(sha256(wire).hexdigest() == table["sha256"], "Catalogue13 published table hash mismatch")
    recipes = by_key(table["recipes"], "id")
    published = {}
    for line in wire.decode("utf-8-sig").splitlines():
        fields = [cell.strip() for cell in line.strip("|").split("|")]
        if len(fields) != 8 or not re.fullmatch(r"h[14]-[a-z0-9-]+", fields[0]):
            continue
        alias, count, holding, *money = fields
        if "/" not in holding or not count.isdecimal():
            continue
        require(alias not in published, f"duplicate published recipe: {alias}")
        published[alias] = (int(count), tuple(Decimal(value.replace(".", "").replace(",", ".")) for value in money))
    require(len(published) == len(recipes) == 24, "Catalogue13 source table census mismatch")
    for key, row in recipes.items():
        require(key == f"eurusd-{row['row_alias']}-r025-v1", f"recipe key drift: {key}")
        gross, commission, slip, swap, net = (
            Decimal(row[name]) for name in ("gross_after_spread_usd", "commission_usd", "slippage_usd",
                                            "financing_usd", "net_stress_usd")
        )
        require(published.get(row["row_alias"]) == (row["closed_trades"], (gross, commission, slip, swap, net)),
                f"published fee attribution mismatch: {key}")
        before_swap = gross - commission - slip
        layer = ("gross_after_spread_not_positive" if gross <= 0 else
                 "commission_plus_slippage" if before_swap <= 0 else "financing")
        require(before_swap - swap == net < 0 and layer == row["first_negative_layer"],
                f"cost layer or reconciliation mismatch: {key}")
        for link in by_key(row["catalogue_links"], "id").values():
            require(link["id"] in records, f"legacy recipe link orphan: {key}")
            parent = records[link["id"]]
            exact = key == parent.get("candidate_id")
            related = key in parent.get("implementations", []) or key in parent.get("version_decisions", {})
            require((exact and link["relationship"] == "exact_recipe")
                    or (not exact and related and link["relationship"] == "related_version_in_family"),
                    f"legacy recipe identity mismatch: {key}")
    require(len(recipes) == 24 and Counter(row["first_negative_layer"] for row in recipes.values())
            == table["counts_by_first_negative_layer"], "Catalogue13 cost census drift")
    for study in studies.values():
        require(set(study.get("recipe_keys", [])) <= recipes.keys(), f"study recipe orphan: {study['id']}")
    return {**table, "recipes": recipes}


def inspect(private_root=None):
    catalogue = json.loads((ROOT / CATALOGUE).read_text(encoding="utf-8-sig"))
    inventory = catalogue["evidence_inventory"]
    require(inventory["version"] == 1, "unsupported evidence inventory version")
    records = by_key(catalogue["records"], "id")
    require(len(records) == catalogue["record_count"], "legacy catalogue count drift")
    datasets = by_key(inventory["datasets"], "id")
    studies = by_key(inventory["studies"], "id")
    require(len(datasets) + len(studies) == len(datasets.keys() | studies.keys()), "duplicate dataset/study ID")
    for row in datasets.values():
        require(all(row.get(field) for field in DATASET_FIELDS), f"dataset fields missing: {row['id']}")
        require(set(row.get("parents", [])) <= datasets.keys() - {row["id"]}, f"dataset parent orphan: {row['id']}")
        validate_quality(row)
    for row in studies.values():
        require(all(row.get(field) for field in STUDY_FIELDS), f"study fields missing: {row['id']}")
        require(set(row["candidates"]) <= records.keys(), f"candidate orphan: {row['id']}")
        require(row["inputs"] and set(row["inputs"]) <= datasets.keys(), f"dataset orphan: {row['id']}")
        require(set(row.get("depends_on", [])) <= studies.keys() - {row["id"]}, f"study parent orphan: {row['id']}")
        require(not (row["verdict"] in {"not_run", "paused_before_run"} and "outcome" in row["docs"]),
                f"unrun work has an outcome: {row['id']}")
        validate_quality(row)

    base = inventory["tracked_base"]
    require(re.fullmatch(r"[0-9a-f]{40}", base) is not None, "invalid scope commit")
    snapshot = git_paths(base, inventory["tracked_scope"])
    current = git_paths("HEAD", inventory["tracked_scope"])
    require(bool(snapshot), "empty tracked snapshot")
    tracked, legacy_missing = classify_tracked(catalogue, inventory, snapshot)
    private = verify_private(inventory, private_root, datasets, studies, snapshot)
    require(inventory["legacy_corpus_meta"]["dataset"] in datasets, "legacy corpus dataset orphan")
    corpus = legacy_corpus(inventory, snapshot)
    costs = fee_recipes(inventory, snapshot, records, studies)
    broker_observations = by_key(inventory.get("broker_observations", []), "id")
    for row in broker_observations.values():
        require(all(_research_file(RESEARCH + relative(row[field]).as_posix()).is_file() for field in ("report", "summary")),
                f"broker observation report locator missing: {row['id']}")
        manifest = relative(row["private_manifest"])
        require(manifest.name == "manifest.json" and HASH.fullmatch(row["private_manifest_sha256"]),
                f"invalid broker observation manifest: {row['id']}")
        row["private_manifest_status"] = "not_checked"
        if private_root is not None:
            file = safe_path(private_root, row["private_manifest"])
            row["private_manifest_status"] = "unavailable"
            if file.is_file():
                require(file.stat().st_size <= 1024 * 1024, f"broker observation manifest too large: {row['id']}")
                require(sha256(file.read_bytes()).hexdigest() == row["private_manifest_sha256"],
                        f"broker observation manifest hash differs: {row['id']}")
                row["private_manifest_status"] = "metadata_hash_verified"
    return {
        "tracked_base": base, "tracked_paths": tracked,
        "tracked_coverage": dict(Counter(row["status"] for row in tracked)),
        "artifact_role_counts": dict(Counter(row["artifact_role"] for row in tracked)),
        "role_basis_counts": dict(Counter(row["role_basis"] for row in tracked)),
        "unknown_tracked_roles": [row["path"] for row in tracked if row["artifact_role"] == "unknown"],
        "tracked_changes_since_scope": {"added": sorted(current - snapshot), "removed": sorted(snapshot - current)},
        "legacy_catalogue_records": len(records), "legacy_records": records,
        "legacy_corpus": corpus, "legacy_exposure": inventory["legacy_exposure"],
        "eurusd_catalogue13_recipes": costs,
        "legacy_source_locator_review": legacy_missing,
        "datasets": datasets, "studies": studies, "broker_observations": broker_observations,
        "private": private, "gaps": inventory["gaps"],
        "price_or_private_outcome_payload_opened": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, help="Explicit ai-engine-jobs root for metadata-only checks")
    view = parser.add_mutually_exclusive_group()
    view.add_argument("--key", help="Show a dataset or study by ID, or studies linked to a catalogue ID")
    view.add_argument("--path", help="Show a tracked or scoped private path and its documentary links")
    view.add_argument("--all", action="store_true", help="Emit every scoped path and its evidence links")
    args = parser.parse_args()
    result = inspect(args.private_root.resolve() if args.private_root else None)
    if args.key:
        matching_candidates = {
            key for key, row in result["legacy_records"].items()
            if args.key == key or args.key == row.get("candidate_id") or args.key in row.get("version_decisions", {})
        }
        fee_table = result["eurusd_catalogue13_recipes"]
        matching_recipes = [row for row in fee_table["recipes"].values()
                            if args.key in (row["id"], row["row_alias"], fee_table["study"])
                            or args.key in {link["id"] for link in row["catalogue_links"]}]
        linked = [row for row in result["studies"].values()
                  if args.key == row["id"] or args.key in row["inputs"]
                  or matching_candidates.intersection(row["candidates"])
                  or (matching_recipes and row["id"] == fee_table["study"])
                  or any(recipe["id"] in row.get("recipe_keys", []) for recipe in matching_recipes)]
        related_keys = {args.key, *matching_candidates, *(row["id"] for row in linked)}
        result = {
            "key": args.key, "dataset": result["datasets"].get(args.key), "studies": linked,
            "broker_observation": result["broker_observations"].get(args.key),
            "legacy_candidates": [result["legacy_records"][key] for key in sorted(matching_candidates)],
            "tracked_evidence": [row for row in result["tracked_paths"]
                                 if any(link["key"] in related_keys for link in row["links"])],
            "private_locators": [row for row in result["private"]["opaque_refs"]
                                 if row["key"] in related_keys or row["key"].startswith(args.key + "/")],
            "legacy_corpus": result["legacy_corpus"] if args.key == result["legacy_corpus"]["dataset"] else None,
            "fee_attribution": ({**fee_table, "recipes": matching_recipes} if matching_recipes else None),
        }
        if not (result["dataset"] or result["broker_observation"] or linked or matching_candidates or matching_recipes):
            parser.exit(1, f"No inventory binding for {args.key}. Use --all to inspect other locators.\n")
    elif args.path:
        path = relative(args.path.replace("\\", "/")).as_posix()
        row = next((row for row in result["tracked_paths"] + result["private"]["directories"]
                    if row["path"] == path), None)
        if row is None:
            parser.exit(1, f"No exact inventory match for {path}. Use --all to list paths.\n")
        result = {"entry": row, "document_relations": [
            edge for edge in result["private"]["document_relations"] if path in (edge["source"], edge["target"])
        ], "documented_private_directories": [
            directory["path"] for directory in result["private"]["directories"]
            if any(doc == path or doc.rpartition(":")[0] == path for doc in directory["documents"])
        ]}
    elif not args.all:
        private = result["private"]
        result = {
            "tracked_base": result["tracked_base"], "tracked_coverage": result["tracked_coverage"],
            "artifact_role_counts": result["artifact_role_counts"], "role_basis_counts": result["role_basis_counts"],
            "tracked_changes_since_scope": result["tracked_changes_since_scope"],
            "legacy_catalogue_records": result["legacy_catalogue_records"],
            "legacy_locator_review": len(result["legacy_source_locator_review"]),
            "datasets": len(result["datasets"]), "studies": len(result["studies"]),
            "broker_observations": len(result["broker_observations"]),
            "legacy_corpus_profiles": result["legacy_corpus"]["profile_count"],
            "eurusd_catalogue13_recipe_labels": result["eurusd_catalogue13_recipes"]["counts_by_first_negative_layer"],
            "private_directory_coverage": private["coverage"],
            "private_coverage_axes": private["coverage_axes"],
            "document_relations": len(private["document_relations"]),
            "documents_with_direct_relations": len({row["source"] for row in private["document_relations"]}),
            "ambiguous_short_locators": len(private["ambiguous_short_locators"]),
            "document_manifest_checks": dict(Counter(row["status"] for row in private["document_manifests"])),
            "private_unavailable_scopes": private["unavailable_scopes"],
            "metadata_checks": dict(Counter(row["status"] for row in private["metadata"])),
            "opaque_refs": dict(Counter(row["status"] for row in private["opaque_refs"])),
            "price_or_outcome_payload_opened": False,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
