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
VALID_MIGRATION_STRATEGIES = {"FullStop", "LiveMigration", "RollingPatch"}
VALID_EXPOSURE_TYPES = {"Gateway", "DirectPort", "Balancer"}
VALID_REGION_EXPOSE_TYPES = {"Internal", "DirectPort", "Balancer", "Gateway"}
DEFAULT_DISCOVERY = {
    "type": "relay",
    "heartbeat": {"enabled": True, "interval": 10000, "timeout": 30000},
}
EXPOSURE_ALLOWED_FIELDS = {
    "Gateway": {"hostname", "annotations"},
    "DirectPort": {"port", "directPort"},
    "Balancer": {"port"},
}
EXPOSURE_ALL_SUB_FIELDS = {"hostname", "annotations", "port", "directPort"}
DEFAULT_EXPOSURE_PORT = 8080
RUNTIME_CATALOG = {
    "3.0.0": "deprecated",
    "3.1.0": "skipped",
    "3.1.1": "supported",
    "4.0.0": "supported",
}
MIGRATION_STAGE_SEQUENCES = {
    "FullStop": ["Migrate"],
    "RollingPatch": ["Migrate"],
    "LiveMigration": ["Prepare", "Migrate", "Complete"],
}


# --- Output helpers ---

def print_json(obj):
    print(json.dumps(obj))


def make_error(field, type_, message):
    return {"field": field, "type": type_, "message": message}


def error_out(errors):
    print_json({"errors": sorted(errors, key=lambda e: (e["field"], e["type"]))})


def success_out(resource, warnings=None):
    out = format_resource_for_output(resource)
    if warnings:
        out["warnings"] = sorted(warnings, key=lambda w: (w["field"], w["message"]))
    print_json(out)


# --- Runtime version helpers ---

def parse_runtime_version(v):
    """Return (major, minor, patch) int tuple or None."""
    if not isinstance(v, str) or not RUNTIME_RE.match(v):
        return None
    parts = v.split(".")
    return tuple(int(p) for p in parts)


def validate_runtime_catalog(version):
    """Return (error, warning) — at most one will be non-None."""
    status = RUNTIME_CATALOG.get(version)
    if status is None:
        return (
            make_error("spec.runtime", "invalid", f"runtime version '{version}' is not in the supported catalog"),
            None,
        )
    if status == "skipped":
        return (
            make_error("spec.runtime", "invalid", f"runtime version '{version}' is skipped and cannot be targeted"),
            None,
        )
    if status == "deprecated":
        return (
            None,
            {"field": "spec.runtime", "message": f"runtime version '{version}' is deprecated"},
        )
    return None, None


# --- Stability helper ---

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


def is_migration_active(conditions):
    return any(c["type"] == "Migration" and c["status"] == "True" for c in conditions)


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


def _save_json_store(path, store):
    dir_ = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(store, f)
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


# --- Telemetry probe computation ---

def compute_telemetry_probe(tags):
    """Compute status.telemetryProbe from metadata.tags."""
    if tags is None:
        return {"enabled": True}
    telemetry_val = (tags.get("mesh.io/telemetry") or "true").lower()
    if telemetry_val == "false":
        return {"enabled": False}
    probe = {"enabled": True}
    label_map = [
        ("mesh.io/targetLabels", "targetLabels"),
        ("mesh.io/probeTargetLabels", "probeTargetLabels"),
        ("mesh.io/instanceLabels", "instanceLabels"),
    ]
    labels = {}
    for tag_key, label_key in label_map:
        val = tags.get(tag_key)
        if val:
            labels[label_key] = [s.strip() for s in val.split(",") if s.strip()]
    if labels:
        probe["labels"] = labels
    return probe


# --- Connection details computation ---

def compute_connection_details(name, exposure):
    exp_type = exposure.get("type")
    if exp_type == "Gateway":
        host = exposure.get("hostname") or f"{name}-gateway"
        port = 443
    elif exp_type == "DirectPort":
        host = name
        port = exposure.get("directPort") or DEFAULT_EXPOSURE_PORT
    elif exp_type == "Balancer":
        host = f"{name}-external"
        port = exposure.get("port") or DEFAULT_EXPOSURE_PORT
    else:
        return None
    return {"host": host, "port": port, "protocol": "https"}


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


# --- Status helpers (task 2.1) ---

def build_initial_status(instances):
    conditions = sorted([
        {"type": "Healthy", "status": "True", "message": ""},
        {"type": "PrechecksPassed", "status": "True", "message": ""},
    ], key=lambda c: c["type"])
    return {
        "state": "Running",
        "stable": True,
        "instances": {"ready": instances, "starting": 0, "stopped": 0},
        "conditions": conditions,
    }


# --- Resource output formatter ---

def format_resource_for_output(resource):
    """Apply output rules: storage format, hide desiredInstancesOnResume when running, inject connection details."""
    out = copy.deepcopy(resource)
    network = out.get("spec", {}).get("network")
    if network and "storage" in network:
        network["storage"] = format_storage(network["storage"])
    status = out.get("status", {})
    if status.get("state") != "Stopped":
        status.pop("desiredInstancesOnResume", None)
    name = out.get("metadata", {}).get("name", "")
    exposure = out.get("spec", {}).get("exposure")
    if exposure is not None:
        status["connectionDetails"] = compute_connection_details(name, exposure)
    else:
        status.pop("connectionDetails", None)
    mgmt_enabled = (out.get("spec", {}).get("management") or {}).get("enabled", False)
    if mgmt_enabled:
        status["managementConnectionDetails"] = {
            "host": f"{name}-admin",
            "port": 9990,
            "protocol": "https",
        }
    else:
        status.pop("managementConnectionDetails", None)
    tags = (out.get("metadata") or {}).get("tags")
    status["telemetryProbe"] = compute_telemetry_probe(tags)
    return out


