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
RUNTIME_CATALOG = {
    "3.0.0": "deprecated",
    "3.1.0": "skipped",
    "3.1.1": "supported",
    "3.2.0": "supported",
    "4.0.0": "supported",
    "4.0.1": "supported",
}
MIGRATION_STRATEGIES = {"FullStop", "LiveMigration", "RollingPatch"}
MIGRATION_STAGES = {
    "FullStop": ["Migrate"],
    "RollingPatch": ["Migrate"],
    "LiveMigration": ["Prepare", "Replicate", "Migrate"],
}
EXPOSURE_TYPES = {"Gateway", "DirectPort", "Balancer"}
EXPOSURE_ALLOWED_FIELDS = {
    "Gateway": {"type", "hostname", "annotations"},
    "DirectPort": {"type", "port", "directPort"},
    "Balancer": {"type", "port"},
}
REGION_EXPOSE_TYPES = {"Internal", "DirectPort", "Balancer", "Gateway"}
REGION_ENCRYPTION_PROTOCOLS = {"TLSv1.2", "TLSv1.3"}
REGION_KEY_STORES = ("transportKeyStore", "relayKeyStore", "trustStore")
PLACEMENT_AFFINITY_TYPES = {"preferred", "required"}
PLACEMENT_AFFINITY_SCOPES = {"node", "zone"}
TELEMETRY_LABEL_TAGS = {
    "mesh.io/targetLabels": "targetLabels",
    "mesh.io/probeTargetLabels": "probeTargetLabels",
    "mesh.io/instanceLabels": "instanceLabels",
}
DEFAULT_EXPOSURE_PORT = 443
MANAGEMENT_PORT = 9990
ONE_SHOT_KINDS = {
    "task": "tasks",
    "snapshot": "snapshots",
    "recovery": "recoveries",
}
SCOPE_KEYS = {"stores", "blueprints", "tallies", "definitions", "procedures"}


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
    if args.command in ONE_SHOT_KINDS:
        operation = getattr(args, f"{args.command}_operation")
        if operation == "create":
            return one_shot_create(args.command, args.file)
        if operation == "list":
            return one_shot_list(args.command)
        if operation == "describe":
            return one_shot_describe(args.command, args.name)
        if operation == "delete":
            return one_shot_delete(args.command, args.name)
        if operation == "update":
            return one_shot_update(args.command, args.file)
        if operation == "run":
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

    for kind in ONE_SHOT_KINDS:
        one_shot = commands.add_parser(kind)
        operations = one_shot.add_subparsers(dest=f"{kind}_operation", required=True)

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
    name = resource.get("metadata", {}).get("name")
    if isinstance(name, str) and name in meshes:
        errors.append(error("metadata.name", "Mesh already exists", "duplicate"))

    if errors:
        print_errors(errors)
        return 0

    warnings = collect_mesh_warnings(resource)
    meshes[name] = resource
    save_store(store)
    print_success(public_resource(resource), warnings)
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

    runtime_change = runtime_version_change(stored, candidate)
    errors = validate_merged_resource(candidate, stored)
    validate_active_migration_update(stored, document, errors)
    if runtime_change and not has_active_migration(stored):
        validate_runtime_version_change(stored, candidate, errors)
    if errors:
        print_errors(errors)
        return 0

    canonicalize_resource_access(candidate)
    canonicalize_mesh_policies(candidate)
    reconcile_update_status(stored, candidate, resume_without_count)
    if runtime_change:
        start_runtime_migration(stored, candidate)
    config_refresh = config_refresh_for_update(stored, candidate, document)
    warnings = collect_mesh_warnings(candidate)
    meshes[name] = candidate
    save_store(store)
    response = copy.deepcopy(candidate)
    if config_refresh is not None:
        response.setdefault("status", {})["configRefresh"] = config_refresh
    print_success(public_resource(response), warnings)
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


def mesh_migrate(name: str, rollback: bool = False) -> int:
    store = load_store()
    meshes = store["meshes"]
    if name not in meshes:
        print_errors([error("metadata.name", "Mesh not found", "not_found")])
        return 0

    resource = upgrade_stored_resource(meshes[name])
    migration = get_active_migration(resource)
    if migration is None:
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
        strategy = get_path(resource, ["spec", "migration", "strategy"])
        if strategy != "LiveMigration":
            print_errors(
                [
                    error(
                        "spec.migration.strategy",
                        "rollback is only supported for LiveMigration strategy",
                        "invalid",
                    )
                ]
            )
            return 0
        complete_runtime_migration(resource)
    else:
        advance_runtime_migration(resource)

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
    connection_details = get_path(resource, ["status", "connectionDetails"])
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

    if resource != meshes[name]:
        meshes[name] = resource
        save_store(store)
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
    collection = one_shot_collection(store, kind)
    resource, errors = normalize_one_shot_for_create(kind, document, store)
    name = resource.get("metadata", {}).get("name")
    if isinstance(name, str) and name in collection:
        errors.append(error("metadata.name", f"{kind.capitalize()} already exists", "duplicate"))

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
    collection = one_shot_collection(store, kind)
    if name not in collection:
        print_errors([not_found_error(kind)])
        return 0

    stored = upgrade_stored_one_shot(kind, collection[name])
    candidate = deep_merge(stored, one_shot_update_patch(document))
    validate_one_shot_update(candidate, stored, errors)
    if errors:
        print_errors(errors)
        return 0

    collection[name] = candidate
    save_store(store)
    print_json(public_one_shot(kind, candidate))
    return 0


def one_shot_list(kind: str) -> int:
    store = load_store()
    collection = one_shot_collection(store, kind)
    summaries = []
    for name, resource in sorted(collection.items(), key=lambda item: item[0]):
        public = public_one_shot(kind, upgrade_stored_one_shot(kind, resource))
        summaries.append(
            {
                "name": name,
                "meshRef": public["spec"].get("meshRef"),
                "status": public["status"],
            }
        )
    print_json(summaries)
    return 0


def one_shot_describe(kind: str, name: str) -> int:
    store = load_store()
    collection = one_shot_collection(store, kind)
    if name not in collection:
        print_errors([not_found_error(kind)])
        return 0
    print_json(public_one_shot(kind, upgrade_stored_one_shot(kind, collection[name])))
    return 0


