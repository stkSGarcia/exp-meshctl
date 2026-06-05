#!/usr/bin/env python3
import argparse
import copy
import json
import os
import re
import sys
import tempfile

import yaml

STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.json")
VAULT_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault_store.json")
TASK_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "task_store.json")
SNAPSHOT_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot_store.json")
RECOVERY_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovery_store.json")

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
RUNTIME_RE = re.compile(r"^\d+\.\d+\.\d+$")
MEMORY_UNITS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}
TRANSIENT_CONDITION_TYPES = {"Scaling"}
VALID_DIGEST_ALGORITHMS = {"SHA-256", "SHA-384", "SHA-512"}
VALID_ENCRYPTION_SOURCES = {"None", "Secret", "Service"}
VALID_CLIENT_MODES = {"None", "Authenticate", "Validate"}

RUNTIME_CATALOG = {
    "3.0.0": "deprecated",
    "3.0.1": "deprecated",
    "3.1.0": "skipped",
    "3.1.1": "supported",
    "4.0.0": "supported",
    "4.0.1": "supported",
    "4.1.0": "supported",
}

MIGRATION_STAGES = {
    "FullStop": ["Migrate"],
    "RollingPatch": ["Migrate"],
    "LiveMigration": ["Prepare", "Migrate"],
}

VALID_STRATEGIES = {"FullStop", "LiveMigration", "RollingPatch"}

DEFAULT_EXPOSURE_PORT = 8080
VALID_EXPOSURE_TYPES = {"Gateway", "DirectPort", "Balancer"}
EXPOSURE_ALLOWED_FIELDS = {
    "Gateway": {"hostname", "annotations"},
    "DirectPort": {"port", "directPort"},
    "Balancer": {"port"},
}


# --- Output helpers ---

def print_json(obj):
    print(json.dumps(obj))


def make_error(field, type_, message):
    return {"field": field, "type": type_, "message": message}


def error_out(errors):
    print_json({"errors": sorted(errors, key=lambda e: (e["field"], e["type"]))})


# --- Store ---

def load_store():
    if not os.path.exists(STORE_PATH):
        return {}
    with open(STORE_PATH) as f:
        return json.load(f)


def save_store(store):
    dir_ = os.path.dirname(STORE_PATH)
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(store, f)
        os.replace(tmp, STORE_PATH)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_vault_store():
    if not os.path.exists(VAULT_STORE_PATH):
        return {}
    with open(VAULT_STORE_PATH) as f:
        return json.load(f)