# --- Validation + default application (tasks 1.1-1.5, 6.2, 6.3) ---

def validate_and_build(doc, is_update=False):  # returns (result, errors, warnings)
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

    # metadata.tags
    tags = None
    raw_tags = metadata.get("tags")
    if raw_tags is not None:
        if isinstance(raw_tags, dict):
            tags = raw_tags

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
            cat_err, cat_warn = validate_runtime_catalog(raw_runtime)
            if cat_err:
                errors.append(cat_err)
            else:
                runtime = raw_runtime
                if cat_warn:
                    warnings.append(cat_warn)

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
        if raw_strategy not in VALID_MIGRATION_STRATEGIES:
            errors.append(make_error(
                "spec.migration.strategy", "invalid",
                f"migration.strategy must be one of FullStop, LiveMigration, RollingPatch; got {raw_strategy!r}",
            ))
            strategy = None
        else:
            strategy = raw_strategy
            if raw_strategy == "LiveMigration" and spec.get("regions"):
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

    # spec.exposure
    raw_exposure = spec.get("exposure")
    exposure = None
    if raw_exposure is not None:
        if not isinstance(raw_exposure, dict):
            errors.append(make_error("spec.exposure.type", "required", "exposure.type is required"))
        else:
            exp_type = raw_exposure.get("type")
            if not exp_type:
                errors.append(make_error("spec.exposure.type", "required", "exposure.type is required"))
            elif exp_type not in VALID_EXPOSURE_TYPES:
                errors.append(make_error(
                    "spec.exposure.type", "invalid",
                    f"exposure.type must be one of Gateway, DirectPort, Balancer",
                ))
            else:
                allowed = EXPOSURE_ALLOWED_FIELDS[exp_type]
                for sub in sorted(EXPOSURE_ALL_SUB_FIELDS - allowed):
                    if sub in raw_exposure:
                        errors.append(make_error(
                            f"spec.exposure.{sub}", "forbidden",
                            f"field 'spec.exposure.{sub}' is not allowed for exposure type '{exp_type}'",
                        ))
                exposure = {"type": exp_type}
                if "hostname" in allowed and raw_exposure.get("hostname") is not None:
                    exposure["hostname"] = raw_exposure["hostname"]
                if "annotations" in allowed and raw_exposure.get("annotations") is not None:
                    exposure["annotations"] = raw_exposure["annotations"]
                if "port" in allowed and raw_exposure.get("port") is not None:
                    exposure["port"] = raw_exposure["port"]
                if "directPort" in allowed and raw_exposure.get("directPort") is not None:
                    exposure["directPort"] = raw_exposure["directPort"]

    # spec.management
    raw_management = spec.get("management")
    management_enabled = False
    if isinstance(raw_management, dict):
        raw_enabled = raw_management.get("enabled")
        if raw_enabled is not None:
            management_enabled = bool(raw_enabled)
    management = {"enabled": management_enabled}

    # spec.placement
    raw_placement = spec.get("placement")
    placement_affinity_type = "preferred"
    placement_affinity_scope = "node"
    if raw_placement is not None:
        if not isinstance(raw_placement, dict):
            errors.append(make_error("spec.placement", "invalid", "placement must be an object"))
        else:
            raw_affinity = raw_placement.get("affinity")
            if raw_affinity is not None:
                if not isinstance(raw_affinity, dict):
                    errors.append(make_error("spec.placement.affinity", "invalid", "affinity must be an object"))
                else:
                    raw_type = raw_affinity.get("type", "preferred")
                    if raw_type not in ("preferred", "required"):
                        errors.append(make_error("spec.placement.affinity.type", "invalid",
                                                  "affinity.type must be one of 'preferred', 'required'"))
                    else:
                        placement_affinity_type = raw_type
                    raw_scope = raw_affinity.get("scope", "node")
                    if raw_scope not in ("node", "zone"):
                        errors.append(make_error("spec.placement.affinity.scope", "invalid",
                                                  "affinity.scope must be one of 'node', 'zone'"))
                    else:
                        placement_affinity_scope = raw_scope

    # spec.configBundleRef
    config_bundle_ref = None
    has_config_bundle_ref = "configBundleRef" in spec
    if has_config_bundle_ref:
        raw_cbr = spec["configBundleRef"]
        if not is_update and not isinstance(raw_cbr, str):
            errors.append(make_error("spec.configBundleRef", "invalid", "configBundleRef must be a string"))
        else:
            config_bundle_ref = raw_cbr

    # spec.extensions
    raw_extensions = spec.get("extensions")
    extensions = None
    if raw_extensions is not None and isinstance(raw_extensions, list):
        extensions = []
        for _i, _ext in enumerate(raw_extensions):
            if not isinstance(_ext, dict):
                errors.append(make_error(f"spec.extensions[{_i}]", "invalid",
                                          "exactly one of 'url' or 'artifact' must be set"))
                continue
            _has_url = "url" in _ext
            _has_artifact = "artifact" in _ext
            if _has_url == _has_artifact:
                errors.append(make_error(f"spec.extensions[{_i}]", "invalid",
                                          "exactly one of 'url' or 'artifact' must be set"))
                continue
            _ext_out = {}
            if _has_url:
                _ext_out["url"] = _ext["url"]
            else:
                _ext_out["artifact"] = _ext["artifact"]
            if _ext.get("integrity") is not None:
                _ext_out["integrity"] = _ext["integrity"]
            extensions.append(_ext_out)

    # spec.regions
    raw_regions = spec.get("regions")
    regions = None
    if raw_regions is not None:
        if not isinstance(raw_regions, dict):
            errors.append(make_error("spec.regions", "invalid", "regions must be an object"))
        else:
            _raw_local = raw_regions.get("local")
            if _raw_local is None:
                errors.append(make_error("spec.regions.local", "required", "spec.regions.local is required"))
            elif not isinstance(_raw_local, dict):
                errors.append(make_error("spec.regions.local", "invalid", "spec.regions.local must be an object"))
            else:
                _local_out = {}
                _local_expose_type = None

                # name
                _ln = _raw_local.get("name")
                if not _ln or not isinstance(_ln, str):
                    errors.append(make_error("spec.regions.local.name", "required",
                                              "spec.regions.local.name is required"))
                else:
                    _local_out["name"] = _ln

                # expose.type
                _raw_expose = _raw_local.get("expose")
                if _raw_expose is None or not isinstance(_raw_expose, dict) or not _raw_expose.get("type"):
                    errors.append(make_error("spec.regions.local.expose.type", "required",
                                              "spec.regions.local.expose.type is required"))
                else:
                    _et = _raw_expose["type"]
                    if _et not in VALID_REGION_EXPOSE_TYPES:
                        errors.append(make_error("spec.regions.local.expose.type", "invalid",
                                                  "expose.type must be one of Internal, DirectPort, Balancer, Gateway"))
                    else:
                        _local_expose_type = _et
                        _local_out["expose"] = {"type": _et}

                # maxRelayNodes
                if "maxRelayNodes" in _raw_local:
                    _mrn = _raw_local["maxRelayNodes"]
                    if _mrn is None or isinstance(_mrn, bool) or not isinstance(_mrn, int) or _mrn <= 0:
                        errors.append(make_error("spec.regions.local.maxRelayNodes", "invalid",
                                                  "maxRelayNodes must be a positive integer"))
                    else:
                        _local_out["maxRelayNodes"] = _mrn

                # encryption
                _raw_enc = _raw_local.get("encryption")
                if _raw_enc is not None:
                    if not isinstance(_raw_enc, dict):
                        errors.append(make_error("spec.regions.local.encryption", "invalid",
                                                  "encryption must be an object"))
                    else:
                        _enc_out = {}
                        _proto = _raw_enc.get("protocol", "TLSv1.3")
                        if _proto not in ("TLSv1.2", "TLSv1.3"):
                            errors.append(make_error("spec.regions.local.encryption.protocol", "invalid",
                                                      "protocol must be one of 'TLSv1.2', 'TLSv1.3'"))
                        else:
                            _enc_out["protocol"] = _proto
                        for _ks_name in ("transportKeyStore", "relayKeyStore", "trustStore"):
                            _raw_ks = _raw_enc.get(_ks_name)
                            if _raw_ks is not None:
                                if not isinstance(_raw_ks, dict):
                                    errors.append(make_error(
                                        f"spec.regions.local.encryption.{_ks_name}", "invalid",
                                        f"{_ks_name} must be an object"))
                                else:
                                    _ks_out = {}
                                    for _sf in ("secretRef", "alias", "filename"):
                                        _sfv = _raw_ks.get(_sf)
                                        if not _sfv or not isinstance(_sfv, str):
                                            errors.append(make_error(
                                                f"spec.regions.local.encryption.{_ks_name}.{_sf}",
                                                "required", f"{_sf} is required"))
                                        else:
                                            _ks_out[_sf] = _sfv
                                    _enc_out[_ks_name] = _ks_out
                            elif _ks_name == "transportKeyStore" and _local_expose_type == "Gateway":
                                errors.append(make_error(
                                    "spec.regions.local.encryption.transportKeyStore", "required",
                                    "transportKeyStore is required when expose type is 'Gateway'"))
                        _local_out["encryption"] = _enc_out
                        if "trustStore" not in _raw_enc:
                            warnings.append({
                                "field": "spec.regions.local.encryption.trustStore",
                                "message": "trustStore is absent; inter-region traffic may not be verified",
                            })

                # discovery
                _raw_disc = _raw_local.get("discovery")
                if _raw_disc is not None:
                    if not isinstance(_raw_disc, dict):
                        errors.append(make_error("spec.regions.local.discovery", "invalid",
                                                  "discovery must be an object"))
                        _local_out["discovery"] = copy.deepcopy(DEFAULT_DISCOVERY)
                    else:
                        _disc_type = _raw_disc.get("type")
                        if _disc_type != "relay":
                            errors.append(make_error("spec.regions.local.discovery.type", "invalid",
                                                      "discovery.type must be 'relay'"))
                        _raw_hb = _raw_disc.get("heartbeat") or {}
                        _hb_interval = _raw_hb.get("interval")
                        _hb_timeout = _raw_hb.get("timeout")
                        if (_hb_interval is not None and _hb_timeout is not None
                                and isinstance(_hb_interval, (int, float))
                                and isinstance(_hb_timeout, (int, float))
                                and _hb_interval >= _hb_timeout):
                            errors.append(make_error("spec.regions.local.discovery.heartbeat", "invalid",
                                                      "heartbeat.interval must be less than heartbeat.timeout"))
                        _local_out["discovery"] = _raw_disc
                else:
                    _local_out["discovery"] = copy.deepcopy(DEFAULT_DISCOVERY)

                # remotes
                _raw_remotes = raw_regions.get("remotes")
                regions = {"local": _local_out}
                if _raw_remotes is not None and isinstance(_raw_remotes, list):
                    _remotes_out = []
                    _seen_rnames = {}
                    for _ri, _rem in enumerate(_raw_remotes):
                        if not isinstance(_rem, dict):
                            continue
                        _rem_out = {}
                        _rn = _rem.get("name")
                        _ru = _rem.get("url")
                        if not _rn or not isinstance(_rn, str):
                            errors.append(make_error(f"spec.regions.remotes[{_ri}].name", "required",
                                                      "remote name is required"))
                        else:
                            _rem_out["name"] = _rn
                            _seen_rnames.setdefault(_rn, []).append(_ri)
                        if not _ru or not isinstance(_ru, str):
                            errors.append(make_error(f"spec.regions.remotes[{_ri}].url", "required",
                                                      "remote url is required"))
                        else:
                            _rem_out["url"] = _ru
                        for _opt in ("credentialRef", "namespace", "clusterRef"):
                            if _rem.get(_opt) is not None:
                                _rem_out[_opt] = _rem[_opt]
                        _remotes_out.append(_rem_out)
                    for _rn, _idxs in _seen_rnames.items():
                        if len(_idxs) > 1:
                            for _dup_idx in _idxs[1:]:
                                errors.append(make_error(f"spec.regions.remotes[{_dup_idx}].name", "duplicate",
                                                          f"duplicate remote name: {_rn!r}"))
                    regions["remotes"] = _remotes_out
                elif _raw_remotes is not None:
                    regions["remotes"] = []

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
        "network": {
            "storage": storage,
            "replicationFactor": rf,
        },
        "management": management,
        "placement": {"affinity": {"type": placement_affinity_type, "scope": placement_affinity_scope}},
    }
    if has_runtime:
        out_spec["runtime"] = runtime
    if has_cpu:
        out_spec["resources"]["cpu"] = cpu
    if exposure is not None:
        out_spec["exposure"] = exposure
    if regions is not None:
        out_spec["regions"] = regions
    if has_config_bundle_ref and config_bundle_ref is not None:
        out_spec["configBundleRef"] = config_bundle_ref
    if extensions is not None:
        out_spec["extensions"] = extensions

    out_metadata = {"name": name}
    if tags is not None:
        out_metadata["tags"] = tags

    return {"metadata": out_metadata, "spec": out_spec}, [], warnings


