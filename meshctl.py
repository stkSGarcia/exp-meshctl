#!/usr/bin/env python3
"""Manage mesh resources from YAML specs."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
RUNTIME_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
MEMORY_RE = re.compile(r"^(0|[1-9][0-9]*)(Ki|Mi|Gi|Ti)?$")
CPU_RE = re.compile(r"^(0|[1-9][0-9]*)(m)?$")
MEMORY_UNITS = {
    None: 1,
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
}
AUTH_DIGEST_ALGORITHMS = {"SHA-256", "SHA-384", "SHA-512"}
ENCRYPTION_SOURCES = {"None", "Secret", "Service"}
ENCRYPTION_CLIENT_MODES = {"None", "Authenticate", "Validate"}
ONE_SHOT_COLLECTIONS = {
    "task": "tasks",
    "snapshot": "snapshots",
    "recovery": "recoveries",
}
SCOPE_KEYS = {"stores", "blueprints", "tallies", "definitions", "procedures"}
RUNTIME_CATALOG = {
    "3.0.0": "deprecated",
    "3.1.0": "skipped",
    "3.1.1": "supported",
    "4.0.0": "supported",
    "4.0.1": "supported",
}
MIGRATION_STRATEGIES = {"FullStop", "LiveMigration", "RollingPatch"}
MIGRATION_STAGES = {
    "FullStop": ["Migrate"],
    "RollingPatch": ["Migrate"],
    "LiveMigration": ["Prepare", "Replicate", "Cutover"],
}
EXPOSURE_TYPES = {"Gateway", "DirectPort", "Balancer"}
DEFAULT_GATEWAY_HOST = "mesh.example.local"
DEFAULT_SERVICE_PORT = 443
DEFAULT_DIRECT_PORT = 443
MANAGEMENT_PORT = 9990


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "mesh":
        if args.mesh_operation == "create":
            return mesh_create(args.file)
        if args.mesh_operation == "list":
            return mesh_list()
        if args.mesh_operation == "describe":
            return mesh_describe(args.name)
        if args.mesh_operation == "delete":
            return mesh_delete(args.name)
        if args.mesh_operation == "update":
            return mesh_update(args.file)
        if args.mesh_operation == "migrate":
            return mesh_migrate(args.name, args.rollback)
        if args.mesh_operation == "shell":
            return mesh_shell(args.name)
    if args.command == "vault":
        if args.vault_operation == "create":
            return vault_create(args.file)
        if args.vault_operation == "list":
            return vault_list()
        if args.vault_operation == "describe":
            return vault_describe(args.name)
        if args.vault_operation == "delete":
            return vault_delete(args.name)
        if args.vault_operation == "update":
            return vault_update(args.file)
    if args.command in ONE_SHOT_COLLECTIONS:
        if args.operation == "create":
            return one_shot_create(args.command, args.file)
        if args.operation == "list":
            return one_shot_list(args.command)
        if args.operation == "describe":
            return one_shot_describe(args.command, args.name)
        if args.operation == "delete":
            return one_shot_delete(args.command, args.name)
        if args.operation == "update":
            return one_shot_update(args.command, args.file)
        if args.operation == "run":
            return one_shot_run(args.command, args.name)
    parser.print_help(sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meshctl.py")
    commands = parser.add_subparsers(dest="command", required=True)

    mesh = commands.add_parser("mesh")
    mesh_operations = mesh.add_subparsers(dest="mesh_operation", required=True)

    create = mesh_operations.add_parser("create")
    create.add_argument("-f", "--file", required=True)

    update = mesh_operations.add_parser("update")
    update.add_argument("-f", "--file", required=True)

    mesh_operations.add_parser("list")

    describe = mesh_operations.add_parser("describe")
    describe.add_argument("name")

    delete = mesh_operations.add_parser("delete")
    delete.add_argument("name")

    migrate = mesh_operations.add_parser("migrate")
    migrate.add_argument("name")
    migrate.add_argument("--rollback", action="store_true")

    shell = mesh_operations.add_parser("shell")
    shell.add_argument("name")

    vault = commands.add_parser("vault")
    vault_operations = vault.add_subparsers(dest="vault_operation", required=True)

    vault_create_parser = vault_operations.add_parser("create")
    vault_create_parser.add_argument("-f", "--file", required=True)

    vault_update_parser = vault_operations.add_parser("update")
    vault_update_parser.add_argument("-f", "--file", required=True)

    vault_operations.add_parser("list")

    vault_describe_parser = vault_operations.add_parser("describe")
    vault_describe_parser.add_argument("name")

    vault_delete_parser = vault_operations.add_parser("delete")
    vault_delete_parser.add_argument("name")

    for kind in ONE_SHOT_COLLECTIONS:
        one_shot = commands.add_parser(kind)
        operations = one_shot.add_subparsers(dest="operation", required=True)

        create_parser = operations.add_parser("create")
        create_parser.add_argument("-f", "--file", required=True)

        update_parser = operations.add_parser("update")
        update_parser.add_argument("-f", "--file", required=True)

        operations.add_parser("list")

        describe_parser = operations.add_parser("describe")
        describe_parser.add_argument("name")

        delete_parser = operations.add_parser("delete")
        delete_parser.add_argument("name")

        run_parser = operations.add_parser("run")
        run_parser.add_argument("name")
    return parser


def mesh_create(input_path: str) -> int:
    document, errors = load_resource_input(input_path)
    if errors:
        print_errors(errors)
        return 0

    store = load_store()
    meshes = store["meshes"]
    resource, errors = normalize_mesh_for_create(document)
    warnings = collect_runtime_warnings(resource)
    name = resource.get("metadata", {}).get("name")
    if isinstance(name, str) and name in meshes:
        errors.append(error("metadata.name", "Mesh already exists", "duplicate"))

    if errors:
        print_errors(errors)
        return 0

    meshes[name] = resource
    save_store(store)
    print_json(with_warnings(public_resource(resource), warnings))
    return 0


def mesh_update(input_path: str) -> int:
    document, errors = load_resource_input(input_path)
    if errors:
        print_errors(errors)
        return 0

    metadata = document.get("metadata")
    name = metadata.get("name") if isinstance(metadata, dict) else None
    errors = []
    validate_name(name, errors)
    if errors:
        print_errors(errors)
        return 0

    store = load_store()
    meshes = store["meshes"]
    if name not in meshes:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0

    stored = upgrade_stored_resource(meshes[name])
    candidate = deep_merge(stored, update_patch(document))
    resume_without_count = should_resume_without_count(stored, document)
    if resume_without_count:
        desired = stored.get("status", {}).get("desiredInstancesOnResume")
        candidate.setdefault("spec", {})["instances"] = desired

    errors = validate_merged_resource(candidate, stored)
    if errors:
        print_errors(errors)
        return 0

    runtime_changed = is_runtime_version_change(stored, candidate)
    warnings = collect_runtime_warnings(candidate)
    canonicalize_resource_access(candidate)
    reconcile_update_status(stored, candidate, resume_without_count)
    if runtime_changed:
        start_migration(stored, candidate)
    finalize_mesh_status(candidate)
    meshes[name] = candidate
    save_store(store)
    print_json(with_warnings(public_resource(candidate), warnings))
    return 0


def mesh_list() -> int:
    store = load_store()
    meshes = store["meshes"]
    summaries = [
        {"name": name, "status": {"state": public_resource(resource)["status"]["state"]}}
        for name, resource in sorted(meshes.items(), key=lambda item: item[0])
    ]
    print_json(summaries)
    return 0


def mesh_describe(name: str) -> int:
    store = load_store()
    meshes = store["meshes"]
    if name not in meshes:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0

    resource = upgrade_stored_resource(meshes[name])
    completed = complete_pending_transition(resource)
    if completed or resource != meshes[name]:
        meshes[name] = resource
        save_store(store)
    print_json(public_resource(resource))
    return 0


def mesh_delete(name: str) -> int:
    store = load_store()
    meshes = store["meshes"]
    vaults = store["vaults"]
    if name not in meshes:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0
    dependents = sorted(
        vault_name
        for vault_name, vault in vaults.items()
        if get_path(vault, ["spec", "meshRef"]) == name
    )
    if dependents:
        print_errors(
            [
                error(
                    "metadata.name",
                    f"Mesh {name} is referenced by vaults: {', '.join(dependents)}",
                    "conflict",
                )
            ]
        )
        return 0
    del meshes[name]
    save_store(store)
    print_json({"message": f"Deleted mesh {name}", "metadata": {"name": name}})
    return 0


def mesh_migrate(name: str, rollback: bool) -> int:
    store = load_store()
    meshes = store["meshes"]
    if name not in meshes:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0

    resource = upgrade_stored_resource(meshes[name])
    migration = resource.get("status", {}).get("migration")
    if not isinstance(migration, dict):
        print_errors(
            [
                error(
                    "status.migration",
                    f"no active migration for mesh '{name}'",
                    "invalid",
                )
            ]
        )
        return 0

    if rollback:
        errors = rollback_migration(resource)
        if errors:
            print_errors(errors)
            return 0
    else:
        advance_migration(resource)

    finalize_mesh_status(resource)
    meshes[name] = resource
    save_store(store)
    print_json(public_resource(resource))
    return 0


def mesh_shell(name: str) -> int:
    store = load_store()
    meshes = store["meshes"]
    if name not in meshes:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0

    resource = upgrade_stored_resource(meshes[name])
    public = public_resource(resource)
    connection_details = get_path(public, ["status", "connectionDetails"])
    if not isinstance(connection_details, dict):
        print_errors(
            [
                error(
                    "spec.exposure",
                    f"mesh '{name}' has no exposure configured",
                    "invalid",
                )
            ]
        )
        return 0

    print_json(connection_details)
    return 0


def vault_create(input_path: str) -> int:
    document, errors = load_resource_input(input_path)
    if errors:
        print_errors(errors)
        return 0

    store = load_store()
    vaults = store["vaults"]
    resource, errors = normalize_vault_for_create(document)
    name = resource.get("metadata", {}).get("name")
    if isinstance(name, str) and name in vaults:
        errors.append(error("metadata.name", "Vault already exists", "duplicate"))
    validate_vault_resource(resource, store, None, errors)

    if errors:
        print_errors(errors)
        return 0

    vaults[name] = resource
    save_store(store)
    print_json(public_vault(resource, store["meshes"]))
    return 0


def vault_update(input_path: str) -> int:
    document, errors = load_resource_input(input_path)
    if errors:
        print_errors(errors)
        return 0

    metadata = document.get("metadata")
    name = metadata.get("name") if isinstance(metadata, dict) else None
    errors = []
    validate_name(name, errors)
    if errors:
        print_errors(errors)
        return 0

    store = load_store()
    vaults = store["vaults"]
    if name not in vaults:
        print_errors([error("metadata.name", "Vault not found", "not_found")])
        return 0

    stored = upgrade_stored_vault(vaults[name])
    candidate = deep_merge(stored, vault_update_patch(document))
    validate_vault_resource(candidate, store, name, errors, stored)
    if errors:
        print_errors(errors)
        return 0

    vaults[name] = candidate
    save_store(store)
    print_json(public_vault(candidate, store["meshes"]))
    return 0


def vault_list() -> int:
    store = load_store()
    meshes = store["meshes"]
    summaries = []
    for name, vault in sorted(store["vaults"].items(), key=lambda item: item[0]):
        public = public_vault(vault, meshes)
        summaries.append(
            {
                "name": name,
                "meshRef": public["spec"].get("meshRef"),
                "vaultName": public["spec"].get("vaultName"),
                "status": {"state": public["status"]["state"]},
            }
        )
    print_json(summaries)
    return 0


def vault_describe(name: str) -> int:
    store = load_store()
    vaults = store["vaults"]
    if name not in vaults:
        print_errors([error("metadata.name", "Vault not found", "not_found")])
        return 0
    print_json(public_vault(vaults[name], store["meshes"]))
    return 0


def vault_delete(name: str) -> int:
    store = load_store()
    vaults = store["vaults"]
    if name not in vaults:
        print_errors([error("metadata.name", "Vault not found", "not_found")])
        return 0
    del vaults[name]
    save_store(store)
    print_json({"message": f"Deleted vault {name}", "metadata": {"name": name}})
    return 0


def one_shot_create(kind: str, input_path: str) -> int:
    document, errors = load_resource_input(input_path)
    if errors:
        print_errors(errors)
        return 0

    store = load_store()
    collection = store[collection_name(kind)]
    resource, errors = normalize_one_shot_for_create(kind, document, store)
    name = resource.get("metadata", {}).get("name")
    if isinstance(name, str) and name in collection:
        errors.append(error("metadata.name", f"{kind.title()} already exists", "duplicate"))

    if errors:
        print_errors(errors)
        return 0

    collection[name] = resource
    save_store(store)
    print_json(public_one_shot(kind, resource))
    return 0


def one_shot_update(kind: str, input_path: str) -> int:
    document, errors = load_resource_input(input_path)
    if errors:
        print_errors(errors)
        return 0

    metadata = document.get("metadata")
    name = metadata.get("name") if isinstance(metadata, dict) else None
    errors = []
    validate_name(name, errors)
    if errors:
        print_errors(errors)
        return 0

    store = load_store()
    collection = store[collection_name(kind)]
    if name not in collection:
        print_errors([error("metadata.name", f"{kind.title()} not found", "not_found")])
        return 0

    stored = upgrade_one_shot(collection[name])
    candidate = deep_merge(stored, one_shot_update_patch(document))
    if candidate.get("spec") != stored.get("spec"):
        errors.append(error("spec", "spec is immutable after creation", "immutable"))
    if errors:
        print_errors(errors)
        return 0

    collection[name] = candidate
    save_store(store)
    print_json(public_one_shot(kind, candidate))
    return 0


def one_shot_list(kind: str) -> int:
    store = load_store()
    summaries = [
        one_shot_summary(kind, name, resource)
        for name, resource in sorted(store[collection_name(kind)].items(), key=lambda item: item[0])
    ]
    print_json(summaries)
    return 0


def one_shot_describe(kind: str, name: str) -> int:
    store = load_store()
    collection = store[collection_name(kind)]
    if name not in collection:
        print_errors([error("metadata.name", f"{kind.title()} not found", "not_found")])
        return 0
    print_json(public_one_shot(kind, collection[name]))
    return 0


def one_shot_delete(kind: str, name: str) -> int:
    store = load_store()
    collection = store[collection_name(kind)]
    if name not in collection:
        print_errors([error("metadata.name", f"{kind.title()} not found", "not_found")])
        return 0
    if kind == "snapshot":
        dependents = sorted(
            recovery_name
            for recovery_name, recovery in store["recoveries"].items()
            if get_path(recovery, ["spec", "snapshotRef"]) == name
        )
        if dependents:
            print_errors(
                [
                    error(
                        "metadata.name",
                        f"Snapshot {name} is referenced by recoveries: {', '.join(dependents)}",
                        "conflict",
                    )
                ]
            )
            return 0
    del collection[name]
    save_store(store)
    print_json({"message": f"Deleted {kind} {name}", "metadata": {"name": name}})
    return 0


def one_shot_run(kind: str, name: str) -> int:
    store = load_store()
    collection = store[collection_name(kind)]
    if name not in collection:
        print_errors([error("metadata.name", f"{kind.title()} not found", "not_found")])
        return 0

    resource = upgrade_one_shot(collection[name])
    state = get_path(resource, ["status", "state"])
    if state != "Initializing":
        print_errors(
            [
                error(
                    "status.state",
                    f"resource is in state '{state}', expected 'Initializing'",
                    "invalid",
                )
            ]
        )
        return 0

    resource.setdefault("status", {})["state"] = "Running"
    if kind == "task":
        run_task(resource)
    elif kind == "snapshot":
        run_snapshot(resource, store["meshes"])
    elif kind == "recovery":
        run_recovery(resource, store["meshes"])

    collection[name] = resource
    save_store(store)
    print_json(public_one_shot(kind, resource))
    return 0


def store_path() -> Path:
    override = os.environ.get("MESHCTL_STORE")
    if override:
        return Path(override)
    return Path.cwd() / ".meshctl_store.json"


def empty_store() -> dict[str, dict[str, dict[str, Any]]]:
    return {"meshes": {}, "vaults": {}, "tasks": {}, "snapshots": {}, "recoveries": {}}


def clean_resource_collection(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    return {
        str(name): resource
        for name, resource in value.items()
        if isinstance(resource, dict)
    }


def load_store() -> dict[str, dict[str, dict[str, Any]]]:
    path = store_path()
    if not path.exists():
        return empty_store()
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_store()
    if not isinstance(content, dict):
        return empty_store()
    if any(key in content for key in empty_store()):
        store = empty_store()
        for key in store:
            store[key] = clean_resource_collection(content.get(key))
        return store
    store = empty_store()
    store["meshes"] = clean_resource_collection(content)
    return store


def save_store(store: dict[str, dict[str, dict[str, Any]]]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, sort_keys=True), encoding="utf-8")


def load_resource_input(input_path: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    document, parse_error = load_yaml_document(Path(input_path))
    if parse_error:
        return {}, [error("", parse_error, "parse")]
    if not isinstance(document, dict):
        return {}, [error("", "YAML document must be a mapping", "invalid")]
    return document, []


def load_yaml_document(path: Path) -> tuple[Any, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, str(exc)

    try:
        import yaml  # type: ignore[import-not-found]

        docs = list(yaml.safe_load_all(text))
    except ImportError:
        return parse_simple_yaml(text)
    except Exception as exc:  # pragma: no cover - exact parser exceptions vary
        return None, str(exc)

    if len(docs) != 1:
        return None, "YAML input must contain exactly one document"
    return docs[0], None


def parse_simple_yaml(text: str) -> tuple[Any, str | None]:
    lines: list[tuple[int, str]] = []
    document_markers = 0
    for raw_line in text.splitlines():
        if raw_line.strip() == "---":
            document_markers += 1
            if lines or document_markers > 1:
                return None, "YAML input must contain exactly one document"
            continue
        if raw_line.strip() == "...":
            continue
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "\t" in raw_line:
            return None, "Tabs are not supported in YAML indentation"
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line[indent:]))

    if not lines:
        return None, None
    if lines[0][0] != 0:
        return None, "Root mapping must start at indentation zero"
    if lines[0][1].startswith("- "):
        values: list[Any] = []
        for indent, content in lines:
            if indent != 0 or not content.startswith("- "):
                return None, f"Invalid sequence line: {content}"
            values.append(parse_scalar(content[2:].strip()))
        return values, None

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for index, (indent, content) in enumerate(lines):
        if ":" not in content:
            return None, f"Invalid mapping line: {content}"
        key, raw_value = content.split(":", 1)
        key = key.strip()
        if not key:
            return None, "Mapping keys must not be empty"
        value_text = raw_value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            return None, "Invalid indentation"

        parent = stack[-1][1]
        has_nested_value = index + 1 < len(lines) and lines[index + 1][0] > indent
        if value_text == "" and has_nested_value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        elif value_text == "":
            parent[key] = None
        else:
            parent[key] = parse_scalar(value_text)

    return root, None


def parse_scalar(value: str) -> Any:
    if value.startswith(("[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if re.fullmatch(r"-?(0|[1-9][0-9]*)", value):
        return int(value)
    return value


def normalize_mesh_for_create(
    document: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    metadata = document.get("metadata")
    spec = document.get("spec")

    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    name = metadata.get("name")
    validate_name(name, errors)
    validate_forbidden_autoscaling(spec, "spec", errors)

    normalized_spec: dict[str, Any] = {}
    normalize_instances(spec, normalized_spec, errors, default=1)
    normalize_runtime(spec, normalized_spec, errors)
    normalize_resources(spec, normalized_spec, errors)
    normalize_access(spec, normalized_spec, errors)
    normalize_migration(spec, normalized_spec, errors)
    normalize_network(spec, normalized_spec, errors, apply_defaults=True)
    normalize_exposure(spec, normalized_spec, errors)
    normalize_management(spec, normalized_spec, errors, apply_defaults=True)
    if "regions" in spec:
        normalized_spec["regions"] = copy.deepcopy(spec.get("regions"))

    resource = {
        "metadata": {"name": name},
        "spec": normalized_spec,
        "status": {},
    }
    initialize_status(resource)
    validate_merged_resource(resource, None, errors)
    if not errors:
        canonicalize_resource_access(resource)
    return resource, errors


def normalize_vault_for_create(
    document: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    metadata = document.get("metadata")
    spec = document.get("spec")

    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    name = metadata.get("name")
    validate_name(name, errors)

    normalized_spec: dict[str, Any] = {}
    mesh_ref = spec.get("meshRef")
    normalize_required_string(mesh_ref, "spec.meshRef", "Mesh reference is required", errors)
    if isinstance(mesh_ref, str) and mesh_ref:
        normalized_spec["meshRef"] = mesh_ref

    vault_name = spec.get("vaultName", name)
    if isinstance(vault_name, str) and vault_name:
        normalized_spec["vaultName"] = vault_name
    else:
        errors.append(error("spec.vaultName", "Vault name must be a non-empty string", "invalid"))

    update_policy = spec.get("updatePolicy", "retain")
    normalized_spec["updatePolicy"] = update_policy
    validate_vault_update_policy(update_policy, errors)

    for field in ("template", "templateRef"):
        if field in spec:
            value = spec.get(field)
            if value is not None and not isinstance(value, str):
                errors.append(error(f"spec.{field}", f"{field} must be a string", "invalid"))
            if value is not None:
                normalized_spec[field] = value

    validate_template_exclusivity(normalized_spec, errors)
    return {"metadata": {"name": name}, "spec": normalized_spec, "status": {}}, errors


def normalize_required_string(
    value: Any,
    field: str,
    message: str,
    errors: list[dict[str, str]],
) -> None:
    if value is None or value == "":
        errors.append(error(field, message, "required"))
    elif not isinstance(value, str):
        errors.append(error(field, f"{field} must be a string", "invalid"))


def vault_update_patch(document: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if isinstance(document.get("metadata"), dict):
        patch["metadata"] = {"name": document["metadata"].get("name")}
    if isinstance(document.get("spec"), dict):
        patch["spec"] = copy.deepcopy(document["spec"])
    return patch


def upgrade_stored_vault(resource: dict[str, Any]) -> dict[str, Any]:
    upgraded = copy.deepcopy(resource)
    metadata = upgraded.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        upgraded["metadata"] = metadata
    spec = upgraded.setdefault("spec", {})
    if not isinstance(spec, dict):
        spec = {}
        upgraded["spec"] = spec
    if "vaultName" not in spec and isinstance(metadata.get("name"), str):
        spec["vaultName"] = metadata["name"]
    spec.setdefault("updatePolicy", "retain")
    upgraded.setdefault("status", {})
    return upgraded


def validate_vault_resource(
    resource: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
    current_name: str | None,
    errors: list[dict[str, str]],
    stored: dict[str, Any] | None = None,
) -> None:
    resource = upgrade_stored_vault(resource)
    metadata = resource.get("metadata")
    spec = resource.get("spec")
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    name = metadata.get("name")
    validate_name(name, errors)
    mesh_ref = spec.get("meshRef")
    normalize_required_string(mesh_ref, "spec.meshRef", "Mesh reference is required", errors)
    if isinstance(mesh_ref, str) and mesh_ref and mesh_ref not in store["meshes"]:
        errors.append(error("spec.meshRef", f"Mesh {mesh_ref} does not exist", "invalid"))

    vault_name = spec.get("vaultName")
    if not isinstance(vault_name, str) or not vault_name:
        errors.append(error("spec.vaultName", "Vault name must be a non-empty string", "invalid"))

    validate_vault_update_policy(spec.get("updatePolicy"), errors)
    validate_template_exclusivity(spec, errors)

    for field in ("template", "templateRef"):
        if field in spec and spec.get(field) is not None and not isinstance(spec.get(field), str):
            errors.append(error(f"spec.{field}", f"{field} must be a string", "invalid"))

    if stored is not None:
        for field in ("meshRef", "vaultName"):
            if get_path(stored, ["spec", field]) != spec.get(field):
                path = f"spec.{field}"
                errors.append(error(path, f"field '{path}' is immutable after creation", "immutable"))

    for other_name, other in store["vaults"].items():
        if current_name is not None and other_name == current_name:
            continue
        other_spec = other.get("spec") if isinstance(other.get("spec"), dict) else {}
        if other_spec.get("meshRef") == mesh_ref and other_spec.get("vaultName") == vault_name:
            errors.append(
                error(
                    "spec.vaultName",
                    f"Vault identity {mesh_ref}/{vault_name} conflicts with {other_name}",
                    "duplicate",
                )
            )
            break


def validate_vault_update_policy(value: Any, errors: list[dict[str, str]]) -> None:
    if value not in {"retain", "recreate"}:
        errors.append(error("spec.updatePolicy", "Update policy must be retain or recreate", "invalid"))


def validate_template_exclusivity(
    spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if spec.get("template") is not None and spec.get("templateRef") is not None:
        errors.append(error("spec.template", "template and templateRef are mutually exclusive", "invalid"))


def collection_name(kind: str) -> str:
    return ONE_SHOT_COLLECTIONS[kind]


def normalize_one_shot_for_create(
    kind: str,
    document: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    metadata = document.get("metadata")
    spec = document.get("spec")

    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    name = metadata.get("name")
    validate_name(name, errors)

    if kind == "task":
        normalized_spec = normalize_task_spec(spec, store, errors)
    elif kind == "snapshot":
        normalized_spec = normalize_snapshot_spec(spec, store, errors)
    elif kind == "recovery":
        normalized_spec = normalize_recovery_spec(spec, store, errors)
    else:  # pragma: no cover - argparse prevents this path
        normalized_spec = {}

    resource = {
        "metadata": {"name": name},
        "spec": normalized_spec,
        "status": {"state": "Initializing"},
    }
    return resource, errors


def normalize_task_spec(
    spec: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    mesh_ref = spec.get("meshRef")
    normalize_required_string(mesh_ref, "spec.meshRef", "Mesh reference is required", errors)
    if isinstance(mesh_ref, str) and mesh_ref:
        normalized["meshRef"] = mesh_ref
        if mesh_ref not in store["meshes"]:
            errors.append(error("spec.meshRef", f"Mesh {mesh_ref} does not exist", "invalid"))

    inline = spec.get("inline")
    bundle_ref = spec.get("bundleRef")
    inline_set = is_non_empty_string(inline)
    bundle_set = is_non_empty_string(bundle_ref)
    if inline_set == bundle_set:
        errors.append(
            error(
                "spec",
                "exactly one of 'spec.inline' or 'spec.bundleRef' must be set",
                "invalid",
            )
        )
    if "inline" in spec:
        if inline_set:
            normalized["inline"] = inline
        elif inline is not None:
            errors.append(error("spec.inline", "Inline task content must be a non-empty string", "invalid"))
    if "bundleRef" in spec:
        if bundle_set:
            normalized["bundleRef"] = bundle_ref
        elif bundle_ref is not None:
            errors.append(error("spec.bundleRef", "Bundle reference must be a non-empty string", "invalid"))
    return normalized


def normalize_snapshot_spec(
    spec: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    mesh_ref = spec.get("meshRef")
    normalize_required_string(mesh_ref, "spec.meshRef", "Mesh reference is required", errors)
    if isinstance(mesh_ref, str) and mesh_ref:
        normalized["meshRef"] = mesh_ref
        if mesh_ref not in store["meshes"]:
            errors.append(error("spec.meshRef", f"Mesh {mesh_ref} does not exist", "invalid"))

    if "storage" in spec:
        storage = normalize_snapshot_storage(spec.get("storage"), errors)
        if storage is not None:
            normalized["storage"] = storage
    if "scope" in spec:
        scope = normalize_scope(spec.get("scope"), "spec.scope", errors)
        if scope is not None:
            normalized["scope"] = scope
    normalized["resources"] = normalize_one_shot_resources(spec.get("resources"), errors)
    return normalized


def normalize_recovery_spec(
    spec: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    mesh_ref = spec.get("meshRef")
    normalize_required_string(mesh_ref, "spec.meshRef", "Mesh reference is required", errors)
    if isinstance(mesh_ref, str) and mesh_ref:
        normalized["meshRef"] = mesh_ref
        if mesh_ref not in store["meshes"]:
            errors.append(error("spec.meshRef", f"Mesh {mesh_ref} does not exist", "invalid"))

    snapshot_ref = spec.get("snapshotRef")
    normalize_required_string(snapshot_ref, "spec.snapshotRef", "Snapshot reference is required", errors)
    if isinstance(snapshot_ref, str) and snapshot_ref:
        normalized["snapshotRef"] = snapshot_ref
        snapshot = store["snapshots"].get(snapshot_ref)
        if snapshot is None:
            errors.append(error("spec.snapshotRef", f"Snapshot {snapshot_ref} does not exist", "invalid"))
        else:
            snapshot_mesh = get_path(snapshot, ["spec", "meshRef"])
            if isinstance(mesh_ref, str) and snapshot_mesh != mesh_ref:
                errors.append(
                    error(
                        "spec.snapshotRef",
                        f"snapshot '{snapshot_ref}' belongs to mesh '{snapshot_mesh}', not '{mesh_ref}'",
                        "invalid",
                    )
                )

    if "scope" in spec:
        scope = normalize_scope(spec.get("scope"), "spec.scope", errors)
        if scope is not None:
            normalized["scope"] = scope
    normalized["resources"] = normalize_one_shot_resources(spec.get("resources"), errors)
    return normalized


def normalize_snapshot_storage(
    value: Any,
    errors: list[dict[str, str]],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(error("spec.storage", "Storage must be an object", "invalid"))
        return None
    normalized: dict[str, Any] = {}
    if "size" in value:
        size = value.get("size")
        normalized["size"] = size
        if parse_quantity(size, "memory") is None:
            errors.append(error("spec.storage.size", "Storage size is invalid", "invalid"))
    if "className" in value:
        class_name = value.get("className")
        normalized["className"] = class_name
        if not isinstance(class_name, str) or not class_name:
            errors.append(error("spec.storage.className", "Storage className must be a non-empty string", "invalid"))
    return normalized


def normalize_scope(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(error(path, "Scope must be an object", "invalid"))
        return None
    normalized: dict[str, Any] = {}
    for key, items in value.items():
        field = f"{path}.{key}"
        if key not in SCOPE_KEYS:
            errors.append(error(field, "Scope field is not supported", "invalid"))
            continue
        if not isinstance(items, list) or any(not isinstance(item, str) or not item for item in items):
            errors.append(error(field, "Scope values must be non-empty string arrays", "invalid"))
            continue
        normalized[key] = copy.deepcopy(items)
    return normalized


def normalize_one_shot_resources(
    value: Any,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if value is None:
        normalized["memory"] = {"limit": "1Gi", "request": "1Gi"}
        return normalized
    if not isinstance(value, dict):
        errors.append(error("spec.resources", "Resources must be an object", "invalid"))
        normalized["memory"] = {"limit": "1Gi", "request": "1Gi"}
        return normalized

    if "memory" in value:
        memory = normalize_quantity_object(
            value.get("memory"),
            "spec.resources.memory",
            "memory",
            errors,
        )
        if memory is not None:
            normalized["memory"] = memory
    else:
        normalized["memory"] = {"limit": "1Gi", "request": "1Gi"}

    if "cpu" in value:
        cpu = normalize_quantity_object(
            value.get("cpu"),
            "spec.resources.cpu",
            "cpu",
            errors,
        )
        if cpu is not None:
            normalized["cpu"] = cpu
    return normalized


def one_shot_update_patch(document: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if isinstance(document.get("metadata"), dict):
        patch["metadata"] = {"name": document["metadata"].get("name")}
    if isinstance(document.get("spec"), dict):
        patch["spec"] = copy.deepcopy(document["spec"])
    return patch


def upgrade_one_shot(resource: dict[str, Any]) -> dict[str, Any]:
    upgraded = copy.deepcopy(resource)
    metadata = upgraded.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        upgraded["metadata"] = metadata
    spec = upgraded.setdefault("spec", {})
    if not isinstance(spec, dict):
        spec = {}
        upgraded["spec"] = spec
    status = upgraded.setdefault("status", {})
    if not isinstance(status, dict):
        status = {}
        upgraded["status"] = status
    status.setdefault("state", "Initializing")
    return upgraded


def run_task(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    status.pop("detail", None)
    spec = resource.get("spec") if isinstance(resource.get("spec"), dict) else {}
    inline = spec.get("inline")
    if isinstance(inline, str):
        for index, line in enumerate(inline.splitlines(), start=1):
            if line.startswith("FAIL:"):
                reason = line[len("FAIL:") :].strip()
                status["state"] = "Failed"
                status["detail"] = f"command {index} failed: {reason}"
                return
    status["state"] = "Succeeded"


def run_snapshot(
    resource: dict[str, Any],
    meshes: dict[str, dict[str, Any]],
) -> None:
    status = resource.setdefault("status", {})
    status.pop("detail", None)
    status.pop("storageRef", None)
    if referenced_mesh_stable(resource, meshes):
        name = get_path(resource, ["metadata", "name"])
        status["state"] = "Succeeded"
        status["storageRef"] = f"snapshot://{name}"
    else:
        status["state"] = "Unknown"
        status["detail"] = "referenced mesh is not stable"


def run_recovery(
    resource: dict[str, Any],
    meshes: dict[str, dict[str, Any]],
) -> None:
    status = resource.setdefault("status", {})
    status.pop("detail", None)
    if referenced_mesh_stable(resource, meshes):
        status["state"] = "Succeeded"
    else:
        status["state"] = "Unknown"
        status["detail"] = "referenced mesh is not stable"


def referenced_mesh_stable(
    resource: dict[str, Any],
    meshes: dict[str, dict[str, Any]],
) -> bool:
    mesh_ref = get_path(resource, ["spec", "meshRef"])
    parent = meshes.get(mesh_ref) if isinstance(mesh_ref, str) else None
    if not isinstance(parent, dict):
        return False
    return public_resource(upgrade_stored_resource(parent))["status"].get("stable") is True


def one_shot_summary(kind: str, name: str, resource: dict[str, Any]) -> dict[str, Any]:
    public = public_one_shot(kind, resource)
    summary: dict[str, Any] = {
        "name": name,
        "meshRef": public.get("spec", {}).get("meshRef"),
        "status": {"state": public["status"]["state"]},
    }
    if kind == "recovery":
        summary["snapshotRef"] = public.get("spec", {}).get("snapshotRef")
    if kind == "snapshot" and "storageRef" in public["status"]:
        summary["storageRef"] = public["status"]["storageRef"]
    return summary


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def update_patch(document: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if isinstance(document.get("metadata"), dict):
        patch["metadata"] = {"name": document["metadata"].get("name")}
    if isinstance(document.get("spec"), dict):
        patch["spec"] = copy.deepcopy(document["spec"])
    return patch


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def upgrade_stored_resource(resource: dict[str, Any]) -> dict[str, Any]:
    upgraded = copy.deepcopy(resource)
    spec = upgraded.setdefault("spec", {})
    if not isinstance(spec, dict):
        spec = {}
        upgraded["spec"] = spec

    if "instances" not in spec:
        spec["instances"] = 1
    if "resources" not in spec:
        spec["resources"] = {"memory": {"limit": "1Gi", "request": "1Gi"}}
    spec["access"] = defaulted_access(spec.get("access"))
    if "migration" not in spec:
        spec["migration"] = {"strategy": "FullStop"}
    if "network" not in spec or not isinstance(spec.get("network"), dict):
        spec["network"] = {}
    network = spec["network"]
    if "storage" not in network or not isinstance(network.get("storage"), dict):
        network["storage"] = {}
    storage = network["storage"]
    storage.setdefault("size", "1Gi")
    storage.setdefault("ephemeral", False)
    if "replicationFactor" not in network:
        network["replicationFactor"] = computed_replication_factor(spec.get("instances"))
    if "management" not in spec or not isinstance(spec.get("management"), dict):
        spec["management"] = {}
    spec["management"].setdefault("enabled", False)

    if "status" not in upgraded or not isinstance(upgraded.get("status"), dict):
        upgraded["status"] = {}
    initialize_status(upgraded)
    return upgraded


def validate_name(name: Any, errors: list[dict[str, str]]) -> None:
    if name is None or name == "":
        errors.append(error("metadata.name", "Name is required", "required"))
        return
    if not isinstance(name, str) or len(name) < 2 or not NAME_RE.fullmatch(name):
        errors.append(error("metadata.name", "Name format is invalid", "invalid"))


def normalize_instances(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
    default: int | None = None,
) -> None:
    if "instances" not in spec and default is None:
        return
    instances = spec.get("instances", default)
    normalized_spec["instances"] = instances
    validate_instances(instances, errors)


def validate_instances(instances: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(instances, int) or isinstance(instances, bool) or instances < 0:
        errors.append(
            error("spec.instances", "Instances must be a non-negative integer", "invalid")
        )


def normalize_runtime(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if "runtime" not in spec:
        return
    runtime = spec.get("runtime")
    normalized_spec["runtime"] = runtime


def validate_runtime(runtime: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(runtime, str) or not RUNTIME_RE.fullmatch(runtime):
        errors.append(error("spec.runtime", "Runtime must be major.minor.patch", "invalid"))
        return
    status = runtime_catalog_status(runtime)
    if status == "skipped":
        errors.append(
            error(
                "spec.runtime",
                f"runtime version '{runtime}' is skipped and cannot be targeted",
                "invalid",
            )
        )
    elif status is None:
        errors.append(error("spec.runtime", "Runtime version is not supported", "invalid"))


def runtime_catalog_status(runtime: Any) -> str | None:
    if not isinstance(runtime, str):
        return None
    return RUNTIME_CATALOG.get(runtime)


def parse_runtime_version(runtime: Any) -> tuple[int, int, int] | None:
    if not isinstance(runtime, str):
        return None
    match = RUNTIME_RE.fullmatch(runtime)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def compare_runtime_versions(left: Any, right: Any) -> int | None:
    left_version = parse_runtime_version(left)
    right_version = parse_runtime_version(right)
    if left_version is None or right_version is None:
        return None
    return (left_version > right_version) - (left_version < right_version)


def collect_runtime_warnings(resource: dict[str, Any]) -> list[dict[str, str]]:
    runtime = get_path(resource, ["spec", "runtime"])
    if runtime_catalog_status(runtime) != "deprecated":
        return []
    return [
        {
            "field": "spec.runtime",
            "message": f"runtime version '{runtime}' is deprecated",
        }
    ]


def with_warnings(
    payload: dict[str, Any],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    if not warnings:
        return payload
    output = copy.deepcopy(payload)
    output["warnings"] = sorted(warnings, key=lambda item: (item["field"], item["message"]))
    return output


def normalize_resources(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    resources = spec.get("resources")
    if resources is None:
        normalized_spec["resources"] = {
            "memory": {"limit": "1Gi", "request": "1Gi"}
        }
        return
    if not isinstance(resources, dict):
        normalized_spec["resources"] = {
            "memory": {"limit": "1Gi", "request": "1Gi"}
        }
        errors.append(error("spec.resources", "Resources must be an object", "invalid"))
        return

    normalized_resources: dict[str, Any] = {}
    if "memory" in resources:
        memory = normalize_quantity_object(
            resources.get("memory"),
            "spec.resources.memory",
            "memory",
            errors,
        )
        if memory is not None:
            normalized_resources["memory"] = memory
    else:
        normalized_resources["memory"] = {"limit": "1Gi", "request": "1Gi"}

    if "cpu" in resources:
        cpu = normalize_quantity_object(
            resources.get("cpu"),
            "spec.resources.cpu",
            "cpu",
            errors,
        )
        if cpu is not None:
            normalized_resources["cpu"] = cpu

    normalized_spec["resources"] = normalized_resources


def normalize_quantity_object(
    value: Any,
    path: str,
    kind: str,
    errors: list[dict[str, str]],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(error(path, f"{kind.capitalize()} resource must be an object", "invalid"))
        return None

    limit = value.get("limit")
    if limit is None:
        errors.append(error(f"{path}.limit", f"{kind.capitalize()} limit is required", "required"))
        return None

    request = value.get("request", limit)
    normalized = {"limit": limit, "request": request}
    validate_quantity_pair(limit, request, path, kind, errors)
    return normalized


def validate_quantity_pair(
    limit: Any,
    request: Any,
    path: str,
    kind: str,
    errors: list[dict[str, str]],
) -> None:
    limit_units = parse_quantity(limit, kind)
    request_units = parse_quantity(request, kind)

    if limit_units is None:
        errors.append(error(f"{path}.limit", f"{kind.capitalize()} limit is invalid", "invalid"))
    if request_units is None:
        errors.append(error(f"{path}.request", f"{kind.capitalize()} request is invalid", "invalid"))
    if (
        limit_units is not None
        and request_units is not None
        and request_units > limit_units
    ):
        errors.append(
            error(f"{path}.request", f"{kind.capitalize()} request exceeds limit", "invalid")
        )


def parse_quantity(value: Any, kind: str) -> int | None:
    if isinstance(value, bool):
        return None
    text = str(value) if isinstance(value, int) else value
    if not isinstance(text, str):
        return None
    if kind == "memory":
        match = MEMORY_RE.fullmatch(text)
        if not match:
            return None
        amount, unit = match.groups()
        return int(amount) * MEMORY_UNITS[unit]
    match = CPU_RE.fullmatch(text)
    if not match:
        return None
    amount, milli_suffix = match.groups()
    return int(amount) if milli_suffix else int(amount) * 1000


def normalize_access(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    access = spec.get("access")
    if access is not None and not isinstance(access, dict):
        errors.append(error("spec.access", "Access must be an object", "invalid"))
        access = None
    if isinstance(access, dict):
        for field, label in (
            ("authentication", "Authentication"),
            ("permissions", "Permissions"),
            ("encryption", "Encryption"),
        ):
            if field in access and access.get(field) is not None and not isinstance(access.get(field), dict):
                errors.append(
                    error(f"spec.access.{field}", f"{label} must be an object", "invalid")
                )
    normalized_spec["access"] = defaulted_access(access)


def defaulted_access(value: Any) -> dict[str, Any]:
    access = value if isinstance(value, dict) else {}
    authentication = access.get("authentication")
    if not isinstance(authentication, dict):
        authentication = {}

    enabled = authentication.get("enabled", True)
    normalized_authentication: dict[str, Any] = {"enabled": enabled}
    if "digestAlgorithm" in authentication or enabled is not False:
        normalized_authentication["digestAlgorithm"] = authentication.get(
            "digestAlgorithm",
            "SHA-256",
        )

    normalized: dict[str, Any] = {"authentication": normalized_authentication}
    if "credentialRef" in access:
        normalized["credentialRef"] = access.get("credentialRef")

    permissions = access.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
    normalized_permissions: dict[str, Any] = {
        "enabled": permissions.get("enabled", False)
    }
    if "roles" in permissions:
        normalized_permissions["roles"] = copy.deepcopy(permissions.get("roles"))
    normalized["permissions"] = normalized_permissions

    encryption = access.get("encryption")
    if not isinstance(encryption, dict):
        encryption = {}
    normalized_encryption: dict[str, Any] = {
        "source": encryption.get("source", "None"),
        "clientMode": encryption.get("clientMode", "None"),
    }
    for field in ("certRef", "certServiceRef"):
        if field in encryption:
            normalized_encryption[field] = encryption.get(field)
    normalized["encryption"] = normalized_encryption
    return normalized


def canonicalize_resource_access(resource: dict[str, Any]) -> None:
    spec = resource.setdefault("spec", {})
    if not isinstance(spec, dict):
        return
    spec["access"] = canonical_access(spec.get("access"))


def canonical_access(value: Any) -> dict[str, Any]:
    access = defaulted_access(value)

    authentication = access["authentication"]
    if authentication.get("enabled") is False:
        access["authentication"] = {"enabled": False}
        access.pop("credentialRef", None)
    else:
        if authentication.get("digestAlgorithm") is None:
            authentication["digestAlgorithm"] = "SHA-256"
        if access.get("credentialRef") is None:
            access.pop("credentialRef", None)

    permissions = access["permissions"]
    if permissions.get("enabled") is True:
        if "roles" in permissions:
            permissions["roles"] = copy.deepcopy(permissions["roles"])
    else:
        access["permissions"] = {"enabled": permissions.get("enabled", False)}

    encryption = access["encryption"]
    source = encryption.get("source", "None")
    canonical_encryption = {
        "source": source,
        "clientMode": encryption.get("clientMode", "None"),
    }
    if source == "Secret" and encryption.get("certRef") is not None:
        canonical_encryption["certRef"] = encryption.get("certRef")
    if source == "Service" and encryption.get("certServiceRef") is not None:
        canonical_encryption["certServiceRef"] = encryption.get("certServiceRef")
    access["encryption"] = canonical_encryption
    return access


def normalize_migration(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    strategy = "FullStop"
    migration = spec.get("migration")
    if isinstance(migration, dict) and "strategy" in migration:
        strategy = migration.get("strategy")
    normalized_spec["migration"] = {"strategy": strategy}


def validate_migration_strategy(strategy: Any, errors: list[dict[str, str]]) -> None:
    if strategy not in MIGRATION_STRATEGIES:
        errors.append(
            error(
                "spec.migration.strategy",
                "Migration strategy must be FullStop, LiveMigration, or RollingPatch",
                "invalid",
            )
        )


def normalize_network(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
    apply_defaults: bool,
) -> None:
    network = spec.get("network")
    if network is None:
        network = {}
    if not isinstance(network, dict):
        errors.append(error("spec.network", "Network must be an object", "invalid"))
        network = {}

    normalized_network: dict[str, Any] = {}
    normalize_storage(network, normalized_network, errors, apply_defaults)
    normalize_replication_factor(
        network,
        normalized_network,
        normalized_spec.get("instances"),
        errors,
        apply_defaults,
    )
    if normalized_network or apply_defaults:
        normalized_spec["network"] = normalized_network


def normalize_storage(
    network: dict[str, Any],
    normalized_network: dict[str, Any],
    errors: list[dict[str, str]],
    apply_defaults: bool,
) -> None:
    storage = network.get("storage")
    if storage is None:
        storage = {}
    if not isinstance(storage, dict):
        errors.append(error("spec.network.storage", "Storage must be an object", "invalid"))
        storage = {}

    normalized_storage: dict[str, Any] = {}
    if "size" in storage or apply_defaults:
        size = storage.get("size", "1Gi")
        normalized_storage["size"] = size
        if parse_quantity(size, "memory") is None:
            errors.append(error("spec.network.storage.size", "Storage size is invalid", "invalid"))
    if "ephemeral" in storage or apply_defaults:
        ephemeral = storage.get("ephemeral", False)
        normalized_storage["ephemeral"] = ephemeral
        if not isinstance(ephemeral, bool):
            errors.append(
                error("spec.network.storage.ephemeral", "Storage ephemeral must be boolean", "invalid")
            )
    if "className" in storage:
        class_name = storage.get("className")
        normalized_storage["className"] = class_name
        if not isinstance(class_name, str):
            errors.append(
                error("spec.network.storage.className", "Storage className must be string", "invalid")
            )
    if normalized_storage or apply_defaults:
        normalized_network["storage"] = normalized_storage


def normalize_replication_factor(
    network: dict[str, Any],
    normalized_network: dict[str, Any],
    instances: Any,
    errors: list[dict[str, str]],
    apply_defaults: bool,
) -> None:
    if "replicationFactor" in network or apply_defaults:
        replication_factor = network.get(
            "replicationFactor",
            computed_replication_factor(instances),
        )
        normalized_network["replicationFactor"] = replication_factor
        validate_replication_factor(replication_factor, instances, errors)


def computed_replication_factor(instances: Any) -> int:
    if isinstance(instances, int) and not isinstance(instances, bool) and instances > 0:
        return min(instances, 3)
    return 1


def normalize_exposure(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if "exposure" not in spec:
        return
    exposure = spec.get("exposure")
    if not isinstance(exposure, dict):
        errors.append(error("spec.exposure", "Exposure must be an object", "invalid"))
        return

    normalized_exposure: dict[str, Any] = {}
    exposure_type = exposure.get("type")
    if exposure_type is not None:
        normalized_exposure["type"] = exposure_type

    for field in ("hostname", "port", "directPort"):
        if field in exposure:
            normalized_exposure[field] = copy.deepcopy(exposure.get(field))
    if "annotations" in exposure:
        normalized_exposure["annotations"] = copy.deepcopy(exposure.get("annotations"))

    normalized_spec["exposure"] = normalized_exposure


def normalize_management(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
    apply_defaults: bool,
) -> None:
    management = spec.get("management")
    if management is None:
        if apply_defaults:
            normalized_spec["management"] = {"enabled": False}
        return
    if not isinstance(management, dict):
        errors.append(error("spec.management", "Management must be an object", "invalid"))
        if apply_defaults:
            normalized_spec["management"] = {"enabled": False}
        return
    if "enabled" in management or apply_defaults:
        normalized_spec["management"] = {"enabled": management.get("enabled", False)}


def validate_merged_resource(
    resource: dict[str, Any],
    stored: dict[str, Any] | None,
    errors: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    if errors is None:
        errors = []

    metadata = resource.get("metadata")
    spec = resource.get("spec")
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    validate_name(metadata.get("name"), errors)
    validate_forbidden_autoscaling(spec, "spec", errors)

    if "instances" in spec:
        validate_instances(spec.get("instances"), errors)
    if "runtime" in spec:
        validate_runtime(spec.get("runtime"), errors)
    validate_resources_object(spec.get("resources"), errors)
    validate_access_object(spec.get("access"), errors)
    validate_migration_object(spec.get("migration"), errors)
    validate_network_object(spec.get("network"), spec.get("instances"), errors)
    validate_exposure_object(spec.get("exposure"), errors)
    validate_management_object(spec.get("management"), errors)

    if stored is not None:
        validate_active_migration_updates(resource, stored, errors)
        validate_runtime_change(resource, stored, errors)
        stored_size = get_path(stored, ["spec", "network", "storage", "size"])
        candidate_size = get_path(resource, ["spec", "network", "storage", "size"])
        if stored_size != candidate_size:
            field = "spec.network.storage.size"
            errors.append(error(field, f"field '{field}' is immutable after creation", "immutable"))
        stored_management = get_path(stored, ["spec", "management", "enabled"])
        candidate_management = get_path(resource, ["spec", "management", "enabled"])
        if stored_management != candidate_management:
            field = "spec.management.enabled"
            errors.append(error(field, f"field '{field}' is immutable after creation", "immutable"))

    return errors


def validate_active_migration_updates(
    resource: dict[str, Any],
    stored: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if not has_active_migration(stored):
        return
    stored_runtime = get_path(stored, ["spec", "runtime"])
    candidate_runtime = get_path(resource, ["spec", "runtime"])
    if stored_runtime != candidate_runtime:
        errors.append(
            error(
                "spec.runtime",
                "cannot change runtime version while a migration is in progress",
                "invalid",
            )
        )

    stored_strategy = migration_strategy(stored)
    candidate_strategy = migration_strategy(resource)
    if stored_strategy != candidate_strategy:
        errors.append(
            error(
                "spec.migration.strategy",
                "cannot change migration strategy while a migration is in progress",
                "invalid",
            )
        )


def validate_runtime_change(
    resource: dict[str, Any],
    stored: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if has_active_migration(stored):
        return
    current = get_path(stored, ["spec", "runtime"])
    target = get_path(resource, ["spec", "runtime"])
    if current == target or not isinstance(target, str):
        return
    if current is None:
        return
    if runtime_catalog_status(current) is None or runtime_catalog_status(target) is None:
        return

    comparison = compare_runtime_versions(current, target)
    if comparison is None:
        return
    if comparison > 0:
        errors.append(
            error(
                "spec.runtime",
                f"version downgrade from '{current}' to '{target}' is not allowed",
                "invalid",
            )
        )
        return

    strategy = migration_strategy(resource)
    current_version = parse_runtime_version(current)
    target_version = parse_runtime_version(target)
    if strategy == "RollingPatch" and current_version is not None and target_version is not None:
        if current_version[:2] != target_version[:2]:
            errors.append(
                error(
                    "spec.runtime",
                    "RollingPatch requires source and target runtime to share major and minor versions",
                    "invalid",
                )
            )
        if target_version[0] < 4:
            errors.append(
                error(
                    "spec.runtime",
                    "RollingPatch requires target runtime major version to be at least 4",
                    "invalid",
                )
            )
    if strategy == "LiveMigration" and is_regions_configured(get_path(resource, ["spec", "regions"])):
        errors.append(
            error(
                "spec.migration.strategy",
                "LiveMigration strategy is not supported with multi-region topology",
                "invalid",
            )
        )


def is_runtime_version_change(stored: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if has_active_migration(stored):
        return False
    current = get_path(stored, ["spec", "runtime"])
    target = get_path(candidate, ["spec", "runtime"])
    if current is None or current == target:
        return False
    return runtime_catalog_status(current) is not None and runtime_catalog_status(target) is not None


def is_regions_configured(regions: Any) -> bool:
    if regions is None:
        return False
    if isinstance(regions, list):
        return len(regions) > 0
    if isinstance(regions, dict):
        return len(regions) > 0
    return True


def migration_strategy(resource: dict[str, Any]) -> Any:
    strategy = get_path(resource, ["spec", "migration", "strategy"])
    return strategy if strategy is not None else "FullStop"


def validate_resources_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.resources", "Resources must be an object", "invalid"))
        return
    for name, kind in (("memory", "memory"), ("cpu", "cpu")):
        if name not in value:
            continue
        child = value.get(name)
        if not isinstance(child, dict):
            errors.append(error(f"spec.resources.{name}", f"{name.capitalize()} resource must be an object", "invalid"))
            continue
        limit = child.get("limit")
        if limit is None:
            errors.append(error(f"spec.resources.{name}.limit", f"{name.capitalize()} limit is required", "required"))
            continue
        validate_quantity_pair(
            limit,
            child.get("request", limit),
            f"spec.resources.{name}",
            kind,
            errors,
        )
        child.setdefault("request", limit)


def validate_access_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.access", "Access must be an object", "invalid"))
        return
    validate_access_authentication(value, errors)
    validate_access_permissions(value, errors)
    validate_access_encryption(value, errors)


def validate_access_authentication(
    access: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    authentication = access.get("authentication")
    if authentication is None:
        authentication = {}
    if not isinstance(authentication, dict):
        errors.append(
            error("spec.access.authentication", "Authentication must be an object", "invalid")
        )
        return

    enabled = authentication.get("enabled", True)
    if not isinstance(enabled, bool):
        errors.append(
            error("spec.access.authentication.enabled", "Authentication enabled must be boolean", "invalid")
        )

    digest_algorithm = authentication.get("digestAlgorithm")
    if enabled is False:
        if digest_algorithm is not None:
            errors.append(
                error(
                    "spec.access.authentication.digestAlgorithm",
                    "Digest algorithm is forbidden when authentication is disabled",
                    "forbidden",
                )
            )
        if access.get("credentialRef") is not None:
            errors.append(
                error(
                    "spec.access.credentialRef",
                    "Credential reference is forbidden when authentication is disabled",
                    "forbidden",
                )
            )
        return

    if digest_algorithm not in AUTH_DIGEST_ALGORITHMS:
        errors.append(
            error(
                "spec.access.authentication.digestAlgorithm",
                "Digest algorithm must be SHA-256, SHA-384, or SHA-512",
                "invalid",
            )
        )


def validate_access_permissions(
    access: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    permissions = access.get("permissions")
    if permissions is None:
        return
    if not isinstance(permissions, dict):
        errors.append(error("spec.access.permissions", "Permissions must be an object", "invalid"))
        return

    enabled = permissions.get("enabled", False)
    if not isinstance(enabled, bool):
        errors.append(
            error("spec.access.permissions.enabled", "Permissions enabled must be boolean", "invalid")
        )
        return
    if enabled is not True:
        return

    roles = permissions.get("roles")
    if roles is None or roles == []:
        errors.append(error("spec.access.permissions.roles", "Permission roles are required", "required"))
        return
    if not isinstance(roles, list):
        errors.append(error("spec.access.permissions.roles", "Permission roles must be an array", "invalid"))
        return

    seen_names: set[str] = set()
    duplicate_found = False
    for index, role in enumerate(roles):
        if not isinstance(role, dict):
            errors.append(
                error(
                    f"spec.access.permissions.roles[{index}].name",
                    "Role name is required",
                    "required",
                )
            )
            errors.append(
                error(
                    f"spec.access.permissions.roles[{index}].permissions",
                    "Role permissions are required",
                    "required",
                )
            )
            continue

        name = role.get("name")
        if not isinstance(name, str) or not name:
            errors.append(
                error(
                    f"spec.access.permissions.roles[{index}].name",
                    "Role name is required",
                    "required",
                )
            )
        elif name in seen_names:
            duplicate_found = True
        else:
            seen_names.add(name)

        role_permissions = role.get("permissions")
        if not isinstance(role_permissions, list) or not role_permissions:
            errors.append(
                error(
                    f"spec.access.permissions.roles[{index}].permissions",
                    "Role permissions are required",
                    "required",
                )
            )
        elif any(not isinstance(permission, str) or not permission for permission in role_permissions):
            errors.append(
                error(
                    f"spec.access.permissions.roles[{index}].permissions",
                    "Role permissions must be non-empty strings",
                    "invalid",
                )
            )

    if duplicate_found:
        errors.append(
            error("spec.access.permissions.roles", "Role names must be unique", "duplicate")
        )


def validate_access_encryption(
    access: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    encryption = access.get("encryption")
    if encryption is None:
        return
    if not isinstance(encryption, dict):
        errors.append(error("spec.access.encryption", "Encryption must be an object", "invalid"))
        return

    source = encryption.get("source", "None")
    client_mode = encryption.get("clientMode", "None")
    if source not in ENCRYPTION_SOURCES:
        errors.append(
            error("spec.access.encryption.source", "Encryption source is invalid", "invalid")
        )
    if client_mode not in ENCRYPTION_CLIENT_MODES:
        errors.append(
            error("spec.access.encryption.clientMode", "Encryption client mode is invalid", "invalid")
        )

    cert_ref = encryption.get("certRef")
    cert_service_ref = encryption.get("certServiceRef")
    if source == "None":
        if cert_ref is not None:
            errors.append(
                error("spec.access.encryption.certRef", "Certificate reference is forbidden", "forbidden")
            )
        if cert_service_ref is not None:
            errors.append(
                error(
                    "spec.access.encryption.certServiceRef",
                    "Certificate service reference is forbidden",
                    "forbidden",
                )
            )
        if client_mode in {"Authenticate", "Validate"}:
            errors.append(
                error(
                    "spec.access.encryption.clientMode",
                    "Encryption client mode requires an encryption source",
                    "invalid",
                )
            )
    elif source == "Secret":
        if cert_ref is None or cert_ref == "":
            errors.append(
                error("spec.access.encryption.certRef", "Certificate reference is required", "required")
            )
        if cert_service_ref is not None:
            errors.append(
                error(
                    "spec.access.encryption.certServiceRef",
                    "Certificate service reference is forbidden",
                    "forbidden",
                )
            )
    elif source == "Service":
        if cert_service_ref is None or cert_service_ref == "":
            errors.append(
                error(
                    "spec.access.encryption.certServiceRef",
                    "Certificate service reference is required",
                    "required",
                )
            )
        if cert_ref is not None:
            errors.append(
                error("spec.access.encryption.certRef", "Certificate reference is forbidden", "forbidden")
            )


def validate_migration_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.migration", "Migration must be an object", "invalid"))
        return
    if "strategy" in value:
        validate_migration_strategy(value.get("strategy"), errors)


def validate_network_object(
    value: Any,
    instances: Any,
    errors: list[dict[str, str]],
) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.network", "Network must be an object", "invalid"))
        return

    storage = value.get("storage")
    if storage is not None:
        if not isinstance(storage, dict):
            errors.append(error("spec.network.storage", "Storage must be an object", "invalid"))
        else:
            if "size" in storage and parse_quantity(storage.get("size"), "memory") is None:
                errors.append(error("spec.network.storage.size", "Storage size is invalid", "invalid"))
            if "ephemeral" in storage and not isinstance(storage.get("ephemeral"), bool):
                errors.append(
                    error("spec.network.storage.ephemeral", "Storage ephemeral must be boolean", "invalid")
                )
            if "className" in storage and not isinstance(storage.get("className"), str):
                errors.append(
                    error("spec.network.storage.className", "Storage className must be string", "invalid")
                )

    if "replicationFactor" in value:
        validate_replication_factor(value.get("replicationFactor"), instances, errors)


def validate_exposure_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.exposure", "Exposure must be an object", "invalid"))
        return

    exposure_type = value.get("type")
    if exposure_type is None or exposure_type == "":
        errors.append(error("spec.exposure.type", "Exposure type is required", "required"))
    elif exposure_type not in EXPOSURE_TYPES:
        errors.append(error("spec.exposure.type", "Exposure type is invalid", "invalid"))

    validate_exposure_field_types(value, errors)
    validate_exposure_allowed_fields(value, exposure_type, errors)


def validate_exposure_field_types(
    exposure: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    hostname = exposure.get("hostname")
    if "hostname" in exposure and not isinstance(hostname, str):
        errors.append(error("spec.exposure.hostname", "Exposure hostname must be a string", "invalid"))

    for field in ("port", "directPort"):
        value = exposure.get(field)
        if field in exposure and (not isinstance(value, int) or isinstance(value, bool)):
            errors.append(error(f"spec.exposure.{field}", f"Exposure {field} must be an integer", "invalid"))

    annotations = exposure.get("annotations")
    if "annotations" in exposure:
        if not isinstance(annotations, dict) or any(
            not isinstance(key, str) or not isinstance(child, str)
            for key, child in annotations.items()
        ):
            errors.append(
                error("spec.exposure.annotations", "Exposure annotations must be a string map", "invalid")
            )


def validate_exposure_allowed_fields(
    exposure: dict[str, Any],
    exposure_type: Any,
    errors: list[dict[str, str]],
) -> None:
    allowed = {
        "Gateway": {"type", "hostname", "annotations"},
        "DirectPort": {"type", "port", "directPort"},
        "Balancer": {"type", "port"},
    }.get(exposure_type)
    if allowed is None:
        return
    for field in sorted(exposure):
        if field not in allowed:
            errors.append(
                error(
                    f"spec.exposure.{field}",
                    f"Field {field} is forbidden for {exposure_type} exposure",
                    "forbidden",
                )
            )


def validate_management_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.management", "Management must be an object", "invalid"))
        return
    if "enabled" in value and not isinstance(value.get("enabled"), bool):
        errors.append(error("spec.management.enabled", "Management enabled must be boolean", "invalid"))


def validate_replication_factor(
    replication_factor: Any,
    instances: Any,
    errors: list[dict[str, str]],
) -> None:
    field = "spec.network.replicationFactor"
    if (
        not isinstance(replication_factor, int)
        or isinstance(replication_factor, bool)
        or replication_factor < 1
    ):
        errors.append(error(field, "Replication factor must be at least 1", "invalid"))
        return
    if isinstance(instances, int) and not isinstance(instances, bool) and instances > 0:
        if replication_factor > instances:
            errors.append(
                error(
                    field,
                    f"Replication factor {replication_factor} exceeds instance limit {instances}",
                    "invalid",
                )
            )


def initialize_status(resource: dict[str, Any]) -> None:
    spec = resource.setdefault("spec", {})
    status = resource.setdefault("status", {})
    instances = spec.get("instances", 1)
    running = isinstance(instances, int) and not isinstance(instances, bool) and instances > 0

    status["state"] = "Running" if running else "Stopped"
    if "instances" not in status or not isinstance(status.get("instances"), dict):
        status["instances"] = {}
    status_instances = status["instances"]
    if running:
        status_instances.setdefault("ready", instances)
        status_instances.setdefault("starting", 0)
        status_instances.setdefault("stopped", 0)
        status.pop("desiredInstancesOnResume", None)
    else:
        desired = status.get("desiredInstancesOnResume", 0)
        status_instances.setdefault("ready", 0)
        status_instances.setdefault("starting", 0)
        status_instances.setdefault("stopped", desired)
        if "desiredInstancesOnResume" in status:
            status["desiredInstancesOnResume"] = desired
    set_condition(status, "Healthy", "True", "")
    set_condition(status, "PrechecksPassed", "True", "")
    finalize_mesh_status(resource)


def reconcile_update_status(
    stored: dict[str, Any],
    candidate: dict[str, Any],
    resume_without_count: bool,
) -> None:
    status = candidate.setdefault("status", {})
    old_instances = stored.get("spec", {}).get("instances")
    new_instances = candidate.get("spec", {}).get("instances")
    old_status = stored.get("status", {})
    was_stopped = (
        old_instances == 0
        and has_condition(old_status, "GracefulShutdown")
        and "desiredInstancesOnResume" in old_status
    )

    status.pop("desiredInstancesOnResume", None)
    candidate.pop("_transition", None)
    set_condition(status, "Healthy", "True", "")
    set_condition(status, "PrechecksPassed", "True", "")
    clear_condition(status, "Scaling")

    if was_stopped and (resume_without_count or (is_positive_int(new_instances))):
        target = new_instances if is_positive_int(new_instances) else old_status["desiredInstancesOnResume"]
        candidate.setdefault("spec", {})["instances"] = target
        status["state"] = "Running"
        status["stable"] = False
        status["instances"] = {"ready": 0, "starting": target, "stopped": 0}
        clear_condition(status, "GracefulShutdown")
        candidate["_transition"] = {"type": "resume", "target": target}
    elif is_positive_int(old_instances) and new_instances == 0:
        status["state"] = "Stopped"
        status["stable"] = True
        status["desiredInstancesOnResume"] = old_instances
        status["instances"] = {"ready": 0, "starting": 0, "stopped": old_instances}
        set_condition(status, "GracefulShutdown", "True", "")
    elif is_positive_int(old_instances) and is_positive_int(new_instances) and new_instances > old_instances:
        status["state"] = "Running"
        status["stable"] = False
        status["instances"] = {
            "ready": old_instances,
            "starting": new_instances - old_instances,
            "stopped": 0,
        }
        set_condition(status, "Scaling", "True", f"Scaling from {old_instances} to {new_instances}")
        candidate["_transition"] = {"type": "scale", "target": new_instances}
    elif is_positive_int(old_instances) and is_positive_int(new_instances) and new_instances < old_instances:
        status["state"] = "Running"
        status["stable"] = False
        status["instances"] = {"ready": new_instances, "starting": 0, "stopped": 0}
        set_condition(status, "Scaling", "True", f"Scaling from {old_instances} to {new_instances}")
        candidate["_transition"] = {"type": "scale", "target": new_instances}
    else:
        status["state"] = "Running" if is_positive_int(new_instances) else "Stopped"
        status["stable"] = True
        if is_positive_int(new_instances):
            status["instances"] = {"ready": new_instances, "starting": 0, "stopped": 0}
            clear_condition(status, "GracefulShutdown")
        else:
            stopped = old_status.get("desiredInstancesOnResume", 0)
            status["instances"] = {"ready": 0, "starting": 0, "stopped": stopped}
            if has_condition(old_status, "GracefulShutdown"):
                status["desiredInstancesOnResume"] = stopped
                set_condition(status, "GracefulShutdown", "True", "")

    finalize_mesh_status(candidate)


def complete_pending_transition(resource: dict[str, Any]) -> bool:
    transition = resource.pop("_transition", None)
    initialize_status(resource)
    if not isinstance(transition, dict):
        finalize_mesh_status(resource)
        return False

    target = transition.get("target")
    if not is_non_negative_int(target):
        finalize_mesh_status(resource)
        return True

    status = resource.setdefault("status", {})
    status["state"] = "Running" if target > 0 else "Stopped"
    if target > 0:
        status["instances"] = {"ready": target, "starting": 0, "stopped": 0}
        clear_condition(status, "Scaling")
        clear_condition(status, "GracefulShutdown")
        status.pop("desiredInstancesOnResume", None)
    else:
        status["instances"] = {"ready": 0, "starting": 0, "stopped": 0}
    finalize_mesh_status(resource)
    return True


def start_migration(stored: dict[str, Any], candidate: dict[str, Any]) -> None:
    status = candidate.setdefault("status", {})
    strategy = migration_strategy(candidate)
    stages = MIGRATION_STAGES.get(strategy, MIGRATION_STAGES["FullStop"])
    status["migration"] = {
        "sourceRuntime": get_path(stored, ["spec", "runtime"]),
        "targetRuntime": get_path(candidate, ["spec", "runtime"]),
        "stage": stages[0],
    }
    set_condition(status, "Migration", "True", "")
    finalize_mesh_status(candidate)


def advance_migration(resource: dict[str, Any]) -> None:
    migration = resource.setdefault("status", {}).get("migration")
    if not isinstance(migration, dict):
        return
    strategy = migration_strategy(resource)
    stages = MIGRATION_STAGES.get(strategy, MIGRATION_STAGES["FullStop"])
    stage = migration.get("stage")
    if stage not in stages or stage == stages[-1]:
        complete_migration(resource)
        return
    migration["stage"] = stages[stages.index(stage) + 1]


def rollback_migration(resource: dict[str, Any]) -> list[dict[str, str]]:
    if migration_strategy(resource) != "LiveMigration":
        return [
            error(
                "status.migration",
                "rollback is supported only for LiveMigration migrations",
                "invalid",
            )
        ]
    migration = resource.get("status", {}).get("migration")
    if isinstance(migration, dict):
        source_runtime = migration.get("sourceRuntime")
        if isinstance(source_runtime, str):
            resource.setdefault("spec", {})["runtime"] = source_runtime
    complete_migration(resource)
    return []


def complete_migration(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    status.pop("migration", None)
    clear_condition(status, "Migration")
    finalize_mesh_status(resource)


def finalize_mesh_status(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    sort_conditions(status)
    status["stable"] = is_mesh_stable(status, resource)


def is_mesh_stable(status: dict[str, Any], resource: dict[str, Any]) -> bool:
    if "_transition" in resource:
        return False
    if condition_status(status, "Healthy") != "True":
        return False
    if condition_status(status, "PrechecksPassed") != "True":
        return False
    for condition_type in ("GracefulShutdown", "Scaling", "Migration"):
        if condition_status(status, condition_type) == "True":
            return False
    return True


def should_resume_without_count(
    stored: dict[str, Any],
    document: dict[str, Any],
) -> bool:
    status = stored.get("status", {})
    if stored.get("spec", {}).get("instances") != 0:
        return False
    if not has_condition(status, "GracefulShutdown"):
        return False
    if "desiredInstancesOnResume" not in status:
        return False
    spec = document.get("spec")
    if not isinstance(spec, dict):
        return True
    return "instances" not in spec or spec.get("instances") is None


def public_one_shot(kind: str, resource: dict[str, Any]) -> dict[str, Any]:
    public = upgrade_one_shot(resource)
    for key in list(public):
        if key.startswith("_"):
            del public[key]
    status = public.setdefault("status", {})
    if status.get("state") not in {"Failed", "Unknown"}:
        status.pop("detail", None)
    if kind != "snapshot" or status.get("state") != "Succeeded":
        status.pop("storageRef", None)
    return public


def public_resource(resource: dict[str, Any]) -> dict[str, Any]:
    public = copy.deepcopy(resource)
    finalize_mesh_status(public)
    for key in list(public):
        if key.startswith("_"):
            del public[key]
    canonicalize_resource_access(public)
    apply_derived_connection_status(public)

    storage = get_path(public, ["spec", "network", "storage"])
    if isinstance(storage, dict) and storage.get("ephemeral") is True:
        storage.pop("size", None)
    status = public.get("status")
    if isinstance(status, dict):
        sort_conditions(status)
    return public


def apply_derived_connection_status(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    if not isinstance(status, dict):
        status = {}
        resource["status"] = status

    status.pop("connectionDetails", None)
    connection_details = computed_connection_details(resource)
    if connection_details is not None:
        status["connectionDetails"] = connection_details

    status.pop("managementConnectionDetails", None)
    management_details = computed_management_connection_details(resource)
    if management_details is not None:
        status["managementConnectionDetails"] = management_details


def computed_connection_details(resource: dict[str, Any]) -> dict[str, Any] | None:
    exposure = get_path(resource, ["spec", "exposure"])
    if not isinstance(exposure, dict):
        return None
    name = get_path(resource, ["metadata", "name"])
    if not isinstance(name, str):
        name = ""

    exposure_type = exposure.get("type")
    if exposure_type == "Gateway":
        host = exposure.get("hostname")
        return {
            "host": host if isinstance(host, str) and host else DEFAULT_GATEWAY_HOST,
            "port": DEFAULT_SERVICE_PORT,
            "protocol": "https",
        }
    if exposure_type == "DirectPort":
        direct_port = exposure.get("directPort")
        return {
            "host": name,
            "port": direct_port if is_int(direct_port) else DEFAULT_DIRECT_PORT,
            "protocol": "https",
        }
    if exposure_type == "Balancer":
        port = exposure.get("port")
        return {
            "host": f"{name}-external",
            "port": port if is_int(port) else DEFAULT_SERVICE_PORT,
            "protocol": "https",
        }
    return None


def computed_management_connection_details(resource: dict[str, Any]) -> dict[str, Any] | None:
    if get_path(resource, ["spec", "management", "enabled"]) is not True:
        return None
    name = get_path(resource, ["metadata", "name"])
    if not isinstance(name, str):
        name = ""
    return {"host": f"{name}-admin", "port": MANAGEMENT_PORT, "protocol": "https"}


def public_vault(
    resource: dict[str, Any],
    meshes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    public = copy.deepcopy(upgrade_stored_vault(resource))
    spec = public.get("spec") if isinstance(public.get("spec"), dict) else {}
    mesh_ref = spec.get("meshRef")
    parent = meshes.get(mesh_ref) if isinstance(mesh_ref, str) else None
    stable = False
    if isinstance(parent, dict):
        stable = public_resource(upgrade_stored_resource(parent))["status"].get("stable") is True

    ready = "True" if stable else "False"
    public["status"] = {
        "conditions": [{"message": "", "status": ready, "type": "Ready"}],
        "state": "Ready" if ready == "True" else "Pending",
    }
    return public


def set_condition(
    status: dict[str, Any],
    condition_type: str,
    condition_status: str,
    message: str,
) -> None:
    conditions = [
        condition
        for condition in status.get("conditions", [])
        if isinstance(condition, dict) and condition.get("type") != condition_type
    ]
    conditions.append(
        {"type": condition_type, "status": condition_status, "message": message}
    )
    status["conditions"] = conditions
    sort_conditions(status)


def clear_condition(status: dict[str, Any], condition_type: str) -> None:
    status["conditions"] = [
        condition
        for condition in status.get("conditions", [])
        if isinstance(condition, dict) and condition.get("type") != condition_type
    ]
    sort_conditions(status)


def has_condition(status: dict[str, Any], condition_type: str) -> bool:
    return any(
        isinstance(condition, dict) and condition.get("type") == condition_type
        for condition in status.get("conditions", [])
    )


def condition_status(status: dict[str, Any], condition_type: str) -> str | None:
    for condition in status.get("conditions", []):
        if isinstance(condition, dict) and condition.get("type") == condition_type:
            value = condition.get("status")
            return value if isinstance(value, str) else None
    return None


def has_active_migration(resource: dict[str, Any]) -> bool:
    status = resource.get("status")
    if not isinstance(status, dict):
        return False
    return isinstance(status.get("migration"), dict) or condition_status(status, "Migration") == "True"


def sort_conditions(status: dict[str, Any]) -> None:
    unique: dict[str, dict[str, Any]] = {}
    for condition in status.get("conditions", []):
        if not isinstance(condition, dict):
            continue
        condition_type = condition.get("type")
        if not isinstance(condition_type, str):
            continue
        unique[condition_type] = {
            "type": condition_type,
            "status": condition.get("status", "False"),
            "message": condition.get("message", ""),
        }
    status["conditions"] = [unique[key] for key in sorted(unique)]


def is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def get_path(value: dict[str, Any], path: list[str]) -> Any:
    current: Any = value
    for item in path:
        if not isinstance(current, dict):
            return None
        current = current.get(item)
    return current


def validate_forbidden_autoscaling(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "autoScaling":
                errors.append(error(child_path, "autoScaling is forbidden", "forbidden"))
            validate_forbidden_autoscaling(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_forbidden_autoscaling(child, f"{path}.{index}", errors)


def error(field: str, message: str, error_type: str) -> dict[str, str]:
    return {"field": field, "message": message, "type": error_type}


def print_json(value: Any) -> None:
    print(json.dumps(value))


def print_errors(errors: list[dict[str, str]]) -> None:
    print_json({"errors": sorted(errors, key=lambda item: (item["field"], item["type"]))})


if __name__ == "__main__":
    raise SystemExit(main())
