"""Tests for checkpoint 8: multi-region topology and operational policies."""
import json
import os
import tempfile

import pytest
import yaml

STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.json")


def _reset_store():
    with open(STORE_PATH, "w") as f:
        json.dump({}, f)


def _run(args):
    """Run meshctl and return parsed JSON output."""
    import subprocess
    result = subprocess.run(
        ["uv", "run", "--project", "/app", "meshctl.py"] + args,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    lines = result.stdout.strip().splitlines()
    payload = next((l for l in lines if l.startswith("{")), None)
    if payload:
        return json.loads(payload)
    if result.stdout.strip():
        return json.loads(result.stdout.strip())
    return {}


def _yaml_file(data):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, f)
    f.close()
    return f.name


def _create(data):
    path = _yaml_file(data)
    try:
        return _run(["mesh", "create", "-f", path])
    finally:
        os.unlink(path)


def _update(data):
    path = _yaml_file(data)
    try:
        return _run(["mesh", "update", "-f", path])
    finally:
        os.unlink(path)


def _describe(name):
    return _run(["mesh", "describe", name])


@pytest.fixture(autouse=True)
def reset():
    _reset_store()
    yield
    _reset_store()


# --- 9.1: Single-region mesh — defaults present ---

def test_single_region_no_region_conditions():
    r = _create({"metadata": {"name": "mx"}, "spec": {"instances": 1}})
    assert "errors" not in r
    cond_types = {c["type"] for c in r["status"]["conditions"]}
    assert "DiscoveryRelayReady" not in cond_types
    assert "RegionViewFormed" not in cond_types


def test_single_region_placement_defaults():
    r = _create({"metadata": {"name": "mx"}, "spec": {"instances": 1}})
    assert r["spec"]["placement"] == {"affinity": {"type": "preferred", "scope": "node"}}


def test_single_region_telemetry_probe_default():
    r = _create({"metadata": {"name": "mx"}, "spec": {"instances": 1}})
    assert r["status"]["telemetryProbe"] == {"enabled": True}


# --- 9.2: Multi-region mesh create ---

def test_multi_region_create_success():
    r = _create({
        "metadata": {"name": "mr"},
        "spec": {
            "instances": 1,
            "regions": {
                "local": {
                    "name": "us-east",
                    "expose": {"type": "Internal"},
                    "maxRelayNodes": 2,
                },
                "remotes": [
                    {"name": "eu-west", "url": "https://eu.example.com"},
                ],
            },
        },
    })
    assert "errors" not in r
    assert r["spec"]["regions"]["local"]["name"] == "us-east"
    assert r["spec"]["regions"]["local"]["expose"]["type"] == "Internal"
    assert r["spec"]["regions"]["local"]["maxRelayNodes"] == 2
    assert r["spec"]["regions"]["remotes"][0]["name"] == "eu-west"


def test_multi_region_region_conditions_present():
    r = _create({
        "metadata": {"name": "mr"},
        "spec": {"instances": 1, "regions": {"local": {"name": "r1", "expose": {"type": "Internal"}}}},
    })
    cond_types = {c["type"] for c in r["status"]["conditions"]}
    assert "DiscoveryRelayReady" in cond_types
    assert "RegionViewFormed" in cond_types
    for c in r["status"]["conditions"]:
        if c["type"] in ("DiscoveryRelayReady", "RegionViewFormed"):
            assert c["status"] == "False"
            assert c["message"] == ""


def test_multi_region_conditions_sorted():
    r = _create({
        "metadata": {"name": "mr"},
        "spec": {"instances": 1, "regions": {"local": {"name": "r1", "expose": {"type": "Internal"}}}},
    })
    types = [c["type"] for c in r["status"]["conditions"]]
    assert types == sorted(types)


def test_multi_region_discovery_defaulted():
    r = _create({
        "metadata": {"name": "mr"},
        "spec": {"instances": 1, "regions": {"local": {"name": "r1", "expose": {"type": "Internal"}}}},
    })
    disc = r["spec"]["regions"]["local"]["discovery"]
    assert disc["type"] == "relay"
    assert disc["heartbeat"]["interval"] == 10000
    assert disc["heartbeat"]["timeout"] == 30000
    assert disc["heartbeat"]["enabled"] is True


def test_multi_region_stable_unaffected_by_region_conditions():
    r = _create({
        "metadata": {"name": "mr"},
        "spec": {"instances": 1, "regions": {"local": {"name": "r1", "expose": {"type": "Internal"}}}},
    })
    assert r["status"]["stable"] is True


# --- 9.3: Missing spec.regions.local ---

def test_missing_local_produces_required_error():
    r = _create({"metadata": {"name": "mx"}, "spec": {"instances": 1, "regions": {}}})
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.regions.local") == "required"


# --- 9.4: Invalid expose type ---

def test_invalid_expose_type():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "regions": {"local": {"name": "r1", "expose": {"type": "LoadBalancer"}}}},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.regions.local.expose.type") == "invalid"


def test_missing_expose_type():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "regions": {"local": {"name": "r1", "expose": {}}}},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.regions.local.expose.type") == "required"