def save_vault_store(store):
    dir_ = os.path.dirname(VAULT_STORE_PATH)
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(store, f)
        os.replace(tmp, VAULT_STORE_PATH)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _load_json_store(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def _save_json_store(path, data):
    dir_ = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_task_store():
    return _load_json_store(TASK_STORE_PATH)


def save_task_store(store):
    _save_json_store(TASK_STORE_PATH, store)


def load_snapshot_store():
    return _load_json_store(SNAPSHOT_STORE_PATH)


def save_snapshot_store(store):
    _save_json_store(SNAPSHOT_STORE_PATH, store)


def load_recovery_store():
    return _load_json_store(RECOVERY_STORE_PATH)


def save_recovery_store(store):
    _save_json_store(RECOVERY_STORE_PATH, store)


# --- YAML loader ---

def load_yaml_file(path):
    try:
        with open(path) as f:
            doc = yaml.safe_load(f)
    except FileNotFoundError:
        return None, [make_error("", "parse", f"file not found: {path}")]
    except yaml.YAMLError as e:
        return None, [make_error("", "parse", f"YAML parse error: {e}")]
    except OSError as e:
        return None, [make_error("", "parse", f"cannot read file: {e}")]

    if not isinstance(doc, dict):
        return None, [make_error("", "parse", "document must be a YAML mapping")]

    return doc, []


# --- Quantity parsers ---

def parse_memory_quantity(value):
    if not isinstance(value, str):
        return None
    for suffix, mult in MEMORY_UNITS.items():
        if value.endswith(suffix):
            num = value[: -len(suffix)]
            return int(num) * mult if re.fullmatch(r"\d+", num) else None
    return int(value) if re.fullmatch(r"\d+", value) else None


def parse_cpu_quantity(value):
    if not isinstance(value, str):
        return None
    if value.endswith("m"):
        num = value[:-1]
        return int(num) if re.fullmatch(r"\d+", num) else None
    return int(value) * 1000 if re.fullmatch(r"\d+", value) else None


def parse_semver(v):
    parts = v.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


# --- autoScaling scanner ---

def find_autoscaling_paths(obj, path):
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path else k
            if k == "autoScaling":
                results.append(child)
            else:
                results.extend(find_autoscaling_paths(v, child))
    return results


# --- Storage output formatter (task 1.4) ---

def format_storage(storage):
    """Output only ephemeral when ephemeral=True; include both ephemeral and size otherwise."""
    if storage.get("ephemeral"):
        return {"ephemeral": True}
    out = {"ephemeral": False, "size": storage["size"]}
    if storage.get("className") is not None:
        out["className"] = storage["className"]
    return out


# --- Condition helpers ---

def set_condition(conditions, type_, status, message):
    updated = [c for c in conditions if c["type"] != type_]
    updated.append({"type": type_, "status": status, "message": message})
    return sorted(updated, key=lambda c: c["type"])


def remove_condition(conditions, type_):
    return sorted([c for c in conditions if c["type"] != type_], key=lambda c: c["type"])


def compute_stable(conditions):
    cond_map = {c["type"]: c["status"] for c in conditions}
    if cond_map.get("Healthy") != "True":
        return False
    if cond_map.get("PrechecksPassed") != "True":
        return False
    if cond_map.get("GracefulShutdown", "False") == "True":
        return False
    if cond_map.get("Scaling", "False") == "True":
        return False
    if cond_map.get("Migration", "False") == "True":
        return False
    return True


# --- Status helpers (task 2.1) ---

def build_initial_status(instances):
    conditions = sorted([
        {"type": "Healthy", "status": "True", "message": ""},
        {"type": "PrechecksPassed", "status": "True", "message": ""},
    ], key=lambda c: c["type"])
    return {
        "state": "Running",
        "stable": compute_stable(conditions),
        "instances": {"ready": instances, "starting": 0, "stopped": 0},
        "conditions": conditions,
    }


# --- Connection details ---

def compute_connection_details(name, exposure):
    exp_type = exposure.get("type")
    if exp_type == "Gateway":
        host = exposure.get("hostname") or name
        port = 443
    elif exp_type == "DirectPort":
        host = name
        port = exposure.get("directPort") or DEFAULT_EXPOSURE_PORT
    else:  # Balancer
        host = f"{name}-external"
        port = exposure.get("port") or DEFAULT_EXPOSURE_PORT
    return {"host": host, "port": port, "protocol": "https"}


# --- Resource output formatter ---

def format_resource_for_output(resource):
    """Apply output rules: storage format, hide desiredInstancesOnResume when running."""
    out = copy.deepcopy(resource)
    network = out.get("spec", {}).get("network")
    if network and "storage" in network:
        network["storage"] = format_storage(network["storage"])
    status = out.get("status", {})
    if status.get("state") != "Stopped":
        status.pop("desiredInstancesOnResume", None)
    name = out.get("metadata", {}).get("name", "")
    exposure = out.get("spec", {}).get("exposure")
    if exposure:
        status["connectionDetails"] = compute_connection_details(name, exposure)
    if out.get("spec", {}).get("management", {}).get("enabled", False):
        status["managementConnectionDetails"] = {
            "host": f"{name}-admin",
            "port": 9990,
            "protocol": "https",
        }
    out["status"] = status
    return out


# --- Validation + default application (tasks 1.1-1.5, 6.2, 6.3) ---

def validate_and_build(doc, is_update=False):
    errors = []
    warnings = []

    if "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")], []

    metadata = doc["metadata"]
    spec = doc["spec"]

    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    # metadata.name
    name = None
    raw_name = metadata.get("name")
    if raw_name is None or raw_name == "":
        errors.append(make_error("metadata.name", "required", "name is required and must not be empty"))
    elif not isinstance(raw_name, str):
        errors.append(make_error("metadata.name", "required", "name must be a non-empty string"))
    elif not NAME_RE.match(raw_name):
        errors.append(make_error(
            "metadata.name", "invalid",
            "name must be lowercase alphanumeric with interior hyphens only, minimum 2 characters",
        ))
    else:
        name = raw_name

    # forbidden autoScaling under spec
    for fp in find_autoscaling_paths(spec, "spec"):
        errors.append(make_error(fp, "forbidden", f"field '{fp}' is not allowed"))

    # spec.instances
    instances = None
    raw_instances = spec.get("instances")
    if raw_instances is None:
        if not is_update:
            instances = 1
    elif isinstance(raw_instances, bool):
        errors.append(make_error("spec.instances", "invalid", "instances must be a positive integer"))
    elif not isinstance(raw_instances, int):
        errors.append(make_error("spec.instances", "invalid", "instances must be a positive integer"))
    elif raw_instances < 0:
        errors.append(make_error("spec.instances", "invalid", "instances must be a positive integer"))
    elif raw_instances == 0 and not is_update:
        errors.append(make_error("spec.instances", "invalid", "instances must be a positive integer"))
    else:
        instances = raw_instances

    # spec.runtime
    runtime = None
    has_runtime = "runtime" in spec
    if has_runtime:
        raw_runtime = spec["runtime"]
        if not isinstance(raw_runtime, str) or not RUNTIME_RE.match(raw_runtime):
            errors.append(make_error(
                "spec.runtime", "invalid",
                "runtime must be in major.minor.patch format with non-negative integers",
            ))
        else:
            runtime = raw_runtime
            catalog_status = RUNTIME_CATALOG.get(runtime)
            if catalog_status is None:
                errors.append(make_error(
                    "spec.runtime", "invalid",
                    f"runtime version '{runtime}' is not in the supported catalog",
                ))
                runtime = None
            elif catalog_status == "skipped":
                errors.append(make_error(
                    "spec.runtime", "invalid",
                    f"runtime version '{runtime}' is skipped and cannot be targeted",
                ))
                runtime = None
            elif catalog_status == "deprecated":
                warnings.append({"field": "spec.runtime", "message": f"runtime version '{runtime}' is deprecated"})

    raw_resources = spec.get("resources")
    has_resources = isinstance(raw_resources, dict)

    # spec.resources.memory
    has_memory = has_resources and "memory" in raw_resources
    memory = None
    if not has_memory:
        memory = {"limit": "1Gi", "request": "1Gi"}
    else:
        raw_memory = raw_resources["memory"]
        if not isinstance(raw_memory, dict):
            errors.append(make_error("spec.resources.memory.limit", "required", "memory.limit is required"))
        else:
            mem_limit_str = raw_memory.get("limit")
            mem_req_str = raw_memory.get("request")

            if mem_limit_str is None:
                errors.append(make_error("spec.resources.memory.limit", "required", "memory.limit is required"))
            else:
                if not isinstance(mem_limit_str, str):
                    mem_limit_str = str(mem_limit_str)
                mem_limit_val = parse_memory_quantity(mem_limit_str)
                if mem_limit_val is None:
                    errors.append(make_error(
                        "spec.resources.memory.limit", "invalid",
                        f"invalid memory quantity: {mem_limit_str!r}",
                    ))
                else:
                    if mem_req_str is None:
                        mem_req_str = mem_limit_str
                        mem_req_val = mem_limit_val
                    else:
                        if not isinstance(mem_req_str, str):
                            mem_req_str = str(mem_req_str)
                        mem_req_val = parse_memory_quantity(mem_req_str)
                        if mem_req_val is None:
                            errors.append(make_error(
                                "spec.resources.memory.request", "invalid",
                                f"invalid memory quantity: {mem_req_str!r}",
                            ))
                            mem_req_val = None
                        elif mem_req_val > mem_limit_val:
                            errors.append(make_error(
                                "spec.resources.memory.request", "invalid",
                                "memory request must not exceed limit",
                            ))
                            mem_req_val = None

                    if mem_req_val is not None:
                        memory = {"limit": mem_limit_str, "request": mem_req_str}

    # spec.resources.cpu
    has_cpu = has_resources and "cpu" in raw_resources
    cpu = None
    if has_cpu:
        raw_cpu = raw_resources["cpu"]
        if not isinstance(raw_cpu, dict):
            errors.append(make_error("spec.resources.cpu.limit", "required", "cpu.limit is required"))
        else:
            cpu_limit_str = raw_cpu.get("limit")
            cpu_req_str = raw_cpu.get("request")

            if cpu_limit_str is None:
                errors.append(make_error("spec.resources.cpu.limit", "required", "cpu.limit is required"))
            else:
                if not isinstance(cpu_limit_str, str):
                    cpu_limit_str = str(cpu_limit_str)
                cpu_limit_val = parse_cpu_quantity(cpu_limit_str)
                if cpu_limit_val is None:
                    errors.append(make_error(
                        "spec.resources.cpu.limit", "invalid",
                        f"invalid CPU quantity: {cpu_limit_str!r}",
                    ))
                else:
                    if cpu_req_str is None:
                        cpu_req_str = cpu_limit_str
                        cpu_req_val = cpu_limit_val
                    else:
                        if not isinstance(cpu_req_str, str):
                            cpu_req_str = str(cpu_req_str)
                        cpu_req_val = parse_cpu_quantity(cpu_req_str)
                        if cpu_req_val is None:
                            errors.append(make_error(
                                "spec.resources.cpu.request", "invalid",
                                f"invalid CPU quantity: {cpu_req_str!r}",
                            ))
                            cpu_req_val = None
                        elif cpu_req_val > cpu_limit_val:
                            errors.append(make_error(
                                "spec.resources.cpu.request", "invalid",
                                "CPU request must not exceed limit",
                            ))
                            cpu_req_val = None

                    if cpu_req_val is not None:
                        cpu = {"limit": cpu_limit_str, "request": cpu_req_str}

    # spec.access
    raw_access = spec.get("access")
    has_access = isinstance(raw_access, dict)
    raw_auth = raw_access.get("authentication") if has_access else None

    auth_enabled = True
    if isinstance(raw_auth, dict) and "enabled" in raw_auth:
        auth_enabled = raw_auth["enabled"]

    # spec.access.authentication.digestAlgorithm
    digest_algorithm = None
    has_digest = isinstance(raw_auth, dict) and "digestAlgorithm" in raw_auth
    if has_digest:
        raw_digest = raw_auth["digestAlgorithm"]
        if not auth_enabled:
            errors.append(make_error(
                "spec.access.authentication.digestAlgorithm", "forbidden",
                "digestAlgorithm must be absent when authentication is disabled",
            ))
        elif raw_digest not in VALID_DIGEST_ALGORITHMS:
            errors.append(make_error(
                "spec.access.authentication.digestAlgorithm", "invalid",
                "digestAlgorithm must be one of SHA-256, SHA-384, SHA-512",
            ))
        else:
            digest_algorithm = raw_digest
    elif auth_enabled:
        digest_algorithm = "SHA-256"

    # spec.access.credentialRef
    credential_ref = None
    has_credential_ref = has_access and "credentialRef" in raw_access
    if has_credential_ref:
        if not auth_enabled:
            errors.append(make_error(
                "spec.access.credentialRef", "forbidden",
                "credentialRef must be absent when authentication is disabled",
            ))
        else:
            credential_ref = raw_access["credentialRef"]

    # spec.access.permissions
    raw_permissions = raw_access.get("permissions") if has_access else None
    permissions_enabled = False
    if isinstance(raw_permissions, dict) and "enabled" in raw_permissions:
        permissions_enabled = bool(raw_permissions["enabled"])

    roles = None
    if permissions_enabled:
        raw_roles = raw_permissions.get("roles") if isinstance(raw_permissions, dict) else None
        if not isinstance(raw_roles, list) or len(raw_roles) == 0:
            errors.append(make_error(
                "spec.access.permissions.roles", "required",
                "roles is required and must not be empty when permissions are enabled",
            ))
        else:
            seen_role_names = {}
            for i, role in enumerate(raw_roles):
                role_dict = role if isinstance(role, dict) else {}
                role_name = role_dict.get("name")
                role_perms = role_dict.get("permissions")
                if not isinstance(role_name, str) or not role_name:
                    errors.append(make_error(
                        f"spec.access.permissions.roles[{i}].name", "required",
                        "role name is required and must not be empty",
                    ))
                else:
                    seen_role_names.setdefault(role_name, []).append(i)
                if not isinstance(role_perms, list) or len(role_perms) == 0:
                    errors.append(make_error(
                        f"spec.access.permissions.roles[{i}].permissions", "required",
                        "role permissions is required and must be a non-empty array",
                    ))
            for rname, indices in seen_role_names.items():
                if len(indices) > 1:
                    errors.append(make_error(
                        "spec.access.permissions.roles", "duplicate",
                        f"duplicate role name: {rname!r}",
                    ))
            roles = raw_roles

    # spec.access.encryption
    raw_encryption = raw_access.get("encryption") if has_access else None
    has_encryption = isinstance(raw_encryption, dict)

    enc_source = "None"
    enc_client_mode = "None"
    enc_cert_ref = None
    enc_cert_service_ref = None

    if has_encryption:
        raw_source = raw_encryption.get("source", "None")
        if raw_source not in VALID_ENCRYPTION_SOURCES:
            errors.append(make_error(
                "spec.access.encryption.source", "invalid",
                "encryption.source must be one of None, Secret, Service",
            ))
        else:
            enc_source = raw_source

        raw_client_mode = raw_encryption.get("clientMode", "None")
        if raw_client_mode not in VALID_CLIENT_MODES:
            errors.append(make_error(
                "spec.access.encryption.clientMode", "invalid",
                "encryption.clientMode must be one of None, Authenticate, Validate",
            ))
        else:
            enc_client_mode = raw_client_mode

        if raw_source in VALID_ENCRYPTION_SOURCES:
            has_cert_ref = "certRef" in raw_encryption
            has_cert_service_ref = "certServiceRef" in raw_encryption

            if raw_source == "Secret":
                if not has_cert_ref:
                    errors.append(make_error(
                        "spec.access.encryption.certRef", "required",
                        "certRef is required when encryption.source is 'Secret'",
                    ))
                else:
                    enc_cert_ref = raw_encryption["certRef"]
                if has_cert_service_ref:
                    errors.append(make_error(
                        "spec.access.encryption.certServiceRef", "forbidden",
                        "certServiceRef must be absent when encryption.source is 'Secret'",
                    ))
            elif raw_source == "Service":
                if not has_cert_service_ref:
                    errors.append(make_error(
                        "spec.access.encryption.certServiceRef", "required",
                        "certServiceRef is required when encryption.source is 'Service'",
                    ))
                else:
                    enc_cert_service_ref = raw_encryption["certServiceRef"]
                if has_cert_ref:
                    errors.append(make_error(
                        "spec.access.encryption.certRef", "forbidden",
                        "certRef must be absent when encryption.source is 'Service'",
                    ))
            else:  # raw_source == "None"
                if has_cert_ref:
                    errors.append(make_error(
                        "spec.access.encryption.certRef", "forbidden",
                        "certRef must be absent when encryption.source is 'None'",
                    ))
                if has_cert_service_ref:
                    errors.append(make_error(
                        "spec.access.encryption.certServiceRef", "forbidden",
                        "certServiceRef must be absent when encryption.source is 'None'",
                    ))
                if raw_client_mode in VALID_CLIENT_MODES and raw_client_mode != "None":
                    errors.append(make_error(
                        "spec.access.encryption.clientMode", "invalid",
                        "clientMode must be 'None' when encryption.source is 'None'",
                    ))

    # spec.migration.strategy
    strategy = "FullStop"
    raw_migration = spec.get("migration")
    if isinstance(raw_migration, dict) and "strategy" in raw_migration:
        raw_strategy = raw_migration["strategy"]
        if raw_strategy not in VALID_STRATEGIES:
            errors.append(make_error(
                "spec.migration.strategy", "invalid",
                f"migration.strategy must be one of FullStop, LiveMigration, RollingPatch, got {raw_strategy!r}",
            ))
            strategy = None
        else:
            strategy = raw_strategy

    # LiveMigration region restriction
    if strategy == "LiveMigration":
        raw_regions = spec.get("regions")
        if raw_regions:
            errors.append(make_error(
                "spec.migration.strategy", "invalid",
                "LiveMigration strategy is not supported with multi-region topology",
            ))

    # spec.network.storage (tasks 1.2, 6.3)
    raw_network = spec.get("network")
    has_network = isinstance(raw_network, dict)
    raw_storage_block = raw_network.get("storage") if has_network else None
    has_storage_block = isinstance(raw_storage_block, dict)

    storage_size = "1Gi"
    storage_ephemeral = False
    storage_class_name = None

    if has_storage_block:
        raw_size = raw_storage_block.get("size")
        if raw_size is None:
            pass  # keep default "1Gi"
        else:
            size_str = raw_size if isinstance(raw_size, str) else str(raw_size)
            if parse_memory_quantity(size_str) is None:
                errors.append(make_error(
                    "spec.network.storage.size", "invalid",
                    f"invalid storage size: {size_str!r}",
                ))
            else:
                storage_size = size_str

        storage_ephemeral = bool(raw_storage_block.get("ephemeral", False))

        raw_class = raw_storage_block.get("className")
        if raw_class is not None:
            storage_class_name = str(raw_class)

    storage = {"size": storage_size, "ephemeral": storage_ephemeral}
    if storage_class_name is not None:
        storage["className"] = storage_class_name

    # spec.network.replicationFactor (tasks 1.3, 6.2)
    rf = None
    has_rf = has_network and "replicationFactor" in raw_network

    if has_rf:
        raw_rf = raw_network["replicationFactor"]
        if isinstance(raw_rf, bool) or not isinstance(raw_rf, int) or raw_rf < 1:
            errors.append(make_error(
                "spec.network.replicationFactor", "invalid",
                "replicationFactor must be a positive integer",
            ))
        else:
            rf = raw_rf
    else:
        # compute default: min(instances, 3); only meaningful on create
        if instances is not None and isinstance(instances, int) and instances >= 1:
            rf = min(instances, 3)
        else:
            rf = 1

    # post-merge check: rf <= instances (only when instances > 0)
    if rf is not None and instances is not None and isinstance(instances, int) and instances > 0:
        if rf > instances:
            errors.append(make_error(
                "spec.network.replicationFactor", "invalid",
                f"replicationFactor {rf} exceeds instances {instances}",
            ))
            rf = None

    # spec.exposure (optional)
    raw_exposure = spec.get("exposure")
    has_exposure = raw_exposure is not None
    exposure_out = None

    if has_exposure:
        if not isinstance(raw_exposure, dict):
            errors.append(make_error("spec.exposure.type", "required", "exposure.type is required"))
        else:
            exp_type = raw_exposure.get("type")
            if exp_type is None or exp_type == "":
                errors.append(make_error("spec.exposure.type", "required", "exposure.type is required"))
            elif exp_type not in VALID_EXPOSURE_TYPES:
                errors.append(make_error(
                    "spec.exposure.type", "invalid",
                    "exposure.type must be one of Gateway, DirectPort, Balancer",
                ))
            else:
                allowed = EXPOSURE_ALLOWED_FIELDS[exp_type]
                for field in raw_exposure:
                    if field != "type" and field not in allowed:
                        fp = f"spec.exposure.{field}"
                        errors.append(make_error(fp, "forbidden", f"field '{fp}' is not allowed for exposure type '{exp_type}'"))

                exposure_out = {"type": exp_type}
                if exp_type == "Gateway":
                    if raw_exposure.get("hostname") is not None:
                        exposure_out["hostname"] = raw_exposure["hostname"]
                    if isinstance(raw_exposure.get("annotations"), dict):
                        exposure_out["annotations"] = raw_exposure["annotations"]
                elif exp_type == "DirectPort":
                    if raw_exposure.get("port") is not None:
                        exposure_out["port"] = raw_exposure["port"]
                    if raw_exposure.get("directPort") is not None:
                        exposure_out["directPort"] = raw_exposure["directPort"]
                elif exp_type == "Balancer":
                    if raw_exposure.get("port") is not None:
                        exposure_out["port"] = raw_exposure["port"]

    # spec.management.enabled (default false, immutable after create)
    raw_management = spec.get("management")
    management_enabled = False
    if isinstance(raw_management, dict) and "enabled" in raw_management:
        management_enabled = bool(raw_management["enabled"])

    if errors:
        return None, errors, []

    if auth_enabled:
        auth_out = {"enabled": True, "digestAlgorithm": digest_algorithm}
    else:
        auth_out = {"enabled": False}

    permissions_out = {"enabled": permissions_enabled}
    if permissions_enabled and roles is not None:
        permissions_out["roles"] = roles

    encryption_out = {"source": enc_source, "clientMode": enc_client_mode}
    if enc_source == "Secret":
        encryption_out["certRef"] = enc_cert_ref
    elif enc_source == "Service":
        encryption_out["certServiceRef"] = enc_cert_service_ref

    access_out = {"authentication": auth_out, "permissions": permissions_out, "encryption": encryption_out}
    if credential_ref is not None:
        access_out["credentialRef"] = credential_ref

    out_spec = {
        "instances": instances,
        "resources": {"memory": memory},
        "access": access_out,
        "migration": {"strategy": strategy},
        "management": {"enabled": management_enabled},
        "network": {
            "storage": storage,
            "replicationFactor": rf,
        },
    }
    if has_runtime:
        out_spec["runtime"] = runtime
    if has_cpu:
        out_spec["resources"]["cpu"] = cpu
    if exposure_out is not None:
        out_spec["exposure"] = exposure_out

    return {"metadata": {"name": name}, "spec": out_spec}, [], warnings