# --- Merge helpers ---

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
    if "management" in stored_spec:
        stored_mgmt = (stored_spec.get("management") or {}).get("enabled", False)
        merged_mgmt = (merged_spec.get("management") or {}).get("enabled", False)
        if merged_mgmt != stored_mgmt:
            errors.append(make_error(
                "spec.management.enabled", "immutable",
                "field 'spec.management.enabled' is immutable after creation",
            ))
    return errors


# --- Migration lifecycle helpers ---

def check_migration_guards(stored, update_spec):
    """Return errors if a locked field is being changed during an active migration."""
    errors = []
    conditions = stored.get("status", {}).get("conditions", [])
    if not is_migration_active(conditions):
        return errors
    stored_runtime = stored.get("spec", {}).get("runtime")
    new_runtime = update_spec.get("runtime")
    if new_runtime is not None and new_runtime != stored_runtime:
        errors.append(make_error(
            "spec.runtime", "invalid",
            "cannot change runtime version while a migration is in progress",
        ))
    stored_strategy = stored.get("spec", {}).get("migration", {}).get("strategy")
    new_strategy = (update_spec.get("migration") or {}).get("strategy")
    if new_strategy is not None and new_strategy != stored_strategy:
        errors.append(make_error(
            "spec.migration.strategy", "invalid",
            "cannot change migration strategy while a migration is in progress",
        ))
    return errors


