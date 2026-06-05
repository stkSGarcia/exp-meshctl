"""Tests for checkpoint 8: multi-region topology and operational policies."""
import copy
import io
import json
import os
import tempfile
import pytest
import yaml

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meshctl
from meshctl import validate_and_build, compute_telemetry_probe, format_resource_for_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vb(spec_extra=None, meta_extra=None):
    """Build a minimal valid doc and call validate_and_build."""
    doc = {
        "metadata": {"name": "my-mesh"},
        "spec": {"instances": 1},
    }
    if meta_extra:
        doc["metadata"].update(meta_extra)
    if spec_extra:
        doc["spec"].update(spec_extra)
    return validate_and_build(doc)


def _run_cmd(store_state, argv, vault_store=None):
    """Run a meshctl command with a given store state and return parsed JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "store.json")
        vault_path = os.path.join(tmpdir, "vault_store.json")
        task_path = os.path.join(tmpdir, "task_store.json")
        snap_path = os.path.join(tmpdir, "snapshot_store.json")
        rec_path = os.path.join(tmpdir, "recovery_store.json")

        with open(store_path, "w") as f:
            json.dump(store_state, f)
        with open(vault_path, "w") as f:
            json.dump(vault_store or {}, f)
        for p in (task_path, snap_path, rec_path):
            with open(p, "w") as f:
                json.dump({}, f)

        orig_paths = (
            meshctl.STORE_PATH,
            meshctl.VAULT_STORE_PATH,
            meshctl.TASK_STORE_PATH,
            meshctl.SNAPSHOT_STORE_PATH,
            meshctl.RECOVERY_STORE_PATH,
        )
        meshctl.STORE_PATH = store_path
        meshctl.VAULT_STORE_PATH = vault_path
        meshctl.TASK_STORE_PATH = task_path
        meshctl.SNAPSHOT_STORE_PATH = snap_path
        meshctl.RECOVERY_STORE_PATH = rec_path
        try:
            buf = io.StringIO()
            old_argv = sys.argv
            sys.argv = argv
            import contextlib
            with contextlib.redirect_stdout(buf):
                try:
                    meshctl.main()
                except SystemExit:
                    pass
            sys.argv = old_argv
            # Re-read the updated store after the command
            with open(store_path) as f:
                updated_store = json.load(f)
        finally:
            (meshctl.STORE_PATH, meshctl.VAULT_STORE_PATH, meshctl.TASK_STORE_PATH,
             meshctl.SNAPSHOT_STORE_PATH, meshctl.RECOVERY_STORE_PATH) = orig_paths

        raw = buf.getvalue().strip()
        return json.loads(raw) if raw else {}, updated_store


def _make_yaml_file(doc, tmpdir):
    path = os.path.join(tmpdir, "input.yaml")
    with open(path, "w") as f:
        yaml.dump(doc, f)
    return path


def _create_mesh(doc_spec, meta_extra=None):
    """Create a mesh in a fresh store and return (output, updated_store, tmpdir).
    Caller is responsible for cleanup of tmpdir."""
    tmpdir = tempfile.mkdtemp()
    doc = {"metadata": {"name": "my-mesh"}, "spec": doc_spec}
    if meta_extra:
        doc["metadata"].update(meta_extra)
    path = _make_yaml_file(doc, tmpdir)
    out, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
    return out, store, tmpdir


# ---------------------------------------------------------------------------
# 7.1 Existing create/describe output updated to include placement + telemetryProbe
# ---------------------------------------------------------------------------

class TestAlwaysPresentFields:
    def test_create_includes_placement(self):
        result, errs, _ = _vb()
        assert errs == []
        assert result["spec"]["placement"] == {"affinity": {"type": "preferred", "scope": "node"}}

    def test_describe_includes_placement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_yaml_file({"metadata": {"name": "my-mesh"}, "spec": {"instances": 1}}, tmpdir)
            out, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            assert "placement" in out["spec"]

    def test_create_output_includes_telemetry_probe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_yaml_file({"metadata": {"name": "my-mesh"}, "spec": {"instances": 1}}, tmpdir)
            out, _ = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            assert out["status"]["telemetryProbe"] == {"enabled": True}

    def test_describe_includes_telemetry_probe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_yaml_file({"metadata": {"name": "my-mesh"}, "spec": {"instances": 1}}, tmpdir)
            _, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            out, _ = _run_cmd(store, ["meshctl.py", "mesh", "describe", "my-mesh"])
            assert "telemetryProbe" in out["status"]


# ---------------------------------------------------------------------------
# 7.2 Telemetry tag combinations
# ---------------------------------------------------------------------------

class TestTelemetryProbe:
    def test_no_tags_enabled(self):
        assert compute_telemetry_probe(None) == {"enabled": True}
        assert compute_telemetry_probe({}) == {"enabled": True}

    def test_explicit_true(self):
        assert compute_telemetry_probe({"mesh.io/telemetry": "true"}) == {"enabled": True}

    def test_disabled(self):
        assert compute_telemetry_probe({"mesh.io/telemetry": "false"}) == {"enabled": False}

    def test_target_labels(self):
        result = compute_telemetry_probe({"mesh.io/targetLabels": "region,env"})
        assert result == {"enabled": True, "labels": {"targetLabels": ["region", "env"]}}

    def test_probe_target_labels(self):
        result = compute_telemetry_probe({"mesh.io/probeTargetLabels": "pod"})
        assert result == {"enabled": True, "labels": {"probeTargetLabels": ["pod"]}}

    def test_instance_labels(self):
        result = compute_telemetry_probe({"mesh.io/instanceLabels": "node,rack"})
        assert result == {"enabled": True, "labels": {"instanceLabels": ["node", "rack"]}}

    def test_all_label_tags(self):
        tags = {
            "mesh.io/targetLabels": "region,env",
            "mesh.io/probeTargetLabels": "pod",
            "mesh.io/instanceLabels": "node",
        }
        result = compute_telemetry_probe(tags)
        assert result["enabled"] is True
        assert result["labels"]["targetLabels"] == ["region", "env"]
        assert result["labels"]["probeTargetLabels"] == ["pod"]
        assert result["labels"]["instanceLabels"] == ["node"]

    def test_only_set_categories_included(self):
        result = compute_telemetry_probe({"mesh.io/targetLabels": "region"})
        assert "probeTargetLabels" not in result.get("labels", {})
        assert "instanceLabels" not in result.get("labels", {})

    def test_order_preserved(self):
        result = compute_telemetry_probe({"mesh.io/targetLabels": "c,a,b"})
        assert result["labels"]["targetLabels"] == ["c", "a", "b"]

    def test_metadata_tags_persisted(self):
        result, errs, _ = _vb(meta_extra={"tags": {"mesh.io/telemetry": "true", "env": "prod"}})
        assert errs == []
        assert result["metadata"]["tags"]["env"] == "prod"

    def test_no_tags_no_metadata_tags_key(self):
        result, errs, _ = _vb()
        assert errs == []
        assert "tags" not in result["metadata"]


# ---------------------------------------------------------------------------
# 7.3 Placement validation errors
# ---------------------------------------------------------------------------

class TestPlacementValidation:
    def test_non_object_placement(self):
        _, errs, _ = _vb({"placement": "wrong"})
        assert any(e["field"] == "spec.placement" and e["type"] == "invalid" for e in errs)

    def test_non_object_affinity(self):
        _, errs, _ = _vb({"placement": {"affinity": "wrong"}})
        assert any(e["field"] == "spec.placement.affinity" and e["type"] == "invalid" for e in errs)

    def test_invalid_affinity_type(self):
        _, errs, _ = _vb({"placement": {"affinity": {"type": "random", "scope": "node"}}})
        assert any(e["field"] == "spec.placement.affinity.type" and e["type"] == "invalid" for e in errs)

    def test_invalid_affinity_scope(self):
        _, errs, _ = _vb({"placement": {"affinity": {"type": "preferred", "scope": "rack"}}})
        assert any(e["field"] == "spec.placement.affinity.scope" and e["type"] == "invalid" for e in errs)

    def test_valid_required_zone(self):
        result, errs, _ = _vb({"placement": {"affinity": {"type": "required", "scope": "zone"}}})
        assert errs == []
        assert result["spec"]["placement"] == {"affinity": {"type": "required", "scope": "zone"}}

    def test_default_when_absent(self):
        result, errs, _ = _vb()
        assert errs == []
        assert result["spec"]["placement"]["affinity"]["type"] == "preferred"
        assert result["spec"]["placement"]["affinity"]["scope"] == "node"


# ---------------------------------------------------------------------------
# 7.4 configBundleRef
# ---------------------------------------------------------------------------

class TestConfigBundleRef:
    def test_create_with_string_ref(self):
        result, errs, _ = _vb({"configBundleRef": "bundle-v1"})
        assert errs == []
        assert result["spec"]["configBundleRef"] == "bundle-v1"

    def test_create_with_non_string_invalid(self):
        _, errs, _ = _vb({"configBundleRef": 123})
        assert any(e["field"] == "spec.configBundleRef" and e["type"] == "invalid" for e in errs)

    def test_create_absent_not_in_output(self):
        result, errs, _ = _vb()
        assert errs == []
        assert "configBundleRef" not in result["spec"]

    def test_update_change_produces_configRefresh(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "configBundleRef": "v1"}}
            path = _make_yaml_file(create_doc, tmpdir)
            _, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])

            update_doc = {"metadata": {"name": "my-mesh"}, "spec": {"configBundleRef": "v2"}}
            up_path = _make_yaml_file(update_doc, os.path.join(tmpdir, "up.yaml") and tmpdir)
            up_path2 = os.path.join(tmpdir, "up.yaml")
            with open(up_path2, "w") as f:
                yaml.dump(update_doc, f)
            out, store2 = _run_cmd(store, ["meshctl.py", "mesh", "update", "-f", up_path2])
            cr = out["status"]["configRefresh"]
            assert cr["currentRef"] == "v2"
            assert cr["previousRef"] == "v1"
            assert cr["pending"] is True

    def test_omit_configBundleRef_on_update_keeps_value(self):
        # Create with configBundleRef, then update without mentioning it — kept
        with tempfile.TemporaryDirectory() as tmpdir:
            create_doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "configBundleRef": "v1"}}
            path = _make_yaml_file(create_doc, tmpdir)
            _, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])

            update_doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 2}}
            up_path = os.path.join(tmpdir, "up.yaml")
            with open(up_path, "w") as f:
                yaml.dump(update_doc, f)
            out, _ = _run_cmd(store, ["meshctl.py", "mesh", "update", "-f", up_path])
            # No configRefresh since ref didn't change
            assert "configRefresh" not in out["status"]
            assert out["spec"]["configBundleRef"] == "v1"

    def test_null_configBundleRef_clears_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "configBundleRef": "v1"}}
            path = _make_yaml_file(create_doc, tmpdir)
            _, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])

            update_doc = {"metadata": {"name": "my-mesh"}, "spec": {"configBundleRef": None}}
            up_path = os.path.join(tmpdir, "up.yaml")
            with open(up_path, "w") as f:
                yaml.dump(update_doc, f)
            out, _ = _run_cmd(store, ["meshctl.py", "mesh", "update", "-f", up_path])
            cr = out["status"]["configRefresh"]
            assert cr["currentRef"] is None
            assert cr["previousRef"] == "v1"

    def test_describe_omits_configRefresh(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "configBundleRef": "v1"}}
            path = _make_yaml_file(create_doc, tmpdir)
            _, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])

            update_doc = {"metadata": {"name": "my-mesh"}, "spec": {"configBundleRef": "v2"}}
            up_path = os.path.join(tmpdir, "up.yaml")
            with open(up_path, "w") as f:
                yaml.dump(update_doc, f)
            _, store2 = _run_cmd(store, ["meshctl.py", "mesh", "update", "-f", up_path])

            out, _ = _run_cmd(store2, ["meshctl.py", "mesh", "describe", "my-mesh"])
            assert "configRefresh" not in out["status"]


# ---------------------------------------------------------------------------
# 7.5 Extensions
# ---------------------------------------------------------------------------

class TestExtensions:
    def test_url_extension_accepted(self):
        result, errs, _ = _vb({"extensions": [{"url": "https://example.com/plugin.wasm"}]})
        assert errs == []
        assert result["spec"]["extensions"][0] == {"url": "https://example.com/plugin.wasm"}

    def test_artifact_extension_accepted(self):
        result, errs, _ = _vb({"extensions": [{"artifact": "oci://registry/plugin:v1"}]})
        assert errs == []
        assert result["spec"]["extensions"][0] == {"artifact": "oci://registry/plugin:v1"}

    def test_integrity_included_when_set(self):
        result, errs, _ = _vb({"extensions": [{"url": "https://a.com", "integrity": "sha256:abc"}]})
        assert errs == []
        assert result["spec"]["extensions"][0]["integrity"] == "sha256:abc"

    def test_integrity_omitted_when_absent(self):
        result, errs, _ = _vb({"extensions": [{"url": "https://a.com"}]})
        assert errs == []
        assert "integrity" not in result["spec"]["extensions"][0]

    def test_both_url_and_artifact_invalid(self):
        _, errs, _ = _vb({"extensions": [{"url": "https://a.com", "artifact": "oci://b"}]})
        assert any(e["field"] == "spec.extensions[0]" and e["type"] == "invalid" for e in errs)
        assert "exactly one of 'url' or 'artifact' must be set" in errs[0]["message"]

    def test_neither_url_nor_artifact_invalid(self):
        _, errs, _ = _vb({"extensions": [{}]})
        assert any(e["field"] == "spec.extensions[0]" and e["type"] == "invalid" for e in errs)

    def test_declaration_order_preserved(self):
        ext = [
            {"url": "https://first.com"},
            {"artifact": "oci://second"},
            {"url": "https://third.com"},
        ]
        result, errs, _ = _vb({"extensions": ext})
        assert errs == []
        assert result["spec"]["extensions"][0]["url"] == "https://first.com"
        assert result["spec"]["extensions"][1]["artifact"] == "oci://second"
        assert result["spec"]["extensions"][2]["url"] == "https://third.com"

    def test_multiple_invalid_entries(self):
        _, errs, _ = _vb({"extensions": [{"url": "a", "artifact": "b"}, {}]})
        fields = [e["field"] for e in errs]
        assert "spec.extensions[0]" in fields
        assert "spec.extensions[1]" in fields


# ---------------------------------------------------------------------------
# 7.6 Multi-region validation
# ---------------------------------------------------------------------------

def _reg(local_extra=None, remotes=None):
    local = {"name": "us-east", "expose": {"type": "Internal"}}
    if local_extra:
        local.update(local_extra)
    r = {"local": local}
    if remotes is not None:
        r["remotes"] = remotes
    return r


class TestMultiRegion:
    def test_missing_local(self):
        _, errs, _ = _vb({"regions": {}})
        assert any(e["field"] == "spec.regions.local" and e["type"] == "required" for e in errs)

    def test_missing_local_name(self):
        _, errs, _ = _vb({"regions": {"local": {"expose": {"type": "Internal"}}}})
        assert any(e["field"] == "spec.regions.local.name" and e["type"] == "required" for e in errs)

    def test_missing_expose_type(self):
        _, errs, _ = _vb({"regions": {"local": {"name": "us", "expose": {}}}})
        assert any(e["field"] == "spec.regions.local.expose.type" and e["type"] == "required" for e in errs)

    def test_invalid_expose_type(self):
        _, errs, _ = _vb({"regions": {"local": {"name": "us", "expose": {"type": "NodePort"}}}})
        assert any(e["field"] == "spec.regions.local.expose.type" and e["type"] == "invalid" for e in errs)

    def test_valid_expose_types(self):
        for etype in ("Internal", "DirectPort", "Balancer", "Gateway"):
            extra = {"name": "us", "expose": {"type": etype}}
            if etype == "Gateway":
                extra["encryption"] = {
                    "transportKeyStore": {"secretRef": "s", "alias": "a", "filename": "f"},
                    "trustStore": {"secretRef": "s", "alias": "a", "filename": "f"},
                }
            result, errs, _ = _vb({"regions": {"local": extra}})
            assert errs == [], f"Expected no errors for expose type {etype!r}, got {errs}"

    def test_max_relay_nodes_null_invalid(self):
        _, errs, _ = _vb({"regions": _reg({"maxRelayNodes": None})})
        assert any(e["field"] == "spec.regions.local.maxRelayNodes" and e["type"] == "invalid" for e in errs)

    def test_max_relay_nodes_zero_invalid(self):
        _, errs, _ = _vb({"regions": _reg({"maxRelayNodes": 0})})
        assert any(e["field"] == "spec.regions.local.maxRelayNodes" and e["type"] == "invalid" for e in errs)

    def test_max_relay_nodes_valid(self):
        result, errs, _ = _vb({"regions": _reg({"maxRelayNodes": 5})})
        assert errs == []
        assert result["spec"]["regions"]["local"]["maxRelayNodes"] == 5

    def test_max_relay_nodes_omitted_from_output(self):
        result, errs, _ = _vb({"regions": _reg()})
        assert errs == []
        assert "maxRelayNodes" not in result["spec"]["regions"]["local"]

    def test_encryption_must_be_object(self):
        _, errs, _ = _vb({"regions": _reg({"encryption": "bad"})})
        assert any(e["field"] == "spec.regions.local.encryption" and e["type"] == "invalid" for e in errs)

    def test_encryption_protocol_default(self):
        local = {"name": "us", "expose": {"type": "Internal"},
                 "encryption": {"trustStore": {"secretRef": "s", "alias": "a", "filename": "f"}}}
        result, errs, _ = _vb({"regions": {"local": local}})
        # warnings may exist but no errors
        assert all(e["field"] != "spec.regions.local.encryption.protocol" for e in errs)
        assert result["spec"]["regions"]["local"]["encryption"]["protocol"] == "TLSv1.3"

    def test_invalid_encryption_protocol(self):
        local = {"name": "us", "expose": {"type": "Internal"},
                 "encryption": {"protocol": "TLSv1.0", "trustStore": {"secretRef": "s", "alias": "a", "filename": "f"}}}
        _, errs, _ = _vb({"regions": {"local": local}})
        assert any(e["field"] == "spec.regions.local.encryption.protocol" and e["type"] == "invalid" for e in errs)

    def test_gateway_requires_transport_key_store(self):
        local = {"name": "us", "expose": {"type": "Gateway"},
                 "encryption": {"trustStore": {"secretRef": "s", "alias": "a", "filename": "f"}}}
        _, errs, _ = _vb({"regions": {"local": local}})
        assert any(e["field"] == "spec.regions.local.encryption.transportKeyStore" and e["type"] == "required" for e in errs)

    def test_trust_store_absent_emits_warning(self):
        local = {"name": "us", "expose": {"type": "Internal"}, "encryption": {"protocol": "TLSv1.3"}}
        _, errs, warnings = _vb({"regions": {"local": local}})
        assert not any(e["field"].startswith("spec.regions.local.encryption.trustStore") for e in errs)
        assert any("trustStore" in w["message"] for w in warnings)

    def test_key_store_missing_sub_fields(self):
        local = {"name": "us", "expose": {"type": "Internal"},
                 "encryption": {"transportKeyStore": {"secretRef": "s"}, "trustStore": {"secretRef": "s", "alias": "a", "filename": "f"}}}
        _, errs, _ = _vb({"regions": {"local": local}})
        assert any("alias" in e["field"] and e["type"] == "required" for e in errs)

    def test_discovery_default_applied(self):
        result, errs, _ = _vb({"regions": _reg()})
        assert errs == []
        disc = result["spec"]["regions"]["local"]["discovery"]
        assert disc["type"] == "relay"
        assert disc["heartbeat"]["enabled"] is True
        assert disc["heartbeat"]["interval"] == 10000
        assert disc["heartbeat"]["timeout"] == 30000

    def test_discovery_must_be_object(self):
        _, errs, _ = _vb({"regions": _reg({"discovery": "bad"})})
        assert any(e["field"] == "spec.regions.local.discovery" and e["type"] == "invalid" for e in errs)

    def test_discovery_type_must_be_relay(self):
        _, errs, _ = _vb({"regions": _reg({"discovery": {"type": "broadcast"}})})
        assert any(e["field"] == "spec.regions.local.discovery.type" and e["type"] == "invalid" for e in errs)

    def test_heartbeat_interval_must_be_less_than_timeout(self):
        disc = {"type": "relay", "heartbeat": {"enabled": True, "interval": 30000, "timeout": 10000}}
        _, errs, _ = _vb({"regions": _reg({"discovery": disc})})
        assert any(e["field"] == "spec.regions.local.discovery.heartbeat" and e["type"] == "invalid" for e in errs)

    def test_heartbeat_equal_interval_and_timeout_invalid(self):
        disc = {"type": "relay", "heartbeat": {"enabled": True, "interval": 10000, "timeout": 10000}}
        _, errs, _ = _vb({"regions": _reg({"discovery": disc})})
        assert any(e["field"] == "spec.regions.local.discovery.heartbeat" and e["type"] == "invalid" for e in errs)

    def test_remotes_empty_array_ok(self):
        result, errs, _ = _vb({"regions": _reg(remotes=[])})
        assert errs == []

    def test_remote_name_required(self):
        _, errs, _ = _vb({"regions": _reg(remotes=[{"url": "https://eu.example.com"}])})
        assert any("remotes[0].name" in e["field"] and e["type"] == "required" for e in errs)

    def test_remote_url_required(self):
        _, errs, _ = _vb({"regions": _reg(remotes=[{"name": "eu"}])})
        assert any("remotes[0].url" in e["field"] and e["type"] == "required" for e in errs)

    def test_duplicate_remote_name(self):
        remotes = [
            {"name": "eu", "url": "https://eu.example.com"},
            {"name": "eu", "url": "https://eu2.example.com"},
        ]
        _, errs, _ = _vb({"regions": _reg(remotes=remotes)})
        assert any("remotes[1].name" in e["field"] and e["type"] == "duplicate" for e in errs)

    def test_remote_declaration_order_preserved(self):
        remotes = [
            {"name": "eu", "url": "https://eu.example.com"},
            {"name": "ap", "url": "https://ap.example.com"},
        ]
        result, errs, _ = _vb({"regions": _reg(remotes=remotes)})
        assert errs == []
        out_remotes = result["spec"]["regions"]["remotes"]
        assert out_remotes[0]["name"] == "eu"
        assert out_remotes[1]["name"] == "ap"

    def test_optional_remote_fields_omitted(self):
        remotes = [{"name": "eu", "url": "https://eu.example.com"}]
        result, errs, _ = _vb({"regions": _reg(remotes=remotes)})
        assert errs == []
        r = result["spec"]["regions"]["remotes"][0]
        assert "credentialRef" not in r
        assert "namespace" not in r
        assert "clusterRef" not in r

    def test_optional_remote_fields_included_when_set(self):
        remotes = [{"name": "eu", "url": "https://eu.example.com", "credentialRef": "cred-1", "namespace": "ns-eu"}]
        result, errs, _ = _vb({"regions": _reg(remotes=remotes)})
        assert errs == []
        r = result["spec"]["regions"]["remotes"][0]
        assert r["credentialRef"] == "cred-1"
        assert r["namespace"] == "ns-eu"

    def test_single_region_mesh_no_regions_in_output(self):
        result, errs, _ = _vb()
        assert errs == []
        assert "regions" not in result["spec"]


# ---------------------------------------------------------------------------
# 7.7 Region conditions
# ---------------------------------------------------------------------------

class TestRegionConditions:
    def test_region_conditions_added_on_create(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "regions": {
                "local": {"name": "us", "expose": {"type": "Internal"}}
            }}}
            path = _make_yaml_file(doc, tmpdir)
            out, _ = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            cond_types = {c["type"] for c in out["status"]["conditions"]}
            assert "DiscoveryRelayReady" in cond_types
            assert "RegionViewFormed" in cond_types

    def test_region_condition_status_is_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "regions": {
                "local": {"name": "us", "expose": {"type": "Internal"}}
            }}}
            path = _make_yaml_file(doc, tmpdir)
            out, _ = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            for c in out["status"]["conditions"]:
                if c["type"] in ("DiscoveryRelayReady", "RegionViewFormed"):
                    assert c["status"] == "False"
                    assert c["message"] == ""

    def test_conditions_sorted_alphabetically(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "regions": {
                "local": {"name": "us", "expose": {"type": "Internal"}}
            }}}
            path = _make_yaml_file(doc, tmpdir)
            out, _ = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            cond_types = [c["type"] for c in out["status"]["conditions"]]
            assert cond_types == sorted(cond_types)

    def test_no_region_conditions_without_regions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1}}
            path = _make_yaml_file(doc, tmpdir)
            out, _ = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            cond_types = {c["type"] for c in out["status"]["conditions"]}
            assert "DiscoveryRelayReady" not in cond_types
            assert "RegionViewFormed" not in cond_types

    def test_status_stable_not_affected_by_region_conditions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "regions": {
                "local": {"name": "us", "expose": {"type": "Internal"}}
            }}}
            path = _make_yaml_file(doc, tmpdir)
            out, _ = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])
            assert out["status"]["stable"] is True


# ---------------------------------------------------------------------------
# 7.8 LiveMigration restriction with and without regions
# ---------------------------------------------------------------------------

class TestLiveMigrationRestriction:
    def test_live_migration_allowed_without_regions(self):
        result, errs, _ = _vb({"migration": {"strategy": "LiveMigration"}})
        assert not any(e["field"] == "spec.migration.strategy" and "multi-region" in e["message"] for e in errs)

    def test_live_migration_rejected_with_regions(self):
        _, errs, _ = _vb({
            "migration": {"strategy": "LiveMigration"},
            "regions": {"local": {"name": "us", "expose": {"type": "Internal"}}},
        })
        assert any(
            e["field"] == "spec.migration.strategy"
            and e["type"] == "invalid"
            and "LiveMigration strategy is not supported with multi-region topology" in e["message"]
            for e in errs
        )

    def test_live_migration_rejected_on_update_with_regions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_doc = {"metadata": {"name": "my-mesh"}, "spec": {"instances": 1, "regions": {
                "local": {"name": "us", "expose": {"type": "Internal"}}
            }}}
            path = _make_yaml_file(create_doc, tmpdir)
            _, store = _run_cmd({}, ["meshctl.py", "mesh", "create", "-f", path])

            update_doc = {"metadata": {"name": "my-mesh"}, "spec": {"migration": {"strategy": "LiveMigration"}}}
            up_path = os.path.join(tmpdir, "up.yaml")
            with open(up_path, "w") as f:
                yaml.dump(update_doc, f)
            out, _ = _run_cmd(store, ["meshctl.py", "mesh", "update", "-f", up_path])
            assert "errors" in out
            assert any(
                e["field"] == "spec.migration.strategy" and "LiveMigration" in e["message"]
                for e in out["errors"]
            )

    def test_full_stop_accepted_with_regions(self):
        result, errs, _ = _vb({
            "migration": {"strategy": "FullStop"},
            "regions": {"local": {"name": "us", "expose": {"type": "Internal"}}},
        })
        assert not any(e["field"] == "spec.migration.strategy" for e in errs)
