#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import tempfile

import yaml

STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.json")

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
RUNTIME_RE = re.compile(r"^\d+\.\d+\.\d+$")
MEMORY_UNITS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4}


# --- Output helpers (tasks 4.1, 4.2) ---

def print_json(obj):
    print(json.dumps(obj))


def make_error(field, type_, message):
    return {"field": field, "type": type_, "message": message}


def error_out(errors):
    print_json({"errors": errors})


# --- Store (task 1.3) ---

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


# --- YAML loader (task 2.1) ---

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


# --- Quantity parsers (task 2.7) ---

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


# --- autoScaling scanner (task 2.4) ---

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


# --- Validation + default application (tasks 2.2-2.11, 4.3) ---

def validate_and_build(doc):
    errors = []

    # task 2.2: top-level structure
    if "metadata" not in doc or "spec" not in doc:
        return None, [make_error("", "parse", "document must have 'metadata' and 'spec' keys")]

    metadata = doc["metadata"]
    spec = doc["spec"]

    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(spec, dict):
        spec = {}

    # task 2.3: metadata.name
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

    # task 2.4: forbidden autoScaling under spec
    for fp in find_autoscaling_paths(spec, "spec"):
        errors.append(make_error(fp, "forbidden", f"field '{fp}' is not allowed"))

    # task 2.5: spec.instances
    instances = 1
    raw_instances = spec.get("instances")
    if raw_instances is not None:
        if isinstance(raw_instances, bool) or not isinstance(raw_instances, int) or raw_instances < 1:
            errors.append(make_error("spec.instances", "invalid", "instances must be a positive integer"))
            instances = None
        else:
            instances = raw_instances

    # task 2.6: spec.runtime
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

    raw_resources = spec.get("resources")
    has_resources = isinstance(raw_resources, dict)

    # task 2.8: spec.resources.memory
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

    # task 2.9: spec.resources.cpu
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

    # task 2.10: spec.access.authentication.enabled
    raw_access = spec.get("access")
    raw_auth = raw_access.get("authentication") if isinstance(raw_access, dict) else None
    auth_enabled = True
    if isinstance(raw_auth, dict) and "enabled" in raw_auth:
        auth_enabled = raw_auth["enabled"]

    # task 2.11: spec.migration.strategy
    strategy = "FullStop"
    raw_migration = spec.get("migration")
    if isinstance(raw_migration, dict) and "strategy" in raw_migration:
        raw_strategy = raw_migration["strategy"]
        if raw_strategy != "FullStop":
            errors.append(make_error(
                "spec.migration.strategy", "invalid",
                f"migration.strategy must be 'FullStop', got {raw_strategy!r}",
            ))
            strategy = None

    if errors:
        return None, errors

    # Build resource (task 4.3)
    out_spec = {
        "instances": instances,
        "resources": {"memory": memory},
        "access": {"authentication": {"enabled": auth_enabled}},
        "migration": {"strategy": strategy},
    }
    if has_runtime:
        out_spec["runtime"] = runtime
    if has_cpu:
        out_spec["resources"]["cpu"] = cpu

    return {
        "metadata": {"name": name},
        "spec": out_spec,
        "status": {"state": "Running"},
    }, []


# --- Command handlers (tasks 3.1-3.4) ---

def cmd_create(args):
    doc, errs = load_yaml_file(args.file)
    if errs:
        error_out(errs)
        return

    resource, errs = validate_and_build(doc)
    if errs:
        error_out(errs)
        return

    name = resource["metadata"]["name"]
    store = load_store()
    if name in store:
        error_out([make_error("metadata.name", "duplicate", f"mesh '{name}' already exists")])
        return

    store[name] = resource
    save_store(store)
    print_json(resource)


def cmd_list(_args):
    store = load_store()
    items = sorted(
        [{"name": r["metadata"]["name"], "status": r["status"]} for r in store.values()],
        key=lambda x: x["name"],
    )
    print_json(items)


def cmd_describe(args):
    store = load_store()
    if args.name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{args.name}' not found")])
        return
    print_json(store[args.name])


def cmd_delete(args):
    store = load_store()
    name = args.name
    if name not in store:
        error_out([make_error("metadata.name", "not_found", f"mesh '{name}' not found")])
        return
    del store[name]
    save_store(store)
    # task 4.4
    print_json({"message": f"mesh '{name}' deleted", "metadata": {"name": name}})


# --- CLI entry point (task 1.2) ---

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

    args = parser.parse_args()

    if args.command != "mesh" or not args.operation:
        parser.print_usage(sys.stderr)
        sys.exit(1)

    {"create": cmd_create, "list": cmd_list, "describe": cmd_describe, "delete": cmd_delete}[
        args.operation
    ](args)


if __name__ == "__main__":
    main()