def check_version_change_rules(stored_runtime, new_runtime, strategy, spec):
    """Return errors for version-change constraint violations. Called only when a version change is detected."""
    errors = []
    src = parse_runtime_version(stored_runtime)
    tgt = parse_runtime_version(new_runtime)
    if src is None or tgt is None:
        return errors

    # Downgrade check — all strategies
    if tgt < src:
        errors.append(make_error(
            "spec.runtime", "invalid",
            f"version downgrade from '{stored_runtime}' to '{new_runtime}' is not allowed",
        ))
        return errors  # no further checks make sense after downgrade error

    # RollingPatch rules (both checked independently)
    if strategy == "RollingPatch":
        if (tgt[0], tgt[1]) != (src[0], src[1]):
            errors.append(make_error(
                "spec.runtime", "invalid",
                f"RollingPatch requires the same major and minor version; "
                f"source is {src[0]}.{src[1]}.x but target is {tgt[0]}.{tgt[1]}.x",
            ))
        if tgt[0] < 4:
            errors.append(make_error(
                "spec.runtime", "invalid",
                f"RollingPatch requires target major version to be at least 4; got {tgt[0]}",
            ))

    return errors


def start_migration(resource, source_runtime, target_runtime, strategy):
    """Mutate resource in-place to record migration start."""
    conditions = resource["status"].get("conditions", [])
    conditions = set_condition(conditions, "Migration", "True", "")
    resource["status"]["conditions"] = conditions
    resource["status"]["migration"] = {
        "sourceRuntime": source_runtime,
        "targetRuntime": target_runtime,
        "stage": MIGRATION_STAGE_SEQUENCES[strategy][0],
    }
    resource["status"]["stable"] = False


