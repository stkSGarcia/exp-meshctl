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
    return parser


def mesh_create(input_path: str) -> int:
    document, errors = load_mesh_input(input_path)
    if errors:
        print_errors(errors)
        return 0

    store = load_store()
    resource, errors = normalize_mesh_for_create(document)
    name = resource.get("metadata", {}).get("name")
    if isinstance(name, str) and name in store:
        errors.append(error("metadata.name", "Mesh already exists", "duplicate"))

    if errors:
        print_errors(errors)
        return 0

    store[name] = resource
    save_store(store)
    print_json(public_resource(resource))
    return 0


def mesh_update(input_path: str) -> int:
    document, errors = load_mesh_input(input_path)
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
    if name not in store:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0

    stored = upgrade_stored_resource(store[name])
    candidate = deep_merge(stored, update_patch(document))
    resume_without_count = should_resume_without_count(stored, document)
    if resume_without_count:
        desired = stored.get("status", {}).get("desiredInstancesOnResume")
        candidate.setdefault("spec", {})["instances"] = desired

    errors = validate_merged_resource(candidate, stored)
    if errors:
        print_errors(errors)
        return 0

    reconcile_update_status(stored, candidate, resume_without_count)
    store[name] = candidate
    save_store(store)
    print_json(public_resource(candidate))
    return 0


def mesh_list() -> int:
    store = load_store()
    summaries = [
        {"name": name, "status": {"state": public_resource(resource)["status"]["state"]}}
        for name, resource in sorted(store.items(), key=lambda item: item[0])
    ]
    print_json(summaries)
    return 0


def mesh_describe(name: str) -> int:
    store = load_store()
    if name not in store:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0

    resource = upgrade_stored_resource(store[name])
    completed = complete_pending_transition(resource)
    if completed or resource != store[name]:
        store[name] = resource
        save_store(store)
    print_json(public_resource(resource))
    return 0


def mesh_delete(name: str) -> int:
    store = load_store()
    if name not in store:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0
    del store[name]
    save_store(store)
    print_json({"message": f"Deleted mesh {name}", "metadata": {"name": name}})
    return 0


def store_path() -> Path:
    override = os.environ.get("MESHCTL_STORE")
    if override:
        return Path(override)
    return Path.cwd() / ".meshctl_store.json"


def load_store() -> dict[str, dict[str, Any]]:
    path = store_path()
    if not path.exists():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(content, dict):
        return {}
    return {
        str(name): resource
        for name, resource in content.items()
        if isinstance(resource, dict)
    }


def save_store(store: dict[str, dict[str, Any]]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, sort_keys=True), encoding="utf-8")


def load_mesh_input(input_path: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
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
    normalize_access(spec, normalized_spec)
    normalize_migration(spec, normalized_spec, errors)
    normalize_network(spec, normalized_spec, errors, apply_defaults=True)

    resource = {
        "metadata": {"name": name},
        "spec": normalized_spec,
        "status": {},
    }
    initialize_status(resource)
    validate_merged_resource(resource, None, errors)
    return resource, errors


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
    if "access" not in spec:
        spec["access"] = {"authentication": {"enabled": True}}
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
    validate_runtime(runtime, errors)


def validate_runtime(runtime: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(runtime, str) or not RUNTIME_RE.fullmatch(runtime):
        errors.append(error("spec.runtime", "Runtime must be major.minor.patch", "invalid"))


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


def normalize_access(spec: dict[str, Any], normalized_spec: dict[str, Any]) -> None:
    enabled = True
    access = spec.get("access")
    if isinstance(access, dict):
        authentication = access.get("authentication")
        if isinstance(authentication, dict) and "enabled" in authentication:
            enabled = authentication.get("enabled")
    normalized_spec["access"] = {"authentication": {"enabled": enabled}}


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
    validate_migration_strategy(strategy, errors)


def validate_migration_strategy(strategy: Any, errors: list[dict[str, str]]) -> None:
    if strategy != "FullStop":
        errors.append(
            error("spec.migration.strategy", "Migration strategy must be FullStop", "invalid")
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

    if stored is not None:
        stored_size = get_path(stored, ["spec", "network", "storage", "size"])
        candidate_size = get_path(resource, ["spec", "network", "storage", "size"])
        if stored_size != candidate_size:
            field = "spec.network.storage.size"
            errors.append(error(field, f"field '{field}' is immutable after creation", "immutable"))

    return errors


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
    if value is None or isinstance(value, dict):
        return
    errors.append(error("spec.access", "Access must be an object", "invalid"))


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
    status["stable"] = "_transition" not in resource
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
    sort_conditions(status)


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

    sort_conditions(status)


def complete_pending_transition(resource: dict[str, Any]) -> bool:
    transition = resource.pop("_transition", None)
    initialize_status(resource)
    if not isinstance(transition, dict):
        return False

    target = transition.get("target")
    if not is_non_negative_int(target):
        return True

    status = resource.setdefault("status", {})
    status["stable"] = True
    status["state"] = "Running" if target > 0 else "Stopped"
    if target > 0:
        status["instances"] = {"ready": target, "starting": 0, "stopped": 0}
        clear_condition(status, "Scaling")
        clear_condition(status, "GracefulShutdown")
        status.pop("desiredInstancesOnResume", None)
    else:
        status["instances"] = {"ready": 0, "starting": 0, "stopped": 0}
    sort_conditions(status)
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


def public_resource(resource: dict[str, Any]) -> dict[str, Any]:
    public = copy.deepcopy(resource)
    for key in list(public):
        if key.startswith("_"):
            del public[key]

    storage = get_path(public, ["spec", "network", "storage"])
    if isinstance(storage, dict) and storage.get("ephemeral") is True:
        storage.pop("size", None)
    status = public.get("status")
    if isinstance(status, dict):
        sort_conditions(status)
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
    print_json({"errors": errors})


if __name__ == "__main__":
    raise SystemExit(main())