# --- 9.5: Gateway without transportKeyStore ---

def test_gateway_without_transport_key_store():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "regions": {
                "local": {
                    "name": "r1",
                    "expose": {"type": "Gateway"},
                    "encryption": {"protocol": "TLSv1.3"},
                }
            },
        },
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.regions.local.encryption.transportKeyStore") == "required"


# --- 9.6: Heartbeat interval >= timeout ---

def test_heartbeat_interval_equal_timeout():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "regions": {
                "local": {
                    "name": "r1",
                    "expose": {"type": "Internal"},
                    "discovery": {"type": "relay", "heartbeat": {"interval": 10000, "timeout": 10000}},
                }
            },
        },
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.regions.local.discovery.heartbeat") == "invalid"


def test_heartbeat_interval_greater_than_timeout():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "regions": {
                "local": {
                    "name": "r1",
                    "expose": {"type": "Internal"},
                    "discovery": {"type": "relay", "heartbeat": {"interval": 30000, "timeout": 10000}},
                }
            },
        },
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.regions.local.discovery.heartbeat") == "invalid"


# --- 9.7: Duplicate remote name ---

def test_duplicate_remote_name():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "regions": {
                "local": {"name": "r1", "expose": {"type": "Internal"}},
                "remotes": [
                    {"name": "eu", "url": "https://eu.example.com"},
                    {"name": "eu", "url": "https://eu2.example.com"},
                ],
            },
        },
    })
    errs = [(e["field"], e["type"]) for e in r["errors"]]
    assert ("spec.regions.remotes[1].name", "duplicate") in errs


# --- 9.8: LiveMigration with/without regions ---

def test_live_migration_rejected_with_regions():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "migration": {"strategy": "LiveMigration"},
            "regions": {"local": {"name": "r1", "expose": {"type": "Internal"}}},
        },
    })
    errs = {e["field"]: e["message"] for e in r["errors"]}
    assert "LiveMigration strategy is not supported with multi-region topology" in errs.get("spec.migration.strategy", "")


def test_live_migration_accepted_without_regions():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "migration": {"strategy": "LiveMigration"}},
    })
    assert "errors" not in r
    assert r["spec"]["migration"]["strategy"] == "LiveMigration"


# --- 9.9: metadata.tags and status.telemetryProbe ---

def test_tags_persisted():
    r = _create({
        "metadata": {"name": "mx", "tags": {"env": "prod", "team": "platform"}},
        "spec": {"instances": 1},
    })
    assert r["metadata"]["tags"] == {"env": "prod", "team": "platform"}


def test_telemetry_probe_disabled():
    r = _create({
        "metadata": {"name": "mx", "tags": {"mesh.io/telemetry": "false"}},
        "spec": {"instances": 1},
    })
    assert r["status"]["telemetryProbe"] == {"enabled": False}


def test_telemetry_probe_with_labels():
    r = _create({
        "metadata": {
            "name": "mx",
            "tags": {"mesh.io/targetLabels": "region,env", "mesh.io/instanceLabels": "pod"},
        },
        "spec": {"instances": 1},
    })
    probe = r["status"]["telemetryProbe"]
    assert probe["enabled"] is True
    assert probe["labels"]["targetLabels"] == ["region", "env"]
    assert probe["labels"]["instanceLabels"] == ["pod"]


def test_telemetry_probe_label_order_preserved():
    r = _create({
        "metadata": {"name": "mx", "tags": {"mesh.io/targetLabels": "zone,region,env"}},
        "spec": {"instances": 1},
    })
    assert r["status"]["telemetryProbe"]["labels"]["targetLabels"] == ["zone", "region", "env"]


def test_telemetry_probe_disabled_ignores_label_tags():
    r = _create({
        "metadata": {"name": "mx", "tags": {"mesh.io/telemetry": "false", "mesh.io/targetLabels": "region"}},
        "spec": {"instances": 1},
    })
    assert r["status"]["telemetryProbe"] == {"enabled": False}
    assert "labels" not in r["status"]["telemetryProbe"]


def test_telemetry_probe_present_in_describe():
    _create({"metadata": {"name": "mx"}, "spec": {"instances": 1}})
    r = _describe("mx")
    assert "telemetryProbe" in r["status"]


# --- 9.10: spec.placement defaults and validation ---

def test_placement_defaults_when_absent():
    r = _create({"metadata": {"name": "mx"}, "spec": {"instances": 1}})
    assert r["spec"]["placement"] == {"affinity": {"type": "preferred", "scope": "node"}}


def test_placement_partial_defaults():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "placement": {"affinity": {"type": "required"}}},
    })
    assert r["spec"]["placement"]["affinity"]["type"] == "required"
    assert r["spec"]["placement"]["affinity"]["scope"] == "node"


def test_placement_invalid_type():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "placement": {"affinity": {"type": "strict"}}},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.placement.affinity.type") == "invalid"


def test_placement_invalid_scope():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "placement": {"affinity": {"scope": "rack"}}},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.placement.affinity.scope") == "invalid"


def test_placement_non_object():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "placement": "invalid"},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.placement") == "invalid"