# --- Merge helpers (tasks 3.1, 3.2) ---

def deep_merge(stored, update):
    """Recursively merge update into stored; None values in update keep stored value."""
    result = dict(stored)
    for k, v in update.items():
        if v is None:
            pass
        elif isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def check_immutable(stored_spec, merged_spec):
    """Return immutable errors for fields that changed after creation."""
    errors = []
    stored_size = (stored_spec.get("network") or {}).get("storage", {}).get("size")
    if stored_size is not None:
        merged_size = (merged_spec.get("network") or {}).get("storage", {}).get("size")
        if merged_size != stored_size:
            errors.append(make_error(
                "spec.network.storage.size", "immutable",
                "field 'spec.network.storage.size' is immutable after creation",
            ))
    stored_mgmt = (stored_spec.get("management") or {}).get("enabled", False)
    merged_mgmt = (merged_spec.get("management") or {}).get("enabled", False)
    if stored_mgmt != merged_mgmt:
        errors.append(make_error(
            "spec.management.enabled", "immutable",
            "field 'spec.management.enabled' is immutable after creation",
        ))
    return errors


# --- Vault validation ---

def validate_vault(doc, mesh_store=None):
    errors = []

    if "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    metadata = doc["metadata"]
    spec = doc["spec"]

    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    # metadata.name
    name = None
    raw_name = metadata.get("name")
    if raw_name is None or raw_name == "":
        errors.append(make_error("metadata.name", "required", "name is required and must not be empty"))
    elif not isinstance(raw_name, str):
        errors.append(make_error("metadata.name", "required", "name must be a non-empty string"))
    elif not NAME_RE.match(raw_name):
        errors.append(make_error(
            "metadata.name", "invalid",
            "name must be lowercase alphanumeric with interior hyphens only, minimum 2 characters",
        ))
    else:
        name = raw_name

    # spec.meshRef
    mesh_ref = None
    raw_mesh_ref = spec.get("meshRef")
    if raw_mesh_ref is None or raw_mesh_ref == "":
        errors.append(make_error("spec.meshRef", "required", "meshRef is required"))
    elif not isinstance(raw_mesh_ref, str):
        errors.append(make_error("spec.meshRef", "required", "meshRef must be a non-empty string"))
    else:
        mesh_ref = raw_mesh_ref
        if mesh_store is not None and mesh_ref not in mesh_store:
            errors.append(make_error(
                "spec.meshRef", "invalid",
                f"mesh '{mesh_ref}' not found",
            ))
            mesh_ref = None

    # spec.vaultName (default to metadata.name)
    vault_name = spec.get("vaultName") or name

    # spec.updatePolicy (default "retain")
    update_policy = spec.get("updatePolicy")
    if update_policy is None:
        update_policy = "retain"
    elif update_policy not in ("retain", "recreate"):
        errors.append(make_error(
            "spec.updatePolicy", "invalid",
            f"updatePolicy must be 'retain' or 'recreate', got {update_policy!r}",
        ))
        update_policy = None

    # template exclusivity
    template = spec.get("template")
    template_ref = spec.get("templateRef")
    if template is not None and template_ref is not None:
        errors.append(make_error(
            "spec.template", "invalid",
            "spec.template and spec.templateRef are mutually exclusive",
        ))

    if errors:
        return None, errors

    out_spec = {
        "meshRef": mesh_ref,
        "vaultName": vault_name,
        "updatePolicy": update_policy,
    }
    if template is not None:
        out_spec["template"] = template
    if template_ref is not None:
        out_spec["templateRef"] = template_ref

    return {"metadata": {"name": name}, "spec": out_spec}, []