def complete_migration(resource):
    """Mutate resource in-place to record migration completion."""
    conditions = resource["status"].get("conditions", [])
    conditions = remove_condition(conditions, "Migration")
    resource["status"]["conditions"] = conditions
    resource["status"].pop("migration", None)
    resource["status"]["stable"] = compute_stable(conditions)


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


# --- One-shot resource shared helpers ---

def run_state_guard(resource):
    """Return errors if resource is not in Initializing state."""
    state = resource.get("status", {}).get("state", "")
    if state != "Initializing":
        return [make_error(
            "status.state", "invalid",
            f"resource is in state '{state}', expected 'Initializing'",
        )]
    return []


def full_spec_immutability_check(stored_spec, incoming_spec):
    """Return immutable errors for any field in incoming_spec that differs from stored_spec."""
    if not isinstance(incoming_spec, dict):
        return []
    errors = []
    for key, value in incoming_spec.items():
        if key not in stored_spec:
            errors.append(make_error(
                f"spec.{key}", "immutable",
                f"field 'spec.{key}' is immutable after creation",
            ))
        elif stored_spec.get(key) != value:
            errors.append(make_error(
                f"spec.{key}", "immutable",
                f"field 'spec.{key}' is immutable after creation",
            ))
    return errors


def validate_resource_name(metadata):
    """Return (name, errors) — shared name validation for all resource kinds."""
    errors = []
    name = None
    raw_name = (metadata or {}).get("name")
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


def validate_meshref(spec, mesh_store):
    """Return (mesh_ref, errors) — validates spec.meshRef against the mesh store."""
    errors = []
    mesh_ref = None
    raw_mesh_ref = (spec or {}).get("meshRef")
    if not raw_mesh_ref:
        errors.append(make_error("spec.meshRef", "invalid", "meshRef is required and must reference an existing mesh"))
    elif not isinstance(raw_mesh_ref, str):
        errors.append(make_error("spec.meshRef", "invalid", "meshRef must be a non-empty string"))
    elif raw_mesh_ref not in mesh_store:
        errors.append(make_error("spec.meshRef", "invalid", f"mesh '{raw_mesh_ref}' not found"))
    else:
        mesh_ref = raw_mesh_ref
    return mesh_ref, errors


def validate_op_resources(spec):
    """Validate resources.memory / resources.cpu for operational resources. Returns (memory, cpu, errors)."""
    errors = []
    raw_resources = (spec or {}).get("resources")
    has_resources = isinstance(raw_resources, dict)

    has_memory = has_resources and "memory" in raw_resources
    memory = None
    if not has_memory:
        memory = {"limit": "1Gi", "request": "1Gi"}
    else:
        raw_memory = raw_resources["memory"]
        if not isinstance(raw_memory, dict):
            errors.append(make_error("spec.resources.memory", "invalid", "memory must be an object"))
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
                        elif mem_req_val > mem_limit_val:
                            errors.append(make_error(
                                "spec.resources.memory.request", "invalid",
                                "memory request must not exceed limit",
                            ))
                            mem_req_val = None
                    if not errors or all(e["field"] not in ("spec.resources.memory.limit", "spec.resources.memory.request") for e in errors):
                        if mem_req_val is not None:
                            memory = {"limit": mem_limit_str, "request": mem_req_str}

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
                        elif cpu_req_val > cpu_limit_val:
                            errors.append(make_error(
                                "spec.resources.cpu.request", "invalid",
                                "CPU request must not exceed limit",
                            ))
                            cpu_req_val = None
                    if cpu_req_val is not None:
                        cpu = {"limit": cpu_limit_str, "request": cpu_req_str}

    return memory, cpu, errors


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
        status["stable"] = True
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

    result, errs, warns = validate_and_build(doc)
    if errs:
        error_out(errs)
        return

    name = result["metadata"]["name"]
    store = load_store()
    if name in store:
        error_out([make_error("metadata.name", "duplicate", f"mesh '{name}' already exists")])
        return

    result["status"] = build_initial_status(result["spec"]["instances"])

    if result["spec"].get("regions"):
        _st = result["status"]
        _st["conditions"] = set_condition(_st["conditions"], "DiscoveryRelayReady", "False", "")
        _st["conditions"] = set_condition(_st["conditions"], "RegionViewFormed", "False", "")

    store[name] = result
    save_store(store)
    success_out(result, warns)


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

    resource = copy.deepcopy(store[args.name])
    status = resource["status"]
    conditions = status.get("conditions", [])
    had_scaling = any(c["type"] == "Scaling" for c in conditions)
    status["conditions"] = [c for c in conditions if c["type"] not in TRANSIENT_CONDITION_TYPES]

    if had_scaling and status.get("state") == "Running":
        n = resource["spec"]["instances"]
        status["instances"] = {"ready": n, "starting": 0, "stopped": 0}
    status["stable"] = compute_stable(status["conditions"])

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