def one_shot_delete(kind: str, name: str) -> int:
    store = load_store()
    collection = one_shot_collection(store, kind)
    if name not in collection:
        print_errors([not_found_error(kind)])
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
    collection = one_shot_collection(store, kind)
    if name not in collection:
        print_errors([not_found_error(kind)])
        return 0

    resource = upgrade_stored_one_shot(kind, collection[name])
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
        run_snapshot(resource, store)
    elif kind == "recovery":
        run_recovery(resource, store)

    collection[name] = resource
    save_store(store)
    print_json(public_one_shot(kind, resource))
    return 0


def one_shot_collection(
    store: dict[str, dict[str, dict[str, Any]]],
    kind: str,
) -> dict[str, dict[str, Any]]:
    return store[ONE_SHOT_KINDS[kind]]


def not_found_error(kind: str) -> dict[str, str]:
    return error("metadata.name", f"{kind.capitalize()} not found", "not_found")


def normalize_one_shot_for_create(
    kind: str,
    document: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if kind == "task":
        return normalize_task_for_create(document, store)
    if kind == "snapshot":
        return normalize_snapshot_for_create(document, store)
    return normalize_recovery_for_create(document, store)


def normalize_base_one_shot(
    document: dict[str, Any],
    errors: list[dict[str, str]],
) -> tuple[Any, dict[str, Any]]:
    metadata = document.get("metadata")
    spec = document.get("spec")
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}
    name = metadata.get("name")
    validate_name(name, errors)
    return name, spec