# --- Vault status helper ---

def build_vault_status(mesh):
    stable = mesh.get("status", {}).get("stable", False)
    ready_status = "True" if stable else "False"
    return {
        "state": "Ready" if stable else "Pending",
        "conditions": [{"type": "Ready", "status": ready_status, "message": ""}],
    }


# --- Lifecycle helpers (tasks 4.1, 4.2) ---

def detect_lifecycle(old_instances, new_instances, old_conditions):
    has_graceful = any(c["type"] == "GracefulShutdown" for c in old_conditions)
    if has_graceful:
        return "resume" if new_instances > 0 else "none"
    if new_instances == 0:
        return "stop"
    if new_instances > old_instances:
        return "scale_up"
    if new_instances < old_instances:
        return "scale_down"
    return "none"


def apply_lifecycle(transition, old_status, old_instances, new_instances):
    status = copy.deepcopy(old_status)
    conditions = status.get("conditions", [])

    if transition == "scale_up":
        conditions = set_condition(
            conditions, "Scaling", "True",
            f"scaling from {old_instances} to {new_instances} instances",
        )
        status["instances"] = {"ready": old_instances, "starting": new_instances - old_instances, "stopped": 0}
        status["state"] = "Running"
        status["stable"] = False

    elif transition == "scale_down":
        conditions = set_condition(conditions, "Scaling", "True", "scaling down")
        status["instances"] = {"ready": old_instances, "starting": 0, "stopped": 0}
        status["state"] = "Running"
        status["stable"] = False

    elif transition == "stop":
        conditions = set_condition(conditions, "GracefulShutdown", "True", "")
        status["instances"] = {"ready": 0, "starting": 0, "stopped": old_instances}
        status["state"] = "Stopped"
        migration_active = any(c["type"] == "Migration" and c["status"] == "True" for c in conditions)
        status["stable"] = not migration_active
        status["desiredInstancesOnResume"] = old_instances

    elif transition == "resume":
        conditions = remove_condition(conditions, "GracefulShutdown")
        conditions = set_condition(
            conditions, "Scaling", "True",
            f"resuming with {new_instances} instances",
        )
        status["instances"] = {"ready": 0, "starting": new_instances, "stopped": 0}
        status["state"] = "Running"
        status["stable"] = False
        status.pop("desiredInstancesOnResume", None)

    status["conditions"] = conditions
    return status


# --- Command handlers ---