def test_placement_always_in_describe():
    _create({"metadata": {"name": "mx"}, "spec": {"instances": 1}})
    r = _describe("mx")
    assert "placement" in r["spec"]
    assert r["spec"]["placement"]["affinity"]["type"] == "preferred"


# --- 9.11: configBundleRef create/update/describe ---

def test_config_bundle_ref_on_create():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "configBundleRef": "bundle-v1"},
    })
    assert r["spec"]["configBundleRef"] == "bundle-v1"


def test_config_bundle_ref_null_invalid_on_create():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "configBundleRef": None},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.configBundleRef") == "invalid"


def test_config_bundle_ref_change_produces_refresh():
    _create({"metadata": {"name": "mx"}, "spec": {"instances": 1, "configBundleRef": "bundle-v1"}})
    r = _update({"metadata": {"name": "mx"}, "spec": {"configBundleRef": "bundle-v2"}})
    assert r["spec"]["configBundleRef"] == "bundle-v2"
    refresh = r["status"]["configRefresh"]
    assert refresh["currentRef"] == "bundle-v2"
    assert refresh["previousRef"] == "bundle-v1"
    assert refresh["pending"] is True


def test_config_bundle_ref_omit_on_update_keeps_value():
    _create({"metadata": {"name": "mx"}, "spec": {"instances": 1, "configBundleRef": "bundle-v1"}})
    r = _update({"metadata": {"name": "mx"}, "spec": {"instances": 2}})
    assert r["spec"]["configBundleRef"] == "bundle-v1"
    assert "configRefresh" not in r["status"]


def test_config_bundle_ref_null_clears():
    _create({"metadata": {"name": "mx"}, "spec": {"instances": 1, "configBundleRef": "bundle-v1"}})
    r = _update({"metadata": {"name": "mx"}, "spec": {"configBundleRef": None}})
    assert "configBundleRef" not in r["spec"]
    assert r["status"]["configRefresh"]["currentRef"] is None


def test_config_bundle_ref_absent_from_describe():
    _create({"metadata": {"name": "mx"}, "spec": {"instances": 1, "configBundleRef": "bundle-v1"}})
    _update({"metadata": {"name": "mx"}, "spec": {"configBundleRef": "bundle-v2"}})
    r = _describe("mx")
    assert "configRefresh" not in r["status"]


# --- 9.12: extensions ---

def test_extensions_url_only_valid():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "extensions": [{"url": "https://example.com/ext"}]},
    })
    assert "errors" not in r
    assert r["spec"]["extensions"][0]["url"] == "https://example.com/ext"
    assert "integrity" not in r["spec"]["extensions"][0]


def test_extensions_artifact_only_valid():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "extensions": [{"artifact": "my-plugin@v1"}]},
    })
    assert "errors" not in r
    assert r["spec"]["extensions"][0]["artifact"] == "my-plugin@v1"


def test_extensions_both_url_and_artifact_invalid():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "extensions": [{"url": "https://x.com", "artifact": "y"}]},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.extensions[0]") == "invalid"


def test_extensions_neither_url_nor_artifact_invalid():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "extensions": [{}]},
    })
    errs = {e["field"]: e["type"] for e in r["errors"]}
    assert errs.get("spec.extensions[0]") == "invalid"


def test_extensions_integrity_included_when_set():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {"instances": 1, "extensions": [{"url": "https://x.com", "integrity": "sha256-abc"}]},
    })
    assert r["spec"]["extensions"][0]["integrity"] == "sha256-abc"


def test_extensions_order_preserved():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "extensions": [
                {"url": "https://first.com"},
                {"artifact": "second"},
                {"url": "https://third.com"},
            ],
        },
    })
    exts = r["spec"]["extensions"]
    assert exts[0]["url"] == "https://first.com"
    assert exts[1]["artifact"] == "second"
    assert exts[2]["url"] == "https://third.com"


# --- 9.13: encryption trustStore warning ---

def test_encryption_without_trust_store_emits_warning():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "regions": {
                "local": {
                    "name": "r1",
                    "expose": {"type": "Gateway"},
                    "encryption": {
                        "protocol": "TLSv1.3",
                        "transportKeyStore": {
                            "secretRef": "s", "alias": "a", "filename": "f.p12"
                        },
                    },
                }
            },
        },
    })
    assert "errors" not in r
    assert "warnings" in r
    warn_fields = [w["field"] for w in r["warnings"]]
    assert "spec.regions.local.encryption.trustStore" in warn_fields


def test_encryption_with_trust_store_no_warning():
    r = _create({
        "metadata": {"name": "mx"},
        "spec": {
            "instances": 1,
            "regions": {
                "local": {
                    "name": "r1",
                    "expose": {"type": "Gateway"},
                    "encryption": {
                        "protocol": "TLSv1.3",
                        "transportKeyStore": {"secretRef": "s", "alias": "a", "filename": "f.p12"},
                        "trustStore": {"secretRef": "t", "alias": "ta", "filename": "t.p12"},
                    },
                }
            },
        },
    })
    assert "errors" not in r
    assert "warnings" not in r