def normalize_task_for_create(
    document: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    name, spec = normalize_base_one_shot(document, errors)
    normalized_spec: dict[str, Any] = {}
    normalize_mesh_ref(spec, store, normalized_spec, errors)

    inline = spec.get("inline")
    bundle_ref = spec.get("bundleRef")
    has_inline = isinstance(inline, str) and inline != ""
    has_bundle = isinstance(bundle_ref, str) and bundle_ref != ""
    if has_inline == has_bundle:
        errors.append(task_source_error())
    elif has_inline:
        normalized_spec["inline"] = inline
    else:
        normalized_spec["bundleRef"] = bundle_ref

    return initializing_resource(name, normalized_spec), errors


def normalize_snapshot_for_create(
    document: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    name, spec = normalize_base_one_shot(document, errors)
    normalized_spec: dict[str, Any] = {}
    normalize_mesh_ref(spec, store, normalized_spec, errors)
    normalize_snapshot_storage(spec, normalized_spec, errors)
    normalize_scope(spec, normalized_spec, errors)
    normalize_resources(spec, normalized_spec, errors)
    return initializing_resource(name, normalized_spec), errors


def normalize_recovery_for_create(
    document: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    name, spec = normalize_base_one_shot(document, errors)
    normalized_spec: dict[str, Any] = {}
    normalize_mesh_ref(spec, store, normalized_spec, errors)

    snapshot_ref = spec.get("snapshotRef")
    if not isinstance(snapshot_ref, str) or snapshot_ref == "":
        errors.append(error("spec.snapshotRef", "Snapshot reference is required", "invalid"))
    elif snapshot_ref not in store["snapshots"]:
        errors.append(error("spec.snapshotRef", f"Snapshot {snapshot_ref} does not exist", "invalid"))
    else:
        normalized_spec["snapshotRef"] = snapshot_ref
        mesh_ref = normalized_spec.get("meshRef")
        snapshot_mesh = get_path(store["snapshots"][snapshot_ref], ["spec", "meshRef"])
        if isinstance(mesh_ref, str) and snapshot_mesh != mesh_ref:
            errors.append(
                error(
                    "spec.snapshotRef",
                    f"snapshot '{snapshot_ref}' belongs to mesh '{snapshot_mesh}', not '{mesh_ref}'",
                    "invalid",
                )
            )

    normalize_scope(spec, normalized_spec, errors)
    normalize_resources(spec, normalized_spec, errors)
    return initializing_resource(name, normalized_spec), errors


def normalize_mesh_ref(
    spec: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    mesh_ref = spec.get("meshRef")
    if not isinstance(mesh_ref, str) or mesh_ref == "":
        errors.append(error("spec.meshRef", "Mesh reference is required", "invalid"))
    elif mesh_ref not in store["meshes"]:
        errors.append(error("spec.meshRef", f"Mesh {mesh_ref} does not exist", "invalid"))
    else:
        normalized_spec["meshRef"] = mesh_ref


def normalize_snapshot_storage(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    storage = spec.get("storage")
    if storage is None:
        return
    if not isinstance(storage, dict):
        errors.append(error("spec.storage", "Storage must be an object", "invalid"))
        return
    normalized_storage: dict[str, Any] = {}
    if "size" in storage:
        size = storage.get("size")
        normalized_storage["size"] = size
        if size is not None and not isinstance(size, str):
            errors.append(error("spec.storage.size", "Storage size must be string", "invalid"))
    if "className" in storage:
        class_name = storage.get("className")
        normalized_storage["className"] = class_name
        if class_name is not None and not isinstance(class_name, str):
            errors.append(error("spec.storage.className", "Storage className must be string", "invalid"))
    normalized_spec["storage"] = normalized_storage


def normalize_scope(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if "scope" not in spec:
        return
    scope = spec.get("scope")
    if not isinstance(scope, dict):
        errors.append(error("spec.scope", "Scope must be an object", "invalid"))
        return
    normalized_scope: dict[str, Any] = {}
    for key, value in scope.items():
        if key not in SCOPE_KEYS:
            errors.append(error(f"spec.scope.{key}", "Scope key is invalid", "invalid"))
            continue
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            errors.append(error(f"spec.scope.{key}", "Scope values must be non-empty strings", "invalid"))
            continue
        normalized_scope[key] = copy.deepcopy(value)
    normalized_spec["scope"] = normalized_scope


def initializing_resource(name: Any, spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "metadata": {"name": name},
        "spec": spec,
        "status": {"state": "Initializing"},
    }


def task_source_error() -> dict[str, str]:
    return error(
        "spec",
        "exactly one of 'spec.inline' or 'spec.bundleRef' must be set",
        "invalid",
    )


def one_shot_update_patch(document: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if isinstance(document.get("metadata"), dict):
        patch["metadata"] = {"name": document["metadata"].get("name")}
    if isinstance(document.get("spec"), dict):
        patch["spec"] = copy.deepcopy(document["spec"])
    if isinstance(document.get("status"), dict):
        patch["status"] = copy.deepcopy(document["status"])
    return patch


def validate_one_shot_update(
    candidate: dict[str, Any],
    stored: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    validate_name(get_path(candidate, ["metadata", "name"]), errors)
    incoming_spec = candidate.get("spec") if isinstance(candidate.get("spec"), dict) else {}
    stored_spec = stored.get("spec") if isinstance(stored.get("spec"), dict) else {}
    compare_immutable_specs(stored_spec, incoming_spec, "spec", errors)


def compare_immutable_specs(
    stored: Any,
    candidate: Any,
    path: str,
    errors: list[dict[str, str]],
) -> None:
    if isinstance(stored, dict) and isinstance(candidate, dict):
        for key in sorted(set(stored) | set(candidate)):
            compare_immutable_specs(
                stored.get(key),
                candidate.get(key),
                f"{path}.{key}",
                errors,
            )
        return
    if stored != candidate:
        errors.append(error(path, f"field '{path}' is immutable after creation", "immutable"))


def upgrade_stored_one_shot(kind: str, resource: dict[str, Any]) -> dict[str, Any]:
    upgraded = copy.deepcopy(resource)
    metadata = upgraded.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        upgraded["metadata"] = metadata
    spec = upgraded.setdefault("spec", {})
    if not isinstance(spec, dict):
        spec = {}
        upgraded["spec"] = spec
    if kind in {"snapshot", "recovery"}:
        resources = spec.setdefault("resources", {})
        if not isinstance(resources, dict):
            resources = {}
            spec["resources"] = resources
        resources.setdefault("memory", {"limit": "1Gi", "request": "1Gi"})
    status = upgraded.setdefault("status", {})
    if not isinstance(status, dict):
        status = {}
        upgraded["status"] = status
    status.setdefault("state", "Initializing")
    return upgraded


def run_task(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    status.pop("detail", None)
    inline = get_path(resource, ["spec", "inline"])
    if isinstance(inline, str):
        for index, line in enumerate(inline.splitlines(), start=1):
            if line.startswith("FAIL:"):
                reason = line.removeprefix("FAIL:").strip()
                status["state"] = "Failed"
                status["detail"] = f"command {index} failed: {reason}"
                return
    status["state"] = "Succeeded"


def run_snapshot(
    resource: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> None:
    status = resource.setdefault("status", {})
    status.pop("detail", None)
    status.pop("storageRef", None)
    if referenced_mesh_stable(resource, store):
        status["state"] = "Succeeded"
        status["storageRef"] = f"snapshot://{resource['metadata']['name']}"
    else:
        status["state"] = "Unknown"
        status["detail"] = "referenced mesh is not stable"


def run_recovery(
    resource: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> None:
    status = resource.setdefault("status", {})
    status.pop("detail", None)
    if referenced_mesh_stable(resource, store):
        status["state"] = "Succeeded"
    else:
        status["state"] = "Unknown"
        status["detail"] = "referenced mesh is not stable"


def referenced_mesh_stable(
    resource: dict[str, Any],
    store: dict[str, dict[str, dict[str, Any]]],
) -> bool:
    mesh_ref = get_path(resource, ["spec", "meshRef"])
    mesh = store["meshes"].get(mesh_ref) if isinstance(mesh_ref, str) else None
    if not isinstance(mesh, dict):
        return False
    public = public_resource(upgrade_stored_resource(mesh))
    return public["status"].get("stable") is True


def public_one_shot(kind: str, resource: dict[str, Any]) -> dict[str, Any]:
    public = copy.deepcopy(upgrade_stored_one_shot(kind, resource))
    status = public.setdefault("status", {})
    if status.get("state") not in {"Failed", "Unknown"}:
        status.pop("detail", None)
    if kind != "snapshot" or status.get("state") != "Succeeded":
        status.pop("storageRef", None)
    return public


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
    if any(key in content for key in ("meshes", "vaults", "tasks", "snapshots", "recoveries")):
        store = {
            "meshes": clean_resource_collection(content.get("meshes")),
            "vaults": clean_resource_collection(content.get("vaults")),
            "tasks": clean_resource_collection(content.get("tasks")),
            "snapshots": clean_resource_collection(content.get("snapshots")),
            "recoveries": clean_resource_collection(content.get("recoveries")),
        }
        return store
    return {
        "meshes": clean_resource_collection(content),
        "vaults": {},
        "tasks": {},
        "snapshots": {},
        "recoveries": {},
    }


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
    metadata_tags = metadata.get("tags") if isinstance(metadata, dict) else None

    normalized_spec: dict[str, Any] = {}
    normalize_instances(spec, normalized_spec, errors, default=1)
    normalize_runtime(spec, normalized_spec, errors)
    normalize_resources(spec, normalized_spec, errors)
    normalize_access(spec, normalized_spec, errors)
    normalize_migration(spec, normalized_spec, errors)
    normalize_network(spec, normalized_spec, errors, apply_defaults=True)
    normalize_exposure(spec, normalized_spec, errors)
    normalize_management(spec, normalized_spec, errors)
    normalize_placement(spec, normalized_spec, errors)
    normalize_regions(spec, normalized_spec, errors)
    normalize_config_bundle_ref(spec, normalized_spec)
    normalize_extensions(spec, normalized_spec, errors)

    normalized_metadata = {"name": name}
    if "tags" in metadata:
        normalized_metadata["tags"] = copy.deepcopy(metadata_tags)

    resource = {
        "metadata": normalized_metadata,
        "spec": normalized_spec,
        "status": {},
    }
    initialize_status(resource)
    validate_merged_resource(resource, None, errors)
    if not errors:
        canonicalize_resource_access(resource)
        canonicalize_mesh_policies(resource)
        reconcile_connectivity_status(resource)
        reconcile_mesh_policy_status(resource)
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


def update_patch(document: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    if isinstance(document.get("metadata"), dict):
        patch["metadata"] = {"name": document["metadata"].get("name")}
        if "tags" in document["metadata"]:
            patch["metadata"]["tags"] = copy.deepcopy(document["metadata"].get("tags"))
    if isinstance(document.get("spec"), dict):
        patch["spec"] = copy.deepcopy(document["spec"])
    return patch


def config_refresh_for_update(
    stored: dict[str, Any],
    candidate: dict[str, Any],
    document: dict[str, Any],
) -> dict[str, Any] | None:
    spec = document.get("spec")
    if not isinstance(spec, dict) or "configBundleRef" not in spec:
        return None
    previous = get_path(stored, ["spec", "configBundleRef"])
    current = get_path(candidate, ["spec", "configBundleRef"])
    if current == previous:
        return None
    return {"currentRef": current, "pending": True, "previousRef": previous}


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
    metadata = upgraded.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        upgraded["metadata"] = metadata
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
    if "exposure" in spec:
        normalized_exposure = defaulted_exposure(spec.get("exposure"))
        if normalized_exposure is not None:
            spec["exposure"] = normalized_exposure
    spec["management"] = defaulted_management(spec.get("management"))
    canonicalize_mesh_policies(upgraded)

    if "status" not in upgraded or not isinstance(upgraded.get("status"), dict):
        upgraded["status"] = {}
    initialize_status(upgraded)
    reconcile_connectivity_status(upgraded)
    reconcile_mesh_policy_status(upgraded)
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


def validate_runtime_catalog(runtime: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(runtime, str) or not RUNTIME_RE.fullmatch(runtime):
        return
    status = RUNTIME_CATALOG.get(runtime)
    if status is None:
        errors.append(error("spec.runtime", f"runtime version '{runtime}' is not supported", "invalid"))
    elif status == "skipped":
        errors.append(
            error(
                "spec.runtime",
                f"runtime version '{runtime}' is skipped and cannot be targeted",
                "invalid",
            )
        )


def collect_runtime_warnings(resource: dict[str, Any]) -> list[dict[str, str]]:
    runtime = get_path(resource, ["spec", "runtime"])
    if isinstance(runtime, str) and RUNTIME_CATALOG.get(runtime) == "deprecated":
        return [
            {
                "field": "spec.runtime",
                "message": f"runtime version '{runtime}' is deprecated",
            }
        ]
    return []


def collect_mesh_warnings(resource: dict[str, Any]) -> list[dict[str, str]]:
    warnings = collect_runtime_warnings(resource)
    encryption = get_path(resource, ["spec", "regions", "local", "encryption"])
    if isinstance(encryption, dict) and "trustStore" not in encryption:
        warnings.append(
            {
                "field": "spec.regions.local.encryption.trustStore",
                "message": "trustStore is recommended when regional encryption is configured",
            }
        )
    return warnings


def parse_runtime_version(runtime: Any) -> tuple[int, int, int] | None:
    if not isinstance(runtime, str):
        return None
    match = RUNTIME_RE.fullmatch(runtime)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def runtime_is_catalog_version(runtime: Any) -> bool:
    return isinstance(runtime, str) and runtime in RUNTIME_CATALOG


def runtime_version_change(
    stored: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    source = get_path(stored, ["spec", "runtime"])
    target = get_path(candidate, ["spec", "runtime"])
    return (
        runtime_is_catalog_version(source)
        and runtime_is_catalog_version(target)
        and source != target
    )


def validate_runtime_version_change(
    stored: dict[str, Any],
    candidate: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    source = get_path(stored, ["spec", "runtime"])
    target = get_path(candidate, ["spec", "runtime"])
    source_version = parse_runtime_version(source)
    target_version = parse_runtime_version(target)
    if source_version is None or target_version is None:
        return

    if target_version < source_version:
        errors.append(
            error(
                "spec.runtime",
                f"version downgrade from '{source}' to '{target}' is not allowed",
                "invalid",
            )
        )

    strategy = get_path(candidate, ["spec", "migration", "strategy"])
    if strategy == "RollingPatch":
        if source_version[:2] != target_version[:2]:
            errors.append(
                error(
                    "spec.runtime",
                    "RollingPatch requires source and target runtime to share the same major and minor version",
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
    elif strategy == "LiveMigration" and get_path(candidate, ["spec", "regions"]) is not None:
        errors.append(
            error(
                "spec.migration.strategy",
                "LiveMigration strategy is not supported with multi-region topology",
                "invalid",
            )
        )


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
    validate_migration_strategy(strategy, errors)


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


def normalize_exposure(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if "exposure" not in spec:
        return
    exposure = spec.get("exposure")
    if exposure is None:
        normalized_spec["exposure"] = {"type": None}
        return
    normalized_exposure = defaulted_exposure(exposure)
    if normalized_exposure is None:
        errors.append(error("spec.exposure", "Exposure must be an object", "invalid"))
        return
    normalized_spec["exposure"] = normalized_exposure


def defaulted_exposure(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    exposure_type = value.get("type")
    normalized: dict[str, Any] = copy.deepcopy(value)
    normalized["type"] = exposure_type
    if exposure_type == "Gateway":
        return normalized
    elif exposure_type == "DirectPort":
        normalized["port"] = value.get("port", DEFAULT_EXPOSURE_PORT)
        normalized["directPort"] = value.get("directPort", DEFAULT_EXPOSURE_PORT)
    elif exposure_type == "Balancer":
        normalized["port"] = value.get("port", DEFAULT_EXPOSURE_PORT)
    return normalized


def normalize_management(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    management = spec.get("management")
    normalized_management = defaulted_management(management)
    if management is not None and not isinstance(management, dict):
        errors.append(error("spec.management", "Management must be an object", "invalid"))
    normalized_spec["management"] = normalized_management


def defaulted_management(value: Any) -> dict[str, Any]:
    management = value if isinstance(value, dict) else {}
    return {"enabled": management.get("enabled", False)}


def normalize_placement(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    placement = spec.get("placement")
    if placement is not None and not isinstance(placement, dict):
        errors.append(error("spec.placement", "Placement must be an object", "invalid"))
    normalized_spec["placement"] = defaulted_placement(placement)


def defaulted_placement(value: Any) -> dict[str, Any]:
    placement = value if isinstance(value, dict) else {}
    affinity = placement.get("affinity")
    if not isinstance(affinity, dict):
        affinity = {}
    return {
        "affinity": {
            "type": affinity.get("type", "preferred"),
            "scope": affinity.get("scope", "node"),
        }
    }


def normalize_regions(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if "regions" not in spec:
        return
    regions = defaulted_regions(spec.get("regions"))
    normalized_spec["regions"] = spec.get("regions") if regions is None else regions


def defaulted_regions(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    normalized: dict[str, Any] = {}
    local = value.get("local")
    if isinstance(local, dict):
        normalized_local: dict[str, Any] = {}
        if "name" in local:
            normalized_local["name"] = local.get("name")
        expose = local.get("expose")
        if isinstance(expose, dict):
            normalized_local["expose"] = {"type": expose.get("type")}
        elif "expose" in local:
            normalized_local["expose"] = copy.deepcopy(expose)
        if "maxRelayNodes" in local:
            normalized_local["maxRelayNodes"] = local.get("maxRelayNodes")
        if "encryption" in local:
            encryption = defaulted_region_encryption(local.get("encryption"))
            normalized_local["encryption"] = (
                copy.deepcopy(local.get("encryption")) if encryption is None else encryption
            )
        discovery = defaulted_region_discovery(local.get("discovery"))
        if "discovery" in local or discovery is not None:
            normalized_local["discovery"] = discovery
        normalized["local"] = normalized_local
    elif "local" in value:
        normalized["local"] = copy.deepcopy(local)

    if "remotes" in value:
        normalized["remotes"] = defaulted_region_remotes(value.get("remotes"))
    return normalized


def defaulted_region_encryption(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, Any] = {"protocol": value.get("protocol", "TLSv1.3")}
    for store in REGION_KEY_STORES:
        if store in value:
            normalized[store] = copy.deepcopy(value.get(store))
    return normalized


def defaulted_region_discovery(value: Any) -> dict[str, Any] | None:
    if value is None:
        return {
            "type": "relay",
            "heartbeat": {"enabled": True, "interval": 10000, "timeout": 30000},
        }
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    heartbeat = value.get("heartbeat")
    if not isinstance(heartbeat, dict):
        heartbeat = {}
    return {
        "type": value.get("type", "relay"),
        "heartbeat": {
            "enabled": heartbeat.get("enabled", True),
            "interval": heartbeat.get("interval", 10000),
            "timeout": heartbeat.get("timeout", 30000),
        },
    }


def defaulted_region_remotes(value: Any) -> Any:
    if not isinstance(value, list):
        return copy.deepcopy(value)
    remotes: list[Any] = []
    for remote in value:
        if not isinstance(remote, dict):
            remotes.append(copy.deepcopy(remote))
            continue
        normalized: dict[str, Any] = {}
        for field in ("name", "url", "credentialRef", "namespace", "clusterRef"):
            if field in remote and remote.get(field) is not None:
                normalized[field] = remote.get(field)
        remotes.append(normalized)
    return remotes


def normalize_config_bundle_ref(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
) -> None:
    if "configBundleRef" in spec:
        normalized_spec["configBundleRef"] = spec.get("configBundleRef")


def normalize_extensions(
    spec: dict[str, Any],
    normalized_spec: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if "extensions" not in spec:
        return
    normalized_spec["extensions"] = defaulted_extensions(spec.get("extensions"))


def defaulted_extensions(value: Any) -> Any:
    if not isinstance(value, list):
        return copy.deepcopy(value)
    extensions: list[Any] = []
    for item in value:
        if not isinstance(item, dict):
            extensions.append(copy.deepcopy(item))
            continue
        normalized: dict[str, Any] = {}
        for field in ("url", "artifact", "integrity"):
            if field in item and item.get(field) is not None:
                normalized[field] = item.get(field)
        extensions.append(normalized)
    return extensions


def canonicalize_mesh_policies(resource: dict[str, Any]) -> None:
    metadata = resource.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        resource["metadata"] = metadata
    if "tags" in metadata and isinstance(metadata.get("tags"), dict):
        metadata["tags"] = copy.deepcopy(metadata["tags"])

    spec = resource.setdefault("spec", {})
    if not isinstance(spec, dict):
        return
    spec["placement"] = defaulted_placement(spec.get("placement"))
    if "regions" in spec:
        regions = defaulted_regions(spec.get("regions"))
        if regions is not None:
            spec["regions"] = regions
    if spec.get("configBundleRef") is None:
        spec.pop("configBundleRef", None)
    if "extensions" in spec:
        spec["extensions"] = defaulted_extensions(spec.get("extensions"))


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
    validate_metadata_tags(metadata.get("tags"), errors)
    validate_forbidden_autoscaling(spec, "spec", errors)

    if "instances" in spec:
        validate_instances(spec.get("instances"), errors)
    if "runtime" in spec:
        validate_runtime(spec.get("runtime"), errors)
        validate_runtime_catalog(spec.get("runtime"), errors)
    validate_resources_object(spec.get("resources"), errors)
    validate_access_object(spec.get("access"), errors)
    validate_migration_object(spec.get("migration"), errors)
    validate_network_object(spec.get("network"), spec.get("instances"), errors)
    validate_exposure_object(spec.get("exposure"), errors)
    validate_management_object(spec.get("management"), errors)
    validate_placement_object(spec.get("placement"), errors)
    if "regions" in spec:
        validate_regions_object(spec.get("regions"), errors)
    validate_regional_migration(spec, errors)
    validate_config_bundle_ref(spec, stored is None, errors)
    validate_extensions_object(spec.get("extensions"), errors)

    if stored is not None:
        stored_size = get_path(stored, ["spec", "network", "storage", "size"])
        candidate_size = get_path(resource, ["spec", "network", "storage", "size"])
        if stored_size != candidate_size:
            field = "spec.network.storage.size"
            errors.append(error(field, f"field '{field}' is immutable after creation", "immutable"))
        stored_management = get_path(stored, ["spec", "management", "enabled"])
        candidate_management = get_path(resource, ["spec", "management", "enabled"])
        if stored_management != candidate_management:
            field = "spec.management.enabled"
            errors.append(
                error(
                    field,
                    "field 'spec.management.enabled' is immutable after creation",
                    "immutable",
                )
            )

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
        allowed_fields: set[str] = {"type"}
    elif exposure_type not in EXPOSURE_TYPES:
        errors.append(error("spec.exposure.type", "Exposure type is invalid", "invalid"))
        allowed_fields = {"type"}
    else:
        allowed_fields = EXPOSURE_ALLOWED_FIELDS[exposure_type]

    for field in sorted(set(value) - allowed_fields):
        errors.append(
            error(
                f"spec.exposure.{field}",
                f"field 'spec.exposure.{field}' is forbidden for exposure type '{exposure_type}'",
                "forbidden",
            )
        )

    if "hostname" in value and not isinstance(value.get("hostname"), str):
        errors.append(error("spec.exposure.hostname", "Exposure hostname must be string", "invalid"))
    if "annotations" in value:
        validate_string_map(value.get("annotations"), "spec.exposure.annotations", errors)
    for field in ("port", "directPort"):
        if field in value and not is_non_negative_int(value.get(field)):
            errors.append(error(f"spec.exposure.{field}", f"Exposure {field} must be an integer", "invalid"))


def validate_string_map(
    value: Any,
    field: str,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(value, dict):
        errors.append(error(field, f"{field} must be a string map", "invalid"))
        return
    for key, child in value.items():
        if not isinstance(key, str) or not isinstance(child, str):
            errors.append(error(field, f"{field} must be a string map", "invalid"))
            return


def validate_metadata_tags(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    validate_string_map(value, "metadata.tags", errors)


def validate_management_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.management", "Management must be an object", "invalid"))
        return
    if "enabled" in value and not isinstance(value.get("enabled"), bool):
        errors.append(error("spec.management.enabled", "Management enabled must be boolean", "invalid"))


def validate_placement_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.placement", "Placement must be an object", "invalid"))
        return
    affinity = value.get("affinity")
    if affinity is not None and not isinstance(affinity, dict):
        errors.append(error("spec.placement.affinity", "Placement affinity must be an object", "invalid"))
        return
    if not isinstance(affinity, dict):
        return
    affinity_type = affinity.get("type", "preferred")
    if affinity_type not in PLACEMENT_AFFINITY_TYPES:
        errors.append(error("spec.placement.affinity.type", "Placement affinity type is invalid", "invalid"))
    affinity_scope = affinity.get("scope", "node")
    if affinity_scope not in PLACEMENT_AFFINITY_SCOPES:
        errors.append(error("spec.placement.affinity.scope", "Placement affinity scope is invalid", "invalid"))


def validate_regions_object(value: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, dict):
        errors.append(error("spec.regions", "Regions must be an object", "invalid"))
        if value is None:
            errors.append(error("spec.regions.local", "Local region is required", "required"))
        return

    local = value.get("local")
    if local is None:
        errors.append(error("spec.regions.local", "Local region is required", "required"))
        return
    if not isinstance(local, dict):
        errors.append(error("spec.regions.local", "Local region must be an object", "invalid"))
        return

    name = local.get("name")
    if name is None or name == "":
        errors.append(error("spec.regions.local.name", "Local region name is required", "required"))
    elif not isinstance(name, str):
        errors.append(error("spec.regions.local.name", "Local region name must be string", "invalid"))

    validate_region_expose(local.get("expose"), errors)
    if "maxRelayNodes" in local and not is_positive_int(local.get("maxRelayNodes")):
        errors.append(
            error("spec.regions.local.maxRelayNodes", "Local region maxRelayNodes must be greater than 0", "invalid")
        )
    validate_region_encryption(local, errors)
    validate_region_discovery(local.get("discovery"), errors)
    validate_region_remotes(value.get("remotes"), errors)


def validate_region_expose(value: Any, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, dict):
        errors.append(error("spec.regions.local.expose.type", "Local region expose type is required", "required"))
        return
    expose_type = value.get("type")
    if expose_type is None or expose_type == "":
        errors.append(error("spec.regions.local.expose.type", "Local region expose type is required", "required"))
    elif expose_type not in REGION_EXPOSE_TYPES:
        errors.append(error("spec.regions.local.expose.type", "Local region expose type is invalid", "invalid"))


def validate_region_encryption(local: dict[str, Any], errors: list[dict[str, str]]) -> None:
    encryption = local.get("encryption")
    expose_type = get_path(local, ["expose", "type"])
    if encryption is None:
        if expose_type == "Gateway":
            errors.append(
                error(
                    "spec.regions.local.encryption.transportKeyStore",
                    "Gateway exposure requires a transport key store",
                    "required",
                )
            )
        return
    if not isinstance(encryption, dict):
        errors.append(error("spec.regions.local.encryption", "Local region encryption must be an object", "invalid"))
        return

    protocol = encryption.get("protocol", "TLSv1.3")
    if protocol not in REGION_ENCRYPTION_PROTOCOLS:
        errors.append(error("spec.regions.local.encryption.protocol", "Encryption protocol is invalid", "invalid"))
    if expose_type == "Gateway" and "transportKeyStore" not in encryption:
        errors.append(
            error(
                "spec.regions.local.encryption.transportKeyStore",
                "Gateway exposure requires a transport key store",
                "required",
            )
        )
    for store in REGION_KEY_STORES:
        if store in encryption:
            validate_region_key_store(encryption.get(store), store, errors)


def validate_region_key_store(
    value: Any,
    store: str,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(value, dict):
        errors.append(
            error(f"spec.regions.local.encryption.{store}", "Region key store must be an object", "invalid")
        )
        return
    for field in ("secretRef", "alias", "filename"):
        if value.get(field) is None or value.get(field) == "":
            errors.append(
                error(
                    f"spec.regions.local.encryption.{store}.{field}",
                    f"Region key store {field} is required",
                    "required",
                )
            )
        elif not isinstance(value.get(field), str):
            errors.append(
                error(
                    f"spec.regions.local.encryption.{store}.{field}",
                    f"Region key store {field} must be string",
                    "invalid",
                )
            )


def validate_region_discovery(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(error("spec.regions.local.discovery", "Local region discovery must be an object", "invalid"))
        return
    if value.get("type", "relay") != "relay":
        errors.append(error("spec.regions.local.discovery.type", "Local region discovery type is invalid", "invalid"))
    heartbeat = value.get("heartbeat")
    if heartbeat is None:
        return
    if not isinstance(heartbeat, dict):
        errors.append(
            error("spec.regions.local.discovery.heartbeat", "Local region discovery heartbeat must be an object", "invalid")
        )
        return
    interval = heartbeat.get("interval", 10000)
    timeout = heartbeat.get("timeout", 30000)
    if not is_positive_int(interval) or not is_positive_int(timeout) or interval >= timeout:
        errors.append(
            error(
                "spec.regions.local.discovery.heartbeat",
                "Heartbeat interval must be less than timeout",
                "invalid",
            )
        )


def validate_region_remotes(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(error("spec.regions.remotes", "Region remotes must be an array", "invalid"))
        return
    seen_names: set[str] = set()
    for index, remote in enumerate(value):
        if not isinstance(remote, dict):
            errors.append(error(f"spec.regions.remotes[{index}]", "Region remote must be an object", "invalid"))
            continue
        name = remote.get("name")
        if name is None or name == "":
            errors.append(error(f"spec.regions.remotes[{index}].name", "Remote region name is required", "required"))
        elif not isinstance(name, str):
            errors.append(error(f"spec.regions.remotes[{index}].name", "Remote region name must be string", "invalid"))
        elif name in seen_names:
            errors.append(error(f"spec.regions.remotes[{index}].name", "Remote region name is duplicate", "duplicate"))
        else:
            seen_names.add(name)

        url = remote.get("url")
        if url is None or url == "":
            errors.append(error(f"spec.regions.remotes[{index}].url", "Remote region URL is required", "required"))
        elif not isinstance(url, str):
            errors.append(error(f"spec.regions.remotes[{index}].url", "Remote region URL must be string", "invalid"))
        for field in ("credentialRef", "namespace", "clusterRef"):
            if field in remote and not isinstance(remote.get(field), str):
                errors.append(error(f"spec.regions.remotes[{index}].{field}", f"Remote region {field} must be string", "invalid"))


def validate_regional_migration(spec: dict[str, Any], errors: list[dict[str, str]]) -> None:
    if "regions" not in spec:
        return
    if get_path(spec, ["migration", "strategy"]) == "LiveMigration":
        errors.append(
            error(
                "spec.migration.strategy",
                "LiveMigration strategy is not supported with multi-region topology",
                "invalid",
            )
        )


def validate_config_bundle_ref(
    spec: dict[str, Any],
    is_create: bool,
    errors: list[dict[str, str]],
) -> None:
    if "configBundleRef" not in spec:
        return
    value = spec.get("configBundleRef")
    if value is None and is_create:
        errors.append(error("spec.configBundleRef", "Config bundle reference must be string", "invalid"))
    elif value is not None and not isinstance(value, str):
        errors.append(error("spec.configBundleRef", "Config bundle reference must be string", "invalid"))


def validate_extensions_object(value: Any, errors: list[dict[str, str]]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(error("spec.extensions", "Extensions must be an array", "invalid"))
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(error(f"spec.extensions[{index}]", "Extension must be an object", "invalid"))
            continue
        has_url = item.get("url") is not None
        has_artifact = item.get("artifact") is not None
        if has_url == has_artifact:
            errors.append(
                error(
                    f"spec.extensions[{index}]",
                    "exactly one of 'url' or 'artifact' must be set",
                    "invalid",
                )
            )
        for field in ("url", "artifact", "integrity"):
            if field in item and item.get(field) is not None and not isinstance(item.get(field), str):
                errors.append(error(f"spec.extensions[{index}].{field}", f"Extension {field} must be string", "invalid"))


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


def has_active_migration(resource: dict[str, Any]) -> bool:
    return get_active_migration(resource) is not None


def get_active_migration(resource: dict[str, Any]) -> dict[str, Any] | None:
    migration = get_path(resource, ["status", "migration"])
    if not isinstance(migration, dict):
        return None
    if not condition_is(resource.get("status", {}), "Migration", "True"):
        return None
    return migration


def validate_active_migration_update(
    stored: dict[str, Any],
    document: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if not has_active_migration(stored):
        return
    incoming_spec = document.get("spec")
    if not isinstance(incoming_spec, dict):
        return

    if "runtime" in incoming_spec and incoming_spec.get("runtime") != get_path(stored, ["spec", "runtime"]):
        errors.append(
            error(
                "spec.runtime",
                "cannot change runtime version while a migration is in progress",
                "invalid",
            )
        )

    incoming_migration = incoming_spec.get("migration")
    if (
        isinstance(incoming_migration, dict)
        and "strategy" in incoming_migration
        and incoming_migration.get("strategy") != get_path(stored, ["spec", "migration", "strategy"])
    ):
        errors.append(
            error(
                "spec.migration.strategy",
                "cannot change migration strategy while a migration is in progress",
                "invalid",
            )
        )


def start_runtime_migration(
    stored: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    source = get_path(stored, ["spec", "runtime"])
    target = get_path(candidate, ["spec", "runtime"])
    strategy = get_path(candidate, ["spec", "migration", "strategy"])
    stages = migration_stages(strategy)
    status = candidate.setdefault("status", {})
    set_condition(status, "Migration", "True", "")
    status["migration"] = {
        "sourceRuntime": source,
        "targetRuntime": target,
        "stage": stages[0],
    }
    update_status_stability(status)


def migration_stages(strategy: Any) -> list[str]:
    if isinstance(strategy, str):
        return MIGRATION_STAGES.get(strategy, MIGRATION_STAGES["FullStop"])
    return MIGRATION_STAGES["FullStop"]


def advance_runtime_migration(resource: dict[str, Any]) -> None:
    migration = get_active_migration(resource)
    if migration is None:
        return
    strategy = get_path(resource, ["spec", "migration", "strategy"])
    stages = migration_stages(strategy)
    stage = migration.get("stage")
    if stage not in stages:
        migration["stage"] = stages[0]
        update_status_stability(resource.setdefault("status", {}))
        return
    index = stages.index(stage)
    if index == len(stages) - 1:
        complete_runtime_migration(resource)
        return
    migration["stage"] = stages[index + 1]
    update_status_stability(resource.setdefault("status", {}))


def complete_runtime_migration(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    clear_condition(status, "Migration")
    status.pop("migration", None)
    update_status_stability(status)


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
    sort_conditions(status)
    update_status_stability(status)


def reconcile_connectivity_status(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    connection_details = mesh_connection_details(resource)
    if connection_details is None:
        status.pop("connectionDetails", None)
    else:
        status["connectionDetails"] = connection_details

    if get_path(resource, ["spec", "management", "enabled"]) is True:
        name = get_path(resource, ["metadata", "name"])
        status["managementConnectionDetails"] = {
            "host": f"{name}-admin",
            "port": MANAGEMENT_PORT,
            "protocol": "https",
        }
    else:
        status.pop("managementConnectionDetails", None)


def reconcile_mesh_policy_status(resource: dict[str, Any]) -> None:
    status = resource.setdefault("status", {})
    status["telemetryProbe"] = telemetry_probe(resource)
    if get_path(resource, ["spec", "regions"]) is not None:
        set_condition(status, "DiscoveryRelayReady", "False", "")
        set_condition(status, "RegionViewFormed", "False", "")
    else:
        clear_condition(status, "DiscoveryRelayReady")
        clear_condition(status, "RegionViewFormed")
    sort_conditions(status)
    update_status_stability(status)


def telemetry_probe(resource: dict[str, Any]) -> dict[str, Any]:
    tags = get_path(resource, ["metadata", "tags"])
    if not isinstance(tags, dict):
        tags = {}
    if tags.get("mesh.io/telemetry") == "false":
        return {"enabled": False}

    probe: dict[str, Any] = {"enabled": True}
    labels: dict[str, list[str]] = {}
    for tag, output_field in TELEMETRY_LABEL_TAGS.items():
        value = tags.get(tag)
        if isinstance(value, str):
            labels[output_field] = [item.strip() for item in value.split(",")]
    if labels:
        probe["labels"] = labels
    return probe


def mesh_connection_details(resource: dict[str, Any]) -> dict[str, Any] | None:
    exposure = get_path(resource, ["spec", "exposure"])
    if not isinstance(exposure, dict):
        return None
    name = get_path(resource, ["metadata", "name"])
    if not isinstance(name, str):
        name = ""
    exposure_type = exposure.get("type")
    if exposure_type == "Gateway":
        host = exposure.get("hostname")
        if not isinstance(host, str) or host == "":
            host = f"{name}.gateway.local"
        return {"host": host, "port": 443, "protocol": "https"}
    if exposure_type == "DirectPort":
        port = exposure.get("directPort", DEFAULT_EXPOSURE_PORT)
        return {"host": name, "port": port, "protocol": "https"}
    if exposure_type == "Balancer":
        port = exposure.get("port", DEFAULT_EXPOSURE_PORT)
        return {"host": f"{name}-external", "port": port, "protocol": "https"}
    return None


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
        status["instances"] = {"ready": 0, "starting": target, "stopped": 0}
        clear_condition(status, "GracefulShutdown")
        set_condition(status, "Scaling", "True", f"Scaling from 0 to {target}")
        candidate["_transition"] = {"type": "resume", "target": target}
    elif is_positive_int(old_instances) and new_instances == 0:
        status["state"] = "Stopped"
        status["desiredInstancesOnResume"] = old_instances
        status["instances"] = {"ready": 0, "starting": 0, "stopped": old_instances}
        set_condition(status, "GracefulShutdown", "True", "")
    elif is_positive_int(old_instances) and is_positive_int(new_instances) and new_instances > old_instances:
        status["state"] = "Running"
        status["instances"] = {
            "ready": old_instances,
            "starting": new_instances - old_instances,
            "stopped": 0,
        }
        set_condition(status, "Scaling", "True", f"Scaling from {old_instances} to {new_instances}")
        candidate["_transition"] = {"type": "scale", "target": new_instances}
    elif is_positive_int(old_instances) and is_positive_int(new_instances) and new_instances < old_instances:
        status["state"] = "Running"
        status["instances"] = {"ready": new_instances, "starting": 0, "stopped": 0}
        set_condition(status, "Scaling", "True", f"Scaling from {old_instances} to {new_instances}")
        candidate["_transition"] = {"type": "scale", "target": new_instances}
    else:
        status["state"] = "Running" if is_positive_int(new_instances) else "Stopped"
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
    update_status_stability(status)
    reconcile_connectivity_status(candidate)
    reconcile_mesh_policy_status(candidate)


def complete_pending_transition(resource: dict[str, Any]) -> bool:
    transition = resource.pop("_transition", None)
    initialize_status(resource)
    if not isinstance(transition, dict):
        return False

    target = transition.get("target")
    if not is_non_negative_int(target):
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
    sort_conditions(status)
    update_status_stability(status)
    reconcile_connectivity_status(resource)
    reconcile_mesh_policy_status(resource)
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
    canonicalize_resource_access(public)
    canonicalize_mesh_policies(public)
    reconcile_connectivity_status(public)
    reconcile_mesh_policy_status(public)

    storage = get_path(public, ["spec", "network", "storage"])
    if isinstance(storage, dict) and storage.get("ephemeral") is True:
        storage.pop("size", None)
    status = public.get("status")
    if isinstance(status, dict):
        sort_conditions(status)
        update_status_stability(status)
    return public


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


def condition_is(
    status: dict[str, Any],
    condition_type: str,
    condition_status: str,
) -> bool:
    return any(
        isinstance(condition, dict)
        and condition.get("type") == condition_type
        and condition.get("status") == condition_status
        for condition in status.get("conditions", [])
    )


def update_status_stability(status: dict[str, Any]) -> None:
    status["stable"] = (
        condition_is(status, "Healthy", "True")
        and condition_is(status, "PrechecksPassed", "True")
        and not condition_is(status, "GracefulShutdown", "True")
        and not condition_is(status, "Scaling", "True")
        and not condition_is(status, "Migration", "True")
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


def print_success(value: dict[str, Any], warnings: list[dict[str, str]] | None = None) -> None:
    if warnings:
        value = copy.deepcopy(value)
        value["warnings"] = sorted(warnings, key=lambda item: (item["field"], item["message"]))
    print_json(value)


def print_errors(errors: list[dict[str, str]]) -> None:
    print_json({"errors": sorted(errors, key=lambda item: (item["field"], item["type"]))})


if __name__ == "__main__":
    raise SystemExit(main())