def cmd_update(args):
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

    # Resolve transient Scaling before merging
    resolved_conditions = [c for c in stored_conditions if c["type"] not in TRANSIENT_CONDITION_TYPES]
    resolved_status = copy.deepcopy(stored["status"])
    resolved_status["conditions"] = resolved_conditions
    if had_scaling and resolved_status.get("state") == "Running":
        n = stored["spec"]["instances"]
        resolved_status["instances"] = {"ready": n, "starting": 0, "stopped": 0}
    resolved_status["stable"] = compute_stable(resolved_conditions)

    old_instances = stored["spec"]["instances"]
    has_graceful = any(c["type"] == "GracefulShutdown" for c in resolved_conditions)

    update_spec = doc.get("spec") or {}
    if not isinstance(update_spec, dict):
        update_spec = {}

    raw_instances_in_update = update_spec.get("instances")

    # Migration guards — checked before merge/validation, accumulated with other errors
    guard_errors = check_migration_guards(stored, update_spec)

    # Deep merge spec
    merged_spec = deep_merge(stored["spec"], update_spec)

    # configBundleRef: explicit null in update means clear (deep_merge keeps stored value for None)
    if "configBundleRef" in update_spec and update_spec["configBundleRef"] is None:
        merged_spec.pop("configBundleRef", None)

    # Also merge metadata.tags from update doc into merged_doc (not part of spec)
    update_metadata_tags = (doc.get("metadata") or {}).get("tags")

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

    # Build merged metadata (merge tags from update when provided)
    stored_tags = (stored.get("metadata") or {}).get("tags")
    if update_metadata_tags is not None:
        merged_tags = update_metadata_tags
    else:
        merged_tags = stored_tags
    merged_metadata = {"name": raw_name}
    if merged_tags is not None:
        merged_metadata["tags"] = merged_tags

    merged_doc = {"metadata": merged_metadata, "spec": merged_spec}

    result, val_errs, warns = validate_and_build(merged_doc, is_update=True)

    # Combine guard errors + validation errors; report all
    all_errors = guard_errors + val_errs
    if all_errors:
        error_out(all_errors)
        return

    # Version change rules (only when no validation errors and no migration active)
    stored_runtime = stored["spec"].get("runtime")
    new_runtime = result["spec"].get("runtime")
    version_errors = []
    is_version_change = (
        stored_runtime is not None
        and new_runtime is not None
        and stored_runtime != new_runtime
    )
    if is_version_change and not is_migration_active(resolved_conditions):
        strategy = result["spec"].get("migration", {}).get("strategy", "FullStop")
        version_errors = check_version_change_rules(stored_runtime, new_runtime, strategy, result["spec"])
    if version_errors:
        error_out(version_errors)
        return

    new_instances = result["spec"]["instances"]
    transition = detect_lifecycle(old_instances, new_instances, resolved_conditions)
    new_status = apply_lifecycle(transition, resolved_status, old_instances, new_instances)

    # Preserve status.migration from resolved state (guards already blocked changes)
    if "migration" in resolved_status:
        new_status["migration"] = resolved_status["migration"]

    result["status"] = new_status

    # Start migration when a version change is detected
    if is_version_change and not is_migration_active(resolved_conditions):
        strategy = result["spec"].get("migration", {}).get("strategy", "FullStop")
        start_migration(result, stored_runtime, new_runtime, strategy)

    # Manage region conditions
    if result["spec"].get("regions"):
        _conds = result["status"].get("conditions", [])
        _existing_types = {c["type"] for c in _conds}
        if "DiscoveryRelayReady" not in _existing_types:
            _conds = set_condition(_conds, "DiscoveryRelayReady", "False", "")
        if "RegionViewFormed" not in _existing_types:
            _conds = set_condition(_conds, "RegionViewFormed", "False", "")
        result["status"]["conditions"] = _conds
    else:
        _conds = sorted(
            [c for c in result["status"].get("conditions", [])
             if c["type"] not in ("DiscoveryRelayReady", "RegionViewFormed")],
            key=lambda c: c["type"],
        )
        result["status"]["conditions"] = _conds

    # configBundleRef change → transient configRefresh (not persisted)
    _stored_cbr = stored["spec"].get("configBundleRef")
    _new_cbr = result["spec"].get("configBundleRef")
    _config_refresh = None
    if _stored_cbr != _new_cbr:
        _config_refresh = {"currentRef": _new_cbr, "pending": True, "previousRef": _stored_cbr}

    store[raw_name] = result
    save_store(store)

    if _config_refresh is not None:
        result["status"]["configRefresh"] = _config_refresh
    success_out(result, warns)