def cmd_create(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    result, errs, warnings = validate_and_build(doc)
    if errs:
        error_out(errs)
        return

    name = result["metadata"]["name"]
    store = load_store()
    if name in store:
        error_out([make_error("metadata.name", "duplicate", f"mesh '{name}' already exists")])
        return

    # task 2.2: enrich status
    result["status"] = build_initial_status(result["spec"]["instances"])

    store[name] = result
    save_store(store)
    output = format_resource_for_output(result)
    if warnings:
        output["warnings"] = sorted(warnings, key=lambda w: (w["field"], w["message"]))
    print_json(output)


def cmd_list(_args):
    store = load_store()
    # task 2.4: list returns summary with state only
    items = sorted(
        [{"name": r["metadata"]["name"], "status": {"state": r["status"]["state"]}} for r in store.values()],
        key=lambda x: x["name"],
    )
    print_json(items)


def cmd_describe(args):
    store = load_store()
    if args.name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{args.name}' not found")])
        return

    # task 2.3: strip transient Scaling and resolve instance counts
    resource = copy.deepcopy(store[args.name])
    status = resource["status"]
    conditions = status.get("conditions", [])
    had_scaling = any(c["type"] == "Scaling" for c in conditions)
    status["conditions"] = [c for c in conditions if c["type"] not in TRANSIENT_CONDITION_TYPES]

    if had_scaling and status.get("state") == "Running":
        n = resource["spec"]["instances"]
        status["instances"] = {"ready": n, "starting": 0, "stopped": 0}
        status["stable"] = True

    print_json(format_resource_for_output(resource))


def cmd_delete(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return
    vault_store = load_vault_store()
    dependent = sorted(v["metadata"]["name"] for v in vault_store.values() if v["spec"]["meshRef"] == name)
    if dependent:
        error_out([make_error(
            "metadata.name", "conflict",
            f"mesh '{name}' is referenced by vault(s): {', '.join(dependent)}",
        )])
        return
    del store[name]
    save_store(store)
    print_json({"message": f"mesh '{name}' deleted", "metadata": {"name": name}})


def cmd_update(args):  # tasks 3.3, 4.3
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    if not isinstance(doc, dict) or "metadata" not in doc:
        error_out([make_error("", "parse", "document must have 'metadata' and 'spec' keys")])
        return

    metadata = doc.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    raw_name = metadata.get("name")
    if not raw_name:
        error_out([make_error("metadata.name", "required", "name is required")])
        return

    store = load_store()
    if raw_name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{raw_name}' not found")])
        return

    stored = store[raw_name]
    stored_conditions = stored["status"].get("conditions", [])
    had_scaling = any(c["type"] == "Scaling" for c in stored_conditions)

    # Resolve transient state before merging
    resolved_conditions = [c for c in stored_conditions if c["type"] not in TRANSIENT_CONDITION_TYPES]
    resolved_status = copy.deepcopy(stored["status"])
    resolved_status["conditions"] = resolved_conditions
    if had_scaling and resolved_status.get("state") == "Running":
        n = stored["spec"]["instances"]
        resolved_status["instances"] = {"ready": n, "starting": 0, "stopped": 0}
        resolved_status["stable"] = True

    old_instances = stored["spec"]["instances"]
    has_graceful = any(c["type"] == "GracefulShutdown" for c in resolved_conditions)

    update_spec = doc.get("spec") or {}
    if not isinstance(update_spec, dict):
        update_spec = {}

    # Track whether instances was explicitly provided (for resume-with-omitted logic)
    raw_instances_in_update = update_spec.get("instances")

    # Active-migration guards: reject runtime/strategy changes while Migration is active
    has_active_migration = any(
        c["type"] == "Migration" and c["status"] == "True"
        for c in stored.get("status", {}).get("conditions", [])
    )
    if has_active_migration:
        migration_errors = []
        raw_update_runtime = update_spec.get("runtime")
        if raw_update_runtime is not None and raw_update_runtime != stored["spec"].get("runtime"):
            migration_errors.append(make_error(
                "spec.runtime", "invalid",
                "cannot change runtime version while a migration is in progress",
            ))
        raw_update_migration = update_spec.get("migration")
        if isinstance(raw_update_migration, dict):
            raw_update_strategy = raw_update_migration.get("strategy")
            if raw_update_strategy is not None and raw_update_strategy != stored["spec"]["migration"]["strategy"]:
                migration_errors.append(make_error(
                    "spec.migration.strategy", "invalid",
                    "cannot change migration strategy while a migration is in progress",
                ))
        if migration_errors:
            error_out(migration_errors)
            return

    # Deep merge spec
    merged_spec = deep_merge(stored["spec"], update_spec)

    # Resume with omitted/null instances: use desiredInstancesOnResume as target
    if has_graceful and raw_instances_in_update is None:
        desired = stored["status"].get("desiredInstancesOnResume")
        if desired:
            merged_spec["instances"] = desired

    # Check immutables before validation
    imm_errors = check_immutable(stored["spec"], merged_spec)
    if imm_errors:
        error_out(imm_errors)
        return

    merged_doc = {"metadata": {"name": raw_name}, "spec": merged_spec}

    result, errs, warnings = validate_and_build(merged_doc, is_update=True)
    if errs:
        error_out(errs)
        return

    # Version-change detection and constraints
    old_runtime = stored["spec"].get("runtime")
    new_runtime = result["spec"].get("runtime")
    is_version_change = (
        old_runtime is not None and new_runtime is not None and old_runtime != new_runtime
    )

    version_errors = []
    if is_version_change:
        old_sv = parse_semver(old_runtime)
        new_sv = parse_semver(new_runtime)
        strategy = result["spec"]["migration"]["strategy"]

        # Downgrade check — all strategies
        if new_sv < old_sv:
            version_errors.append(make_error(
                "spec.runtime", "invalid",
                f"version downgrade from '{old_runtime}' to '{new_runtime}' is not allowed",
            ))

        # RollingPatch-specific checks — evaluated independently
        if strategy == "RollingPatch":
            if (old_sv[0], old_sv[1]) != (new_sv[0], new_sv[1]):
                version_errors.append(make_error(
                    "spec.runtime", "invalid",
                    "RollingPatch requires source and target to share the same major and minor version",
                ))
            if new_sv[0] < 4:
                version_errors.append(make_error(
                    "spec.runtime", "invalid",
                    "RollingPatch requires target major version to be at least 4",
                ))

    if version_errors:
        error_out(version_errors)
        return

    new_instances = result["spec"]["instances"]
    transition = detect_lifecycle(old_instances, new_instances, resolved_conditions)
    new_status = apply_lifecycle(transition, resolved_status, old_instances, new_instances)

    # Start migration on version change
    if is_version_change:
        strategy = result["spec"]["migration"]["strategy"]
        stages = MIGRATION_STAGES[strategy]
        new_status["conditions"] = set_condition(
            new_status.get("conditions", []),
            "Migration", "True", "",
        )
        new_status["migration"] = {
            "sourceRuntime": old_runtime,
            "targetRuntime": new_runtime,
            "stage": stages[0],
        }
        new_status["stable"] = False

    result["status"] = new_status
    store[raw_name] = result
    save_store(store)
    output = format_resource_for_output(result)
    if warnings:
        output["warnings"] = sorted(warnings, key=lambda w: (w["field"], w["message"]))
    print_json(output)


def cmd_migrate(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return

    resource = copy.deepcopy(store[name])
    status = resource.get("status", {})
    migration = status.get("migration")

    if migration is None:
        error_out([make_error("status.migration", "invalid", f"no active migration for mesh '{name}'")])
        return

    strategy = resource["spec"]["migration"]["strategy"]
    stages = MIGRATION_STAGES[strategy]
    current_stage = migration["stage"]
    conditions = status.get("conditions", [])

    if current_stage == stages[-1]:
        # Final stage — complete the migration
        conditions = remove_condition(conditions, "Migration")
        status["conditions"] = conditions
        del status["migration"]
        status["stable"] = compute_stable(conditions)
    else:
        # Advance to next stage
        current_idx = stages.index(current_stage)
        migration["stage"] = stages[current_idx + 1]
        status["migration"] = migration

    resource["status"] = status
    store[name] = resource
    save_store(store)
    print_json(format_resource_for_output(resource))


def cmd_rollback(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return

    resource = copy.deepcopy(store[name])
    status = resource.get("status", {})
    migration = status.get("migration")

    if migration is None:
        error_out([make_error("status.migration", "invalid", f"no active migration for mesh '{name}'")])
        return

    strategy = resource["spec"]["migration"]["strategy"]
    if strategy != "LiveMigration":
        error_out([make_error(
            "spec.migration.strategy", "invalid",
            "rollback is only supported for LiveMigration strategy",
        )])
        return

    conditions = status.get("conditions", [])
    conditions = remove_condition(conditions, "Migration")
    status["conditions"] = conditions
    del status["migration"]
    status["stable"] = compute_stable(conditions)

    resource["status"] = status
    store[name] = resource
    save_store(store)
    print_json(format_resource_for_output(resource))


# --- Vault command handlers ---

def vault_cmd_create(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    mesh_store = load_store()
    result, errs = validate_vault(doc, mesh_store)
    if errs:
        error_out(errs)
        return

    name = result["metadata"]["name"]
    vault_store = load_vault_store()

    if name in vault_store:
        error_out([make_error("metadata.name", "duplicate", f"vault '{name}' already exists")])
        return

    mesh_ref = result["spec"]["meshRef"]
    vault_name = result["spec"]["vaultName"]
    for v in vault_store.values():
        if v["spec"]["meshRef"] == mesh_ref and v["spec"]["vaultName"] == vault_name:
            error_out([make_error(
                "spec.vaultName", "duplicate",
                f"vault identity '{mesh_ref}/{vault_name}' already exists",
            )])
            return

    result["status"] = build_vault_status(mesh_store[mesh_ref])
    vault_store[name] = result
    save_vault_store(vault_store)
    print_json(result)


def vault_cmd_list(_args):
    vault_store = load_vault_store()
    items = sorted(
        [{"name": v["metadata"]["name"], "status": {"state": v["status"]["state"]}} for v in vault_store.values()],
        key=lambda x: x["name"],
    )
    print_json(items)


def vault_cmd_describe(args):
    vault_store = load_vault_store()
    if args.name not in vault_store:
        error_out([make_error("metadata.name", "not_found", f"vault '{args.name}' not found")])
        return
    print_json(vault_store[args.name])


def vault_cmd_delete(args):
    vault_store = load_vault_store()
    name = args.name
    if name not in vault_store:
        error_out([make_error("metadata.name", "not_found", f"vault '{name}' not found")])
        return
    del vault_store[name]
    save_vault_store(vault_store)
    print_json({"message": f"vault '{name}' deleted", "metadata": {"name": name}})


def vault_cmd_update(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    if not isinstance(doc, dict) or "metadata" not in doc:
        error_out([make_error("", "parse", "document must have 'metadata' and 'spec' keys")])
        return

    metadata = doc.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    raw_name = metadata.get("name")
    if not raw_name:
        error_out([make_error("metadata.name", "required", "name is required")])
        return

    vault_store = load_vault_store()
    if raw_name not in vault_store:
        error_out([make_error("metadata.name", "not_found", f"vault '{raw_name}' not found")])
        return

    stored = vault_store[raw_name]
    update_spec = doc.get("spec") or {}
    if not isinstance(update_spec, dict):
        update_spec = {}

    imm_errors = []
    if "meshRef" in update_spec and update_spec["meshRef"] is not None and update_spec["meshRef"] != stored["spec"]["meshRef"]:
        imm_errors.append(make_error(
            "spec.meshRef", "immutable",
            "field 'spec.meshRef' is immutable after creation",
        ))
    if "vaultName" in update_spec and update_spec["vaultName"] is not None and update_spec["vaultName"] != stored["spec"]["vaultName"]:
        imm_errors.append(make_error(
            "spec.vaultName", "immutable",
            "field 'spec.vaultName' is immutable after creation",
        ))
    if imm_errors:
        error_out(imm_errors)
        return

    merged_spec = deep_merge(stored["spec"], update_spec)
    merged_doc = {"metadata": {"name": raw_name}, "spec": merged_spec}

    mesh_store = load_store()
    result, errs = validate_vault(merged_doc, mesh_store)
    if errs:
        error_out(errs)
        return

    result["status"] = build_vault_status(mesh_store[result["spec"]["meshRef"]])
    vault_store[raw_name] = result
    save_vault_store(vault_store)
    print_json(result)


# --- Common operational resource helpers ---

def validate_op_name(metadata):
    name = None
    errors = []
    raw_name = metadata.get("name") if isinstance(metadata, dict) else None
    if raw_name is None or raw_name == "":
        errors.append(make_error("metadata.name", "required", "name is required and must not be empty"))
    elif not isinstance(raw_name, str):
        errors.append(make_error("metadata.name", "required", "name must be a non-empty string"))
    elif not NAME_RE.match(raw_name):
        errors.append(make_error(
            "metadata.name", "invalid",
            "name must be lowercase alphanumeric with interior hyphens only, minimum 2 characters",
        ))
    else:
        name = raw_name
    return name, errors


def validate_mesh_ref_field(spec, mesh_store):
    errors = []
    mesh_ref = None
    raw_ref = spec.get("meshRef") if isinstance(spec, dict) else None
    if not raw_ref or not isinstance(raw_ref, str):
        errors.append(make_error("spec.meshRef", "invalid", "meshRef is required and must reference an existing mesh"))
    elif mesh_store is not None and raw_ref not in mesh_store:
        errors.append(make_error("spec.meshRef", "invalid", f"mesh '{raw_ref}' not found"))
    else:
        mesh_ref = raw_ref
    return mesh_ref, errors


def validate_op_resources(spec):
    errors = []
    raw_resources = spec.get("resources") if isinstance(spec, dict) else None
    has_resources = isinstance(raw_resources, dict)

    memory = {"limit": "1Gi", "request": "1Gi"}
    if has_resources and "memory" in raw_resources:
        raw_memory = raw_resources["memory"]
        if not isinstance(raw_memory, dict):
            errors.append(make_error("spec.resources.memory.limit", "required", "memory.limit is required"))
            memory = None
        else:
            mem_lim = raw_memory.get("limit")
            if mem_lim is None:
                errors.append(make_error("spec.resources.memory.limit", "required", "memory.limit is required"))
                memory = None
            else:
                mem_lim = mem_lim if isinstance(mem_lim, str) else str(mem_lim)
                lim_val = parse_memory_quantity(mem_lim)
                if lim_val is None:
                    errors.append(make_error("spec.resources.memory.limit", "invalid", f"invalid memory quantity: {mem_lim!r}"))
                    memory = None
                else:
                    mem_req = raw_memory.get("request")
                    if mem_req is None:
                        memory = {"limit": mem_lim, "request": mem_lim}
                    else:
                        mem_req = mem_req if isinstance(mem_req, str) else str(mem_req)
                        req_val = parse_memory_quantity(mem_req)
                        if req_val is None:
                            errors.append(make_error("spec.resources.memory.request", "invalid", f"invalid memory quantity: {mem_req!r}"))
                            memory = None
                        elif req_val > lim_val:
                            errors.append(make_error("spec.resources.memory.request", "invalid", "memory request must not exceed limit"))
                            memory = None
                        else:
                            memory = {"limit": mem_lim, "request": mem_req}

    cpu = None
    if has_resources and "cpu" in raw_resources:
        raw_cpu = raw_resources["cpu"]
        if not isinstance(raw_cpu, dict):
            errors.append(make_error("spec.resources.cpu.limit", "required", "cpu.limit is required"))
        else:
            cpu_lim = raw_cpu.get("limit")
            if cpu_lim is None:
                errors.append(make_error("spec.resources.cpu.limit", "required", "cpu.limit is required"))
            else:
                cpu_lim = cpu_lim if isinstance(cpu_lim, str) else str(cpu_lim)
                lim_val = parse_cpu_quantity(cpu_lim)
                if lim_val is None:
                    errors.append(make_error("spec.resources.cpu.limit", "invalid", f"invalid CPU quantity: {cpu_lim!r}"))
                else:
                    cpu_req = raw_cpu.get("request")
                    if cpu_req is None:
                        cpu = {"limit": cpu_lim, "request": cpu_lim}
                    else:
                        cpu_req = cpu_req if isinstance(cpu_req, str) else str(cpu_req)
                        req_val = parse_cpu_quantity(cpu_req)
                        if req_val is None:
                            errors.append(make_error("spec.resources.cpu.request", "invalid", f"invalid CPU quantity: {cpu_req!r}"))
                        elif req_val > lim_val:
                            errors.append(make_error("spec.resources.cpu.request", "invalid", "CPU request must not exceed limit"))
                        else:
                            cpu = {"limit": cpu_lim, "request": cpu_req}

    resources_out = {}
    if memory is not None:
        resources_out["memory"] = memory
    if cpu is not None:
        resources_out["cpu"] = cpu
    return resources_out, errors


def check_op_spec_immutable(stored_spec, update_spec):
    if not update_spec or not isinstance(update_spec, dict):
        return []
    for key, val in update_spec.items():
        if stored_spec.get(key) != val:
            return [make_error("spec", "immutable", "spec is immutable after creation")]
    return []


def run_state_error(current_state):
    return make_error(
        "status.state", "invalid",
        f"resource is in state '{current_state}', expected 'Initializing'",
    )


def format_op_output(resource):
    out = copy.deepcopy(resource)
    status = out.get("status", {})
    state = status.get("state")
    if state not in ("Failed", "Unknown"):
        status.pop("detail", None)
    if state != "Succeeded":
        status.pop("storageRef", None)
    out["status"] = status
    return out


# --- Task validation ---

def validate_task(doc, mesh_store=None):
    errors = []

    if not isinstance(doc, dict) or "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    name, name_errs = validate_op_name(doc.get("metadata"))
    errors.extend(name_errs)

    spec = doc.get("spec") or {}
    if not isinstance(spec, dict):
        spec = {}

    mesh_ref, mesh_errs = validate_mesh_ref_field(spec, mesh_store)
    errors.extend(mesh_errs)

    inline = spec.get("inline")
    bundle_ref = spec.get("bundleRef")
    has_inline = isinstance(inline, str) and inline != ""
    has_bundle = isinstance(bundle_ref, str) and bundle_ref != ""

    if not (has_inline ^ has_bundle):
        errors.append(make_error("spec", "invalid", "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"))
        inline = None
        bundle_ref = None

    if errors:
        return None, errors

    out_spec = {"meshRef": mesh_ref}
    if has_inline:
        out_spec["inline"] = inline
    else:
        out_spec["bundleRef"] = bundle_ref

    return {"metadata": {"name": name}, "spec": out_spec}, []


# --- Task command handlers ---

def task_cmd_create(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    mesh_store = load_store()
    result, errs = validate_task(doc, mesh_store)
    if errs:
        error_out(errs)
        return

    name = result["metadata"]["name"]
    task_store = load_task_store()
    if name in task_store:
        error_out([make_error("metadata.name", "duplicate", f"task '{name}' already exists")])
        return

    result["status"] = {"state": "Initializing"}
    task_store[name] = result
    save_task_store(task_store)
    print_json(format_op_output(result))


def task_cmd_list(_args):
    task_store = load_task_store()
    items = sorted(
        [{"name": r["metadata"]["name"], "status": {"state": r["status"]["state"]}} for r in task_store.values()],
        key=lambda x: x["name"],
    )
    print_json(items)


def task_cmd_describe(args):
    task_store = load_task_store()
    if args.name not in task_store:
        error_out([make_error("metadata.name", "not_found", f"task '{args.name}' not found")])
        return
    print_json(format_op_output(task_store[args.name]))


def task_cmd_update(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    if not isinstance(doc, dict) or "metadata" not in doc:
        error_out([make_error("", "parse", "document must have 'metadata' and 'spec' keys")])
        return

    metadata = doc.get("metadata") or {}
    raw_name = metadata.get("name") if isinstance(metadata, dict) else None
    if not raw_name:
        error_out([make_error("metadata.name", "required", "name is required")])
        return

    task_store = load_task_store()
    if raw_name not in task_store:
        error_out([make_error("metadata.name", "not_found", f"task '{raw_name}' not found")])
        return

    stored = task_store[raw_name]
    imm_errors = check_op_spec_immutable(stored["spec"], doc.get("spec"))
    if imm_errors:
        error_out(imm_errors)
        return

    print_json(format_op_output(stored))


def task_cmd_delete(args):
    task_store = load_task_store()
    name = args.name
    if name not in task_store:
        error_out([make_error("metadata.name", "not_found", f"task '{name}' not found")])
        return
    del task_store[name]
    save_task_store(task_store)
    print_json({"message": f"task '{name}' deleted", "metadata": {"name": name}})


def task_cmd_run(args):
    task_store = load_task_store()
    name = args.name
    if name not in task_store:
        error_out([make_error("metadata.name", "not_found", f"task '{name}' not found")])
        return

    resource = copy.deepcopy(task_store[name])
    current_state = resource["status"]["state"]
    if current_state != "Initializing":
        error_out([run_state_error(current_state)])
        return

    resource["status"]["state"] = "Running"
    task_store[name] = resource
    save_task_store(task_store)

    spec = resource["spec"]
    if "inline" in spec:
        lines = spec["inline"].splitlines()
        failed = False
        for i, line in enumerate(lines):
            if line.startswith("FAIL:"):
                reason = line[5:].strip()
                resource["status"]["state"] = "Failed"
                resource["status"]["detail"] = f"command {i} failed: {reason}"
                failed = True
                break
        if not failed:
            resource["status"]["state"] = "Succeeded"
    else:
        resource["status"]["state"] = "Succeeded"

    task_store[name] = resource
    save_task_store(task_store)
    print_json(format_op_output(resource))


# --- Snapshot validation ---

def validate_snapshot(doc, mesh_store=None):
    errors = []

    if not isinstance(doc, dict) or "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    name, name_errs = validate_op_name(doc.get("metadata"))
    errors.extend(name_errs)

    spec = doc.get("spec") or {}
    if not isinstance(spec, dict):
        spec = {}

    mesh_ref, mesh_errs = validate_mesh_ref_field(spec, mesh_store)
    errors.extend(mesh_errs)

    resources_out, res_errs = validate_op_resources(spec)
    errors.extend(res_errs)

    if errors:
        return None, errors

    out_spec = {"meshRef": mesh_ref, "resources": resources_out}

    raw_storage = spec.get("storage")
    if isinstance(raw_storage, dict):
        storage_out = {}
        if "size" in raw_storage:
            storage_out["size"] = raw_storage["size"]
        if "className" in raw_storage:
            storage_out["className"] = raw_storage["className"]
        if storage_out:
            out_spec["storage"] = storage_out

    raw_scope = spec.get("scope")
    if isinstance(raw_scope, dict):
        out_spec["scope"] = raw_scope

    return {"metadata": {"name": name}, "spec": out_spec}, []


# --- Snapshot command handlers ---

def snapshot_cmd_create(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    mesh_store = load_store()
    result, errs = validate_snapshot(doc, mesh_store)
    if errs:
        error_out(errs)
        return

    name = result["metadata"]["name"]
    snapshot_store = load_snapshot_store()
    if name in snapshot_store:
        error_out([make_error("metadata.name", "duplicate", f"snapshot '{name}' already exists")])
        return

    result["status"] = {"state": "Initializing"}
    snapshot_store[name] = result
    save_snapshot_store(snapshot_store)
    print_json(format_op_output(result))


def snapshot_cmd_list(_args):
    snapshot_store = load_snapshot_store()
    items = sorted(
        [{"name": r["metadata"]["name"], "status": {"state": r["status"]["state"]}} for r in snapshot_store.values()],
        key=lambda x: x["name"],
    )
    print_json(items)


def snapshot_cmd_describe(args):
    snapshot_store = load_snapshot_store()
    if args.name not in snapshot_store:
        error_out([make_error("metadata.name", "not_found", f"snapshot '{args.name}' not found")])
        return
    print_json(format_op_output(snapshot_store[args.name]))


def snapshot_cmd_update(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    if not isinstance(doc, dict) or "metadata" not in doc:
        error_out([make_error("", "parse", "document must have 'metadata' and 'spec' keys")])
        return

    metadata = doc.get("metadata") or {}
    raw_name = metadata.get("name") if isinstance(metadata, dict) else None
    if not raw_name:
        error_out([make_error("metadata.name", "required", "name is required")])
        return

    snapshot_store = load_snapshot_store()
    if raw_name not in snapshot_store:
        error_out([make_error("metadata.name", "not_found", f"snapshot '{raw_name}' not found")])
        return

    stored = snapshot_store[raw_name]
    imm_errors = check_op_spec_immutable(stored["spec"], doc.get("spec"))
    if imm_errors:
        error_out(imm_errors)
        return

    print_json(format_op_output(stored))


def snapshot_cmd_delete(args):
    snapshot_store = load_snapshot_store()
    name = args.name
    if name not in snapshot_store:
        error_out([make_error("metadata.name", "not_found", f"snapshot '{name}' not found")])
        return

    recovery_store = load_recovery_store()
    dependent = sorted(r["metadata"]["name"] for r in recovery_store.values() if r["spec"]["snapshotRef"] == name)
    if dependent:
        error_out([make_error(
            "metadata.name", "conflict",
            f"snapshot '{name}' is referenced by recovery resource(s): {', '.join(dependent)}",
        )])
        return

    del snapshot_store[name]
    save_snapshot_store(snapshot_store)
    print_json({"message": f"snapshot '{name}' deleted", "metadata": {"name": name}})


def snapshot_cmd_run(args):
    snapshot_store = load_snapshot_store()
    name = args.name
    if name not in snapshot_store:
        error_out([make_error("metadata.name", "not_found", f"snapshot '{name}' not found")])
        return

    resource = copy.deepcopy(snapshot_store[name])
    current_state = resource["status"]["state"]
    if current_state != "Initializing":
        error_out([run_state_error(current_state)])
        return

    resource["status"]["state"] = "Running"
    snapshot_store[name] = resource
    save_snapshot_store(snapshot_store)

    mesh_store = load_store()
    mesh_ref = resource["spec"]["meshRef"]
    mesh = mesh_store.get(mesh_ref)
    if mesh is None or not mesh.get("status", {}).get("stable", False):
        resource["status"]["state"] = "Unknown"
        resource["status"]["detail"] = f"mesh '{mesh_ref}' is not stable"
    else:
        resource["status"]["state"] = "Succeeded"
        resource["status"]["storageRef"] = f"snapshot/{name}/data"

    snapshot_store[name] = resource
    save_snapshot_store(snapshot_store)
    print_json(format_op_output(resource))


# --- Recovery validation ---

def validate_recovery(doc, mesh_store=None, snapshot_store=None):
    errors = []

    if not isinstance(doc, dict) or "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    name, name_errs = validate_op_name(doc.get("metadata"))
    errors.extend(name_errs)

    spec = doc.get("spec") or {}
    if not isinstance(spec, dict):
        spec = {}

    mesh_ref, mesh_errs = validate_mesh_ref_field(spec, mesh_store)
    errors.extend(mesh_errs)

    snapshot_ref = None
    raw_snapshot_ref = spec.get("snapshotRef")
    if not raw_snapshot_ref or not isinstance(raw_snapshot_ref, str):
        errors.append(make_error("spec.snapshotRef", "invalid", "snapshotRef is required and must reference an existing snapshot"))
    elif snapshot_store is not None:
        if raw_snapshot_ref not in snapshot_store:
            errors.append(make_error("spec.snapshotRef", "invalid", f"snapshot '{raw_snapshot_ref}' not found"))
        else:
            snap = snapshot_store[raw_snapshot_ref]
            snap_mesh_ref = snap["spec"]["meshRef"]
            if mesh_ref is not None and snap_mesh_ref != mesh_ref:
                errors.append(make_error(
                    "spec.snapshotRef", "invalid",
                    f"snapshot '{raw_snapshot_ref}' belongs to mesh '{snap_mesh_ref}', not '{mesh_ref}'",
                ))
            else:
                snapshot_ref = raw_snapshot_ref
    else:
        snapshot_ref = raw_snapshot_ref

    resources_out, res_errs = validate_op_resources(spec)
    errors.extend(res_errs)

    if errors:
        return None, errors

    out_spec = {"meshRef": mesh_ref, "snapshotRef": snapshot_ref, "resources": resources_out}

    raw_scope = spec.get("scope")
    if isinstance(raw_scope, dict):
        out_spec["scope"] = raw_scope

    return {"metadata": {"name": name}, "spec": out_spec}, []


# --- Recovery command handlers ---

def recovery_cmd_create(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    mesh_store = load_store()
    snapshot_store = load_snapshot_store()
    result, errs = validate_recovery(doc, mesh_store, snapshot_store)
    if errs:
        error_out(errs)
        return

    name = result["metadata"]["name"]
    recovery_store = load_recovery_store()
    if name in recovery_store:
        error_out([make_error("metadata.name", "duplicate", f"recovery '{name}' already exists")])
        return

    result["status"] = {"state": "Initializing"}
    recovery_store[name] = result
    save_recovery_store(recovery_store)
    print_json(format_op_output(result))


def recovery_cmd_list(_args):
    recovery_store = load_recovery_store()
    items = sorted(
        [{"name": r["metadata"]["name"], "status": {"state": r["status"]["state"]}} for r in recovery_store.values()],
        key=lambda x: x["name"],
    )
    print_json(items)


def recovery_cmd_describe(args):
    recovery_store = load_recovery_store()
    if args.name not in recovery_store:
        error_out([make_error("metadata.name", "not_found", f"recovery '{args.name}' not found")])
        return
    print_json(format_op_output(recovery_store[args.name]))


def recovery_cmd_update(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    if not isinstance(doc, dict) or "metadata" not in doc:
        error_out([make_error("", "parse", "document must have 'metadata' and 'spec' keys")])
        return

    metadata = doc.get("metadata") or {}
    raw_name = metadata.get("name") if isinstance(metadata, dict) else None
    if not raw_name:
        error_out([make_error("metadata.name", "required", "name is required")])
        return

    recovery_store = load_recovery_store()
    if raw_name not in recovery_store:
        error_out([make_error("metadata.name", "not_found", f"recovery '{raw_name}' not found")])
        return

    stored = recovery_store[raw_name]
    imm_errors = check_op_spec_immutable(stored["spec"], doc.get("spec"))
    if imm_errors:
        error_out(imm_errors)
        return

    print_json(format_op_output(stored))


def recovery_cmd_delete(args):
    recovery_store = load_recovery_store()
    name = args.name
    if name not in recovery_store:
        error_out([make_error("metadata.name", "not_found", f"recovery '{name}' not found")])
        return
    del recovery_store[name]
    save_recovery_store(recovery_store)
    print_json({"message": f"recovery '{name}' deleted", "metadata": {"name": name}})


def recovery_cmd_run(args):
    recovery_store = load_recovery_store()
    name = args.name
    if name not in recovery_store:
        error_out([make_error("metadata.name", "not_found", f"recovery '{name}' not found")])
        return

    resource = copy.deepcopy(recovery_store[name])
    current_state = resource["status"]["state"]
    if current_state != "Initializing":
        error_out([run_state_error(current_state)])
        return

    resource["status"]["state"] = "Running"
    recovery_store[name] = resource
    save_recovery_store(recovery_store)

    mesh_store = load_store()
    mesh_ref = resource["spec"]["meshRef"]
    mesh = mesh_store.get(mesh_ref)
    if mesh is None or not mesh.get("status", {}).get("stable", False):
        resource["status"]["state"] = "Unknown"
        resource["status"]["detail"] = f"mesh '{mesh_ref}' is not stable"
    else:
        resource["status"]["state"] = "Succeeded"

    recovery_store[name] = resource
    save_recovery_store(recovery_store)
    print_json(format_op_output(resource))


def cmd_shell(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return
    exposure = store[name].get("spec", {}).get("exposure")
    if not exposure:
        error_out([make_error("spec.exposure", "invalid", f"mesh '{name}' has no exposure configured")])
        return
    print_json(compute_connection_details(name, exposure))


# --- CLI entry point (tasks 5.1, 5.2) ---

def main():
    parser = argparse.ArgumentParser(prog="meshctl")
    top_sub = parser.add_subparsers(dest="command")

    mesh_p = top_sub.add_parser("mesh")
    mesh_sub = mesh_p.add_subparsers(dest="operation")

    create_p = mesh_sub.add_parser("create")
    create_p.add_argument("-f", dest="file", required=True)

    mesh_sub.add_parser("list")

    describe_p = mesh_sub.add_parser("describe")
    describe_p.add_argument("name")

    delete_p = mesh_sub.add_parser("delete")
    delete_p.add_argument("name")

    update_p = mesh_sub.add_parser("update")
    update_p.add_argument("-f", dest="file", required=True)

    migrate_p = mesh_sub.add_parser("migrate")
    migrate_p.add_argument("name")

    rollback_p = mesh_sub.add_parser("rollback")
    rollback_p.add_argument("name")

    shell_p = mesh_sub.add_parser("shell")
    shell_p.add_argument("name")

    vault_p = top_sub.add_parser("vault")
    vault_sub = vault_p.add_subparsers(dest="operation")

    vault_create_p = vault_sub.add_parser("create")
    vault_create_p.add_argument("-f", dest="file", required=True)

    vault_sub.add_parser("list")

    vault_describe_p = vault_sub.add_parser("describe")
    vault_describe_p.add_argument("name")

    vault_delete_p = vault_sub.add_parser("delete")
    vault_delete_p.add_argument("name")

    vault_update_p = vault_sub.add_parser("update")
    vault_update_p.add_argument("-f", dest="file", required=True)

    task_p = top_sub.add_parser("task")
    task_sub = task_p.add_subparsers(dest="operation")
    task_create_p = task_sub.add_parser("create")
    task_create_p.add_argument("-f", dest="file", required=True)
    task_sub.add_parser("list")
    task_describe_p = task_sub.add_parser("describe")
    task_describe_p.add_argument("name")
    task_update_p = task_sub.add_parser("update")
    task_update_p.add_argument("-f", dest="file", required=True)
    task_delete_p = task_sub.add_parser("delete")
    task_delete_p.add_argument("name")
    task_run_p = task_sub.add_parser("run")
    task_run_p.add_argument("name")

    snapshot_p = top_sub.add_parser("snapshot")
    snapshot_sub = snapshot_p.add_subparsers(dest="operation")
    snapshot_create_p = snapshot_sub.add_parser("create")
    snapshot_create_p.add_argument("-f", dest="file", required=True)
    snapshot_sub.add_parser("list")
    snapshot_describe_p = snapshot_sub.add_parser("describe")
    snapshot_describe_p.add_argument("name")
    snapshot_update_p = snapshot_sub.add_parser("update")
    snapshot_update_p.add_argument("-f", dest="file", required=True)
    snapshot_delete_p = snapshot_sub.add_parser("delete")
    snapshot_delete_p.add_argument("name")
    snapshot_run_p = snapshot_sub.add_parser("run")
    snapshot_run_p.add_argument("name")

    recovery_p = top_sub.add_parser("recovery")
    recovery_sub = recovery_p.add_subparsers(dest="operation")
    recovery_create_p = recovery_sub.add_parser("create")
    recovery_create_p.add_argument("-f", dest="file", required=True)
    recovery_sub.add_parser("list")
    recovery_describe_p = recovery_sub.add_parser("describe")
    recovery_describe_p.add_argument("name")
    recovery_update_p = recovery_sub.add_parser("update")
    recovery_update_p.add_argument("-f", dest="file", required=True)
    recovery_delete_p = recovery_sub.add_parser("delete")
    recovery_delete_p.add_argument("name")
    recovery_run_p = recovery_sub.add_parser("run")
    recovery_run_p.add_argument("name")

    args = parser.parse_args()

    if args.command == "mesh":
        if not args.operation:
            parser.print_usage(sys.stderr)
            sys.exit(1)
        {
            "create": cmd_create,
            "list": cmd_list,
            "describe": cmd_describe,
            "delete": cmd_delete,
            "update": cmd_update,
            "migrate": cmd_migrate,
            "rollback": cmd_rollback,
            "shell": cmd_shell,
        }[args.operation](args)
    elif args.command == "vault":
        if not args.operation:
            parser.print_usage(sys.stderr)
            sys.exit(1)
        {
            "create": vault_cmd_create,
            "list": vault_cmd_list,
            "describe": vault_cmd_describe,
            "delete": vault_cmd_delete,
            "update": vault_cmd_update,
        }[args.operation](args)
    elif args.command == "task":
        if not args.operation:
            parser.print_usage(sys.stderr)
            sys.exit(1)
        {
            "create": task_cmd_create,
            "list": task_cmd_list,
            "describe": task_cmd_describe,
            "update": task_cmd_update,
            "delete": task_cmd_delete,
            "run": task_cmd_run,
        }[args.operation](args)
    elif args.command == "snapshot":
        if not args.operation:
            parser.print_usage(sys.stderr)
            sys.exit(1)
        {
            "create": snapshot_cmd_create,
            "list": snapshot_cmd_list,
            "describe": snapshot_cmd_describe,
            "update": snapshot_cmd_update,
            "delete": snapshot_cmd_delete,
            "run": snapshot_cmd_run,
        }[args.operation](args)
    elif args.command == "recovery":
        if not args.operation:
            parser.print_usage(sys.stderr)
            sys.exit(1)
        {
            "create": recovery_cmd_create,
            "list": recovery_cmd_list,
            "describe": recovery_cmd_describe,
            "update": recovery_cmd_update,
            "delete": recovery_cmd_delete,
            "run": recovery_cmd_run,
        }[args.operation](args)
    else:
        parser.print_usage(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