def cmd_migrate(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return

    resource = copy.deepcopy(store[name])
    conditions = resource["status"].get("conditions", [])
    if not is_migration_active(conditions):
        error_out([make_error(
            "status.migration", "invalid",
            f"no active migration for mesh '{name}'",
        )])
        return

    migration = resource["status"]["migration"]
    strategy = resource["spec"].get("migration", {}).get("strategy", "FullStop")
    stages = MIGRATION_STAGE_SEQUENCES.get(strategy, ["Migrate"])
    current_stage = migration["stage"]

    if current_stage == stages[-1]:
        # Final stage — complete the migration
        complete_migration(resource)
    else:
        # Advance to next stage
        idx = stages.index(current_stage)
        migration["stage"] = stages[idx + 1]

    store[name] = resource
    save_store(store)
    print_json(format_resource_for_output(resource))


def cmd_shell(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return
    exposure = store[name].get("spec", {}).get("exposure")
    if exposure is None:
        error_out([make_error("spec.exposure", "invalid", f"mesh '{name}' has no exposure configured")])
        return
    print_json(compute_connection_details(name, exposure))


def cmd_rollback(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return

    resource = copy.deepcopy(store[name])
    conditions = resource["status"].get("conditions", [])
    if not is_migration_active(conditions):
        error_out([make_error(
            "status.migration", "invalid",
            f"no active migration for mesh '{name}'",
        )])
        return

    strategy = resource["spec"].get("migration", {}).get("strategy", "FullStop")
    if strategy != "LiveMigration":
        error_out([make_error(
            "spec.migration.strategy", "invalid",
            f"rollback is only supported for LiveMigration strategy",
        )])
        return

    complete_migration(resource)
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


# --- Task validation ---

def validate_task(doc, mesh_store):
    errors = []
    if not isinstance(doc, dict) or "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    metadata = doc["metadata"] if isinstance(doc["metadata"], dict) else {}
    spec = doc["spec"] if isinstance(doc["spec"], dict) else {}

    name, name_errs = validate_resource_name(metadata)
    errors.extend(name_errs)

    mesh_ref, mesh_errs = validate_meshref(spec, mesh_store)
    errors.extend(mesh_errs)

    has_inline = "inline" in spec
    has_bundle_ref = "bundleRef" in spec
    inline_val = spec.get("inline")
    bundle_ref_val = spec.get("bundleRef")

    exclusive_ok = True
    if has_inline and has_bundle_ref:
        errors.append(make_error("spec", "invalid", "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"))
        exclusive_ok = False
    elif not has_inline and not has_bundle_ref:
        errors.append(make_error("spec", "invalid", "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"))
        exclusive_ok = False
    elif has_inline and (inline_val is None or inline_val == ""):
        errors.append(make_error("spec", "invalid", "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"))
        exclusive_ok = False
    elif has_bundle_ref and (bundle_ref_val is None or bundle_ref_val == ""):
        errors.append(make_error("spec", "invalid", "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"))
        exclusive_ok = False

    if errors:
        return None, errors

    out_spec = {"meshRef": mesh_ref}
    if has_inline and exclusive_ok:
        out_spec["inline"] = inline_val
    elif has_bundle_ref and exclusive_ok:
        out_spec["bundleRef"] = bundle_ref_val

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
    print_json(result)


def task_cmd_list(_args):
    task_store = load_task_store()
    items = sorted(task_store.values(), key=lambda r: r["metadata"]["name"])
    print_json(items)


def task_cmd_describe(args):
    task_store = load_task_store()
    if args.name not in task_store:
        error_out([make_error("metadata.name", "not_found", f"task '{args.name}' not found")])
        return
    print_json(task_store[args.name])


def task_cmd_update(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
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
    incoming_spec = doc.get("spec") or {}
    if not isinstance(incoming_spec, dict):
        incoming_spec = {}

    imm_errs = full_spec_immutability_check(stored["spec"], incoming_spec)
    if imm_errs:
        error_out(imm_errs)
        return

    print_json(stored)


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
    errs = run_state_guard(resource)
    if errs:
        error_out(errs)
        return

    resource["status"]["state"] = "Running"

    inline = resource["spec"].get("inline")
    if inline is not None:
        lines = inline.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("FAIL:"):
                reason = line[len("FAIL:"):].strip()
                resource["status"]["state"] = "Failed"
                resource["status"]["detail"] = f"command {i} failed: {reason}"
                task_store[name] = resource
                save_task_store(task_store)
                print_json(resource)
                return

    resource["status"]["state"] = "Succeeded"
    resource["status"].pop("detail", None)
    task_store[name] = resource
    save_task_store(task_store)
    print_json(resource)


# --- Snapshot validation ---

def validate_snapshot(doc, mesh_store):
    errors = []
    if not isinstance(doc, dict) or "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    metadata = doc["metadata"] if isinstance(doc["metadata"], dict) else {}
    spec = doc["spec"] if isinstance(doc["spec"], dict) else {}

    name, name_errs = validate_resource_name(metadata)
    errors.extend(name_errs)

    mesh_ref, mesh_errs = validate_meshref(spec, mesh_store)
    errors.extend(mesh_errs)

    memory, cpu, res_errs = validate_op_resources(spec)
    errors.extend(res_errs)

    if errors:
        return None, errors

    out_spec = {
        "meshRef": mesh_ref,
        "resources": {"memory": memory},
    }
    if cpu is not None:
        out_spec["resources"]["cpu"] = cpu
    scope = spec.get("scope")
    if scope is not None:
        out_spec["scope"] = scope
    storage = spec.get("storage")
    if isinstance(storage, dict):
        out_spec["storage"] = storage

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
    print_json(result)


def snapshot_cmd_list(_args):
    snapshot_store = load_snapshot_store()
    items = sorted(snapshot_store.values(), key=lambda r: r["metadata"]["name"])
    print_json(items)


def snapshot_cmd_describe(args):
    snapshot_store = load_snapshot_store()
    if args.name not in snapshot_store:
        error_out([make_error("metadata.name", "not_found", f"snapshot '{args.name}' not found")])
        return
    print_json(snapshot_store[args.name])


def snapshot_cmd_update(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
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
    incoming_spec = doc.get("spec") or {}
    if not isinstance(incoming_spec, dict):
        incoming_spec = {}

    imm_errs = full_spec_immutability_check(stored["spec"], incoming_spec)
    if imm_errs:
        error_out(imm_errs)
        return

    print_json(stored)


def snapshot_cmd_delete(args):
    snapshot_store = load_snapshot_store()
    name = args.name
    if name not in snapshot_store:
        error_out([make_error("metadata.name", "not_found", f"snapshot '{name}' not found")])
        return

    recovery_store = load_recovery_store()
    dependent = sorted(
        r["metadata"]["name"] for r in recovery_store.values()
        if r["spec"].get("snapshotRef") == name
    )
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
    errs = run_state_guard(resource)
    if errs:
        error_out(errs)
        return

    resource["status"]["state"] = "Running"

    mesh_store = load_store()
    mesh_ref = resource["spec"]["meshRef"]
    mesh = mesh_store.get(mesh_ref)
    stable = mesh is not None and mesh.get("status", {}).get("stable", False)

    if not stable:
        resource["status"]["state"] = "Unknown"
        resource["status"]["detail"] = f"mesh '{mesh_ref}' is not stable"
        resource["status"].pop("storageRef", None)
    else:
        resource["status"]["state"] = "Succeeded"
        resource["status"]["storageRef"] = f"snapshot-{name}-storage"
        resource["status"].pop("detail", None)

    snapshot_store[name] = resource
    save_snapshot_store(snapshot_store)
    print_json(resource)


# --- Recovery validation ---

def validate_recovery(doc, mesh_store, snapshot_store):
    errors = []
    if not isinstance(doc, dict) or "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    metadata = doc["metadata"] if isinstance(doc["metadata"], dict) else {}
    spec = doc["spec"] if isinstance(doc["spec"], dict) else {}

    name, name_errs = validate_resource_name(metadata)
    errors.extend(name_errs)

    mesh_ref, mesh_errs = validate_meshref(spec, mesh_store)
    errors.extend(mesh_errs)

    snapshot_ref = None
    raw_snapshot_ref = spec.get("snapshotRef")
    if not raw_snapshot_ref:
        errors.append(make_error("spec.snapshotRef", "invalid", "snapshotRef is required and must reference an existing snapshot"))
    elif not isinstance(raw_snapshot_ref, str):
        errors.append(make_error("spec.snapshotRef", "invalid", "snapshotRef must be a non-empty string"))
    elif raw_snapshot_ref not in snapshot_store:
        errors.append(make_error("spec.snapshotRef", "invalid", f"snapshot '{raw_snapshot_ref}' not found"))
    else:
        snapshot_ref = raw_snapshot_ref
        if mesh_ref is not None:
            snap_mesh_ref = snapshot_store[snapshot_ref]["spec"].get("meshRef")
            if snap_mesh_ref != mesh_ref:
                errors.append(make_error(
                    "spec.snapshotRef", "invalid",
                    f"snapshot '{snapshot_ref}' belongs to mesh '{snap_mesh_ref}', not '{mesh_ref}'",
                ))

    memory, cpu, res_errs = validate_op_resources(spec)
    errors.extend(res_errs)

    if errors:
        return None, errors

    out_spec = {
        "meshRef": mesh_ref,
        "snapshotRef": snapshot_ref,
        "resources": {"memory": memory},
    }
    if cpu is not None:
        out_spec["resources"]["cpu"] = cpu
    scope = spec.get("scope")
    if scope is not None:
        out_spec["scope"] = scope

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
    print_json(result)


def recovery_cmd_list(_args):
    recovery_store = load_recovery_store()
    items = sorted(recovery_store.values(), key=lambda r: r["metadata"]["name"])
    print_json(items)


def recovery_cmd_describe(args):
    recovery_store = load_recovery_store()
    if args.name not in recovery_store:
        error_out([make_error("metadata.name", "not_found", f"recovery '{args.name}' not found")])
        return
    print_json(recovery_store[args.name])


def recovery_cmd_update(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
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
    incoming_spec = doc.get("spec") or {}
    if not isinstance(incoming_spec, dict):
        incoming_spec = {}

    imm_errs = full_spec_immutability_check(stored["spec"], incoming_spec)
    if imm_errs:
        error_out(imm_errs)
        return

    print_json(stored)


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
    errs = run_state_guard(resource)
    if errs:
        error_out(errs)
        return

    resource["status"]["state"] = "Running"

    mesh_store = load_store()
    mesh_ref = resource["spec"]["meshRef"]
    mesh = mesh_store.get(mesh_ref)
    stable = mesh is not None and mesh.get("status", {}).get("stable", False)

    if not stable:
        resource["status"]["state"] = "Unknown"
        resource["status"]["detail"] = f"mesh '{mesh_ref}' is not stable"
    else:
        resource["status"]["state"] = "Succeeded"
        resource["status"].pop("detail", None)

    recovery_store[name] = resource
    save_recovery_store(recovery_store)
    print_json(resource)


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
