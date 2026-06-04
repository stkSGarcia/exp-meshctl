import io
import json
import os
import sys
from contextlib import redirect_stdout

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meshctl


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(meshctl, "STORE_PATH", str(tmp_path / "store.json"))
    monkeypatch.setattr(meshctl, "VAULT_STORE_PATH", str(tmp_path / "vault_store.json"))
    monkeypatch.setattr(meshctl, "TASK_STORE_PATH", str(tmp_path / "task_store.json"))
    monkeypatch.setattr(meshctl, "SNAPSHOT_STORE_PATH", str(tmp_path / "snapshot_store.json"))
    monkeypatch.setattr(meshctl, "RECOVERY_STORE_PATH", str(tmp_path / "recovery_store.json"))


def capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return json.loads(buf.getvalue())


def yaml_file(tmp_path, data, name="input.yaml"):
    p = tmp_path / name
    p.write_text(yaml.dump(data))
    return str(p)


class Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def make_mesh(tmp_path, name="test-mesh"):
    path = yaml_file(tmp_path, {"metadata": {"name": name}, "spec": {}})
    return capture(meshctl.cmd_create, Args(file=path))


def make_task(tmp_path, name="my-task", mesh="test-mesh", inline="echo hello"):
    path = yaml_file(tmp_path, {"metadata": {"name": name}, "spec": {"meshRef": mesh, "inline": inline}})
    return capture(meshctl.task_cmd_create, Args(file=path))


def make_snapshot(tmp_path, name="snap-1", mesh="test-mesh"):
    path = yaml_file(tmp_path, {"metadata": {"name": name}, "spec": {"meshRef": mesh}})
    return capture(meshctl.snapshot_cmd_create, Args(file=path))


def make_recovery(tmp_path, name="rec-1", mesh="test-mesh", snapshot="snap-1"):
    path = yaml_file(tmp_path, {"metadata": {"name": name}, "spec": {"meshRef": mesh, "snapshotRef": snapshot}})
    return capture(meshctl.recovery_cmd_create, Args(file=path))


# ---------------------------------------------------------------------------
# Task create
# ---------------------------------------------------------------------------

class TestTaskCreate:
    def test_valid_inline(self, tmp_path):
        make_mesh(tmp_path)
        r = make_task(tmp_path)
        assert r["metadata"]["name"] == "my-task"
        assert r["status"]["state"] == "Initializing"
        assert r["spec"]["inline"] == "echo hello"

    def test_valid_bundle_ref(self, tmp_path):
        make_mesh(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "bt-task"}, "spec": {"meshRef": "test-mesh", "bundleRef": "bundle-v1"}})
        r = capture(meshctl.task_cmd_create, Args(file=path))
        assert r["status"]["state"] == "Initializing"
        assert r["spec"]["bundleRef"] == "bundle-v1"

    def test_invalid_mesh_ref(self, tmp_path):
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "no-such-mesh", "inline": "echo hi"}})
        r = capture(meshctl.task_cmd_create, Args(file=path))
        assert "errors" in r
        assert any(e["field"] == "spec.meshRef" and e["type"] == "invalid" for e in r["errors"])

    def test_both_inline_and_bundle_ref(self, tmp_path):
        make_mesh(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "test-mesh", "inline": "echo", "bundleRef": "b"}})
        r = capture(meshctl.task_cmd_create, Args(file=path))
        assert "errors" in r
        assert any(e["field"] == "spec" and e["type"] == "invalid" for e in r["errors"])
        assert any("exactly one" in e["message"] for e in r["errors"])

    def test_neither_inline_nor_bundle_ref(self, tmp_path):
        make_mesh(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "test-mesh"}})
        r = capture(meshctl.task_cmd_create, Args(file=path))
        assert "errors" in r
        assert any(e["field"] == "spec" and e["type"] == "invalid" for e in r["errors"])
        assert any("exactly one" in e["message"] for e in r["errors"])

    def test_empty_inline(self, tmp_path):
        make_mesh(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "test-mesh", "inline": ""}})
        r = capture(meshctl.task_cmd_create, Args(file=path))
        assert "errors" in r
        assert any(e["field"] == "spec" and e["type"] == "invalid" for e in r["errors"])

    def test_error_format(self, tmp_path):
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "no-mesh", "inline": "echo"}})
        r = capture(meshctl.task_cmd_create, Args(file=path))
        assert "errors" in r
        for e in r["errors"]:
            assert "field" in e and "type" in e and "message" in e


# ---------------------------------------------------------------------------
# Task run
# ---------------------------------------------------------------------------

class TestTaskRun:
    def test_success_path_no_fail_lines(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path, inline="cmd1\ncmd2\ncmd3")
        r = capture(meshctl.task_cmd_run, Args(name="my-task"))
        assert r["status"]["state"] == "Succeeded"
        assert "detail" not in r["status"]

    def test_fail_line_detected(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path, inline="cmd1\nFAIL: disk full\ncmd3")
        r = capture(meshctl.task_cmd_run, Args(name="my-task"))
        assert r["status"]["state"] == "Failed"
        assert r["status"]["detail"] == "command 1 failed: disk full"

    def test_fail_line_at_index_0(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path, inline="FAIL: bad start")
        r = capture(meshctl.task_cmd_run, Args(name="my-task"))
        assert r["status"]["state"] == "Failed"
        assert r["status"]["detail"] == "command 0 failed: bad start"

    def test_non_initializing_rejected(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path)
        capture(meshctl.task_cmd_run, Args(name="my-task"))  # succeeds
        r = capture(meshctl.task_cmd_run, Args(name="my-task"))  # second run
        assert "errors" in r
        errs = r["errors"]
        assert any(e["field"] == "status.state" and e["type"] == "invalid" for e in errs)
        assert any("Initializing" in e["message"] for e in errs)

    def test_terminal_state_irreversible_failed(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path, inline="FAIL: boom")
        capture(meshctl.task_cmd_run, Args(name="my-task"))
        r = capture(meshctl.task_cmd_run, Args(name="my-task"))
        assert "errors" in r
        assert any(e["field"] == "status.state" for e in r["errors"])


# ---------------------------------------------------------------------------
# Task spec immutability
# ---------------------------------------------------------------------------

class TestTaskSpecImmutability:
    def test_update_inline_rejected(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path, inline="original")
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "test-mesh", "inline": "changed"}})
        r = capture(meshctl.task_cmd_update, Args(file=path))
        assert "errors" in r
        assert any(e["type"] == "immutable" for e in r["errors"])

    def test_add_previously_omitted_field_rejected(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "test-mesh", "inline": "echo hello", "bundleRef": "new"}})
        r = capture(meshctl.task_cmd_update, Args(file=path))
        assert "errors" in r
        assert any(e["type"] == "immutable" for e in r["errors"])

    def test_no_spec_change_accepted(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path, inline="echo hello")
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {}})
        r = capture(meshctl.task_cmd_update, Args(file=path))
        assert "errors" not in r
        assert r["metadata"]["name"] == "my-task"


# ---------------------------------------------------------------------------
# Snapshot create
# ---------------------------------------------------------------------------

class TestSnapshotCreate:
    def test_valid_minimal(self, tmp_path):
        make_mesh(tmp_path)
        r = make_snapshot(tmp_path)
        assert r["metadata"]["name"] == "snap-1"
        assert r["status"]["state"] == "Initializing"

    def test_memory_default_applied(self, tmp_path):
        make_mesh(tmp_path)
        r = make_snapshot(tmp_path)
        assert r["spec"]["resources"]["memory"] == {"limit": "1Gi", "request": "1Gi"}

    def test_invalid_mesh_ref(self, tmp_path):
        path = yaml_file(tmp_path, {"metadata": {"name": "snap-1"}, "spec": {"meshRef": "no-mesh"}})
        r = capture(meshctl.snapshot_cmd_create, Args(file=path))
        assert "errors" in r
        assert any(e["field"] == "spec.meshRef" and e["type"] == "invalid" for e in r["errors"])

    def test_invalid_memory_quantity(self, tmp_path):
        make_mesh(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "snap-1"}, "spec": {"meshRef": "test-mesh", "resources": {"memory": {"limit": "not-a-quantity"}}}})
        r = capture(meshctl.snapshot_cmd_create, Args(file=path))
        assert "errors" in r
        assert any("memory" in e["field"] and e["type"] == "invalid" for e in r["errors"])

    def test_scope_preserved(self, tmp_path):
        make_mesh(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "snap-sc"}, "spec": {"meshRef": "test-mesh", "scope": {"stores": ["s1"]}}})
        r = capture(meshctl.snapshot_cmd_create, Args(file=path))
        assert r["spec"]["scope"] == {"stores": ["s1"]}

    def test_error_format(self, tmp_path):
        path = yaml_file(tmp_path, {"metadata": {"name": "snap-1"}, "spec": {"meshRef": "no-mesh"}})
        r = capture(meshctl.snapshot_cmd_create, Args(file=path))
        assert "errors" in r
        for e in r["errors"]:
            assert "field" in e and "type" in e and "message" in e


# ---------------------------------------------------------------------------
# Snapshot run
# ---------------------------------------------------------------------------

class TestSnapshotRun:
    def test_stable_mesh_succeeds_with_storage_ref(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        r = capture(meshctl.snapshot_cmd_run, Args(name="snap-1"))
        assert r["status"]["state"] == "Succeeded"
        assert "storageRef" in r["status"]
        assert r["status"]["storageRef"]
        assert "detail" not in r["status"]

    def test_unstable_mesh_sets_unknown(self, tmp_path):
        make_mesh(tmp_path, name="unstable-mesh")
        # Make the mesh unstable by updating its status directly in the store
        store = meshctl.load_store()
        store["unstable-mesh"]["status"]["stable"] = False
        meshctl.save_store(store)
        path = yaml_file(tmp_path, {"metadata": {"name": "snap-u"}, "spec": {"meshRef": "unstable-mesh"}})
        capture(meshctl.snapshot_cmd_create, Args(file=path))
        r = capture(meshctl.snapshot_cmd_run, Args(name="snap-u"))
        assert r["status"]["state"] == "Unknown"
        assert r["status"].get("detail")
        assert "storageRef" not in r["status"]

    def test_non_initializing_rejected(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        capture(meshctl.snapshot_cmd_run, Args(name="snap-1"))
        r = capture(meshctl.snapshot_cmd_run, Args(name="snap-1"))
        assert "errors" in r
        assert any(e["field"] == "status.state" and e["type"] == "invalid" for e in r["errors"])

    def test_terminal_state_irreversible(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        capture(meshctl.snapshot_cmd_run, Args(name="snap-1"))
        r = capture(meshctl.snapshot_cmd_run, Args(name="snap-1"))
        assert "errors" in r


# ---------------------------------------------------------------------------
# Snapshot delete dependency protection
# ---------------------------------------------------------------------------

class TestSnapshotDelete:
    def test_unreferenced_snapshot_deleted(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        r = capture(meshctl.snapshot_cmd_delete, Args(name="snap-1"))
        assert "errors" not in r

    def test_referenced_by_recovery_conflict(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        make_recovery(tmp_path)
        r = capture(meshctl.snapshot_cmd_delete, Args(name="snap-1"))
        assert "errors" in r
        errs = r["errors"]
        assert any(e["field"] == "metadata.name" and e["type"] == "conflict" for e in errs)
        assert any("rec-1" in e["message"] for e in errs)


# ---------------------------------------------------------------------------
# Snapshot spec immutability
# ---------------------------------------------------------------------------

class TestSnapshotSpecImmutability:
    def test_update_mesh_ref_rejected(self, tmp_path):
        make_mesh(tmp_path)
        make_mesh(tmp_path, name="other-mesh")
        make_snapshot(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "snap-1"}, "spec": {"meshRef": "other-mesh"}})
        r = capture(meshctl.snapshot_cmd_update, Args(file=path))
        assert "errors" in r
        assert any(e["type"] == "immutable" for e in r["errors"])

    def test_add_field_rejected(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "snap-1"}, "spec": {"meshRef": "test-mesh", "storage": {"size": "2Gi"}}})
        r = capture(meshctl.snapshot_cmd_update, Args(file=path))
        assert "errors" in r
        assert any(e["type"] == "immutable" for e in r["errors"])


# ---------------------------------------------------------------------------
# Recovery create
# ---------------------------------------------------------------------------

class TestRecoveryCreate:
    def test_valid(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        r = make_recovery(tmp_path)
        assert r["metadata"]["name"] == "rec-1"
        assert r["status"]["state"] == "Initializing"
        assert r["spec"]["snapshotRef"] == "snap-1"

    def test_memory_default_applied(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        r = make_recovery(tmp_path)
        assert r["spec"]["resources"]["memory"] == {"limit": "1Gi", "request": "1Gi"}

    def test_invalid_mesh_ref(self, tmp_path):
        path = yaml_file(tmp_path, {"metadata": {"name": "rec-1"}, "spec": {"meshRef": "no-mesh", "snapshotRef": "snap-1"}})
        r = capture(meshctl.recovery_cmd_create, Args(file=path))
        assert "errors" in r
        assert any(e["field"] == "spec.meshRef" and e["type"] == "invalid" for e in r["errors"])

    def test_missing_snapshot_ref(self, tmp_path):
        make_mesh(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "rec-1"}, "spec": {"meshRef": "test-mesh", "snapshotRef": "no-snap"}})
        r = capture(meshctl.recovery_cmd_create, Args(file=path))
        assert "errors" in r
        assert any(e["field"] == "spec.snapshotRef" and e["type"] == "invalid" for e in r["errors"])

    def test_snapshot_mesh_mismatch(self, tmp_path):
        make_mesh(tmp_path, name="mesh-a")
        make_mesh(tmp_path, name="mesh-b")
        path_s = yaml_file(tmp_path, {"metadata": {"name": "snap-a"}, "spec": {"meshRef": "mesh-a"}}, name="snap.yaml")
        capture(meshctl.snapshot_cmd_create, Args(file=path_s))
        path_r = yaml_file(tmp_path, {"metadata": {"name": "rec-x"}, "spec": {"meshRef": "mesh-b", "snapshotRef": "snap-a"}}, name="rec.yaml")
        r = capture(meshctl.recovery_cmd_create, Args(file=path_r))
        assert "errors" in r
        errs = r["errors"]
        assert any(e["field"] == "spec.snapshotRef" and e["type"] == "invalid" for e in errs)
        assert any("mesh-a" in e["message"] and "mesh-b" in e["message"] for e in errs)

    def test_error_format(self, tmp_path):
        path = yaml_file(tmp_path, {"metadata": {"name": "rec-1"}, "spec": {"meshRef": "no-mesh", "snapshotRef": "no-snap"}})
        r = capture(meshctl.recovery_cmd_create, Args(file=path))
        assert "errors" in r
        for e in r["errors"]:
            assert "field" in e and "type" in e and "message" in e


# ---------------------------------------------------------------------------
# Recovery run
# ---------------------------------------------------------------------------

class TestRecoveryRun:
    def test_stable_mesh_succeeds(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        make_recovery(tmp_path)
        r = capture(meshctl.recovery_cmd_run, Args(name="rec-1"))
        assert r["status"]["state"] == "Succeeded"
        assert "detail" not in r["status"]
        assert "storageRef" not in r["status"]

    def test_unstable_mesh_sets_unknown(self, tmp_path):
        make_mesh(tmp_path, name="unstable-mesh")
        store = meshctl.load_store()
        store["unstable-mesh"]["status"]["stable"] = False
        meshctl.save_store(store)
        path_s = yaml_file(tmp_path, {"metadata": {"name": "snap-u"}, "spec": {"meshRef": "unstable-mesh"}}, name="snap.yaml")
        capture(meshctl.snapshot_cmd_create, Args(file=path_s))
        path_r = yaml_file(tmp_path, {"metadata": {"name": "rec-u"}, "spec": {"meshRef": "unstable-mesh", "snapshotRef": "snap-u"}}, name="rec.yaml")
        capture(meshctl.recovery_cmd_create, Args(file=path_r))
        r = capture(meshctl.recovery_cmd_run, Args(name="rec-u"))
        assert r["status"]["state"] == "Unknown"
        assert r["status"].get("detail")

    def test_non_initializing_rejected(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        make_recovery(tmp_path)
        capture(meshctl.recovery_cmd_run, Args(name="rec-1"))
        r = capture(meshctl.recovery_cmd_run, Args(name="rec-1"))
        assert "errors" in r
        assert any(e["field"] == "status.state" and e["type"] == "invalid" for e in r["errors"])

    def test_terminal_state_irreversible(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        make_recovery(tmp_path)
        capture(meshctl.recovery_cmd_run, Args(name="rec-1"))
        r = capture(meshctl.recovery_cmd_run, Args(name="rec-1"))
        assert "errors" in r


# ---------------------------------------------------------------------------
# Recovery spec immutability
# ---------------------------------------------------------------------------

class TestRecoverySpecImmutability:
    def test_update_snapshot_ref_rejected(self, tmp_path):
        make_mesh(tmp_path)
        path_s1 = yaml_file(tmp_path, {"metadata": {"name": "snap-1"}, "spec": {"meshRef": "test-mesh"}}, name="s1.yaml")
        path_s2 = yaml_file(tmp_path, {"metadata": {"name": "snap-2"}, "spec": {"meshRef": "test-mesh"}}, name="s2.yaml")
        capture(meshctl.snapshot_cmd_create, Args(file=path_s1))
        capture(meshctl.snapshot_cmd_create, Args(file=path_s2))
        make_recovery(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "rec-1"}, "spec": {"meshRef": "test-mesh", "snapshotRef": "snap-2"}})
        r = capture(meshctl.recovery_cmd_update, Args(file=path))
        assert "errors" in r
        assert any(e["type"] == "immutable" for e in r["errors"])

    def test_no_spec_change_accepted(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        make_recovery(tmp_path)
        path = yaml_file(tmp_path, {"metadata": {"name": "rec-1"}, "spec": {}})
        r = capture(meshctl.recovery_cmd_update, Args(file=path))
        assert "errors" not in r
        assert r["metadata"]["name"] == "rec-1"


# ---------------------------------------------------------------------------
# Output field rules (task group 5)
# ---------------------------------------------------------------------------

class TestOutputFields:
    def test_detail_absent_on_succeeded_task(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path)
        r = capture(meshctl.task_cmd_run, Args(name="my-task"))
        assert r["status"]["state"] == "Succeeded"
        assert "detail" not in r["status"]

    def test_detail_present_on_failed_task(self, tmp_path):
        make_mesh(tmp_path)
        make_task(tmp_path, inline="FAIL: oops")
        r = capture(meshctl.task_cmd_run, Args(name="my-task"))
        assert r["status"]["state"] == "Failed"
        assert "detail" in r["status"]

    def test_storage_ref_on_succeeded_snapshot(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        r = capture(meshctl.snapshot_cmd_run, Args(name="snap-1"))
        assert r["status"]["state"] == "Succeeded"
        assert "storageRef" in r["status"]
        assert r["status"]["storageRef"]

    def test_no_storage_ref_on_recovery(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        make_recovery(tmp_path)
        r = capture(meshctl.recovery_cmd_run, Args(name="rec-1"))
        assert r["status"]["state"] == "Succeeded"
        assert "storageRef" not in r["status"]

    def test_detail_absent_on_succeeded_snapshot(self, tmp_path):
        make_mesh(tmp_path)
        make_snapshot(tmp_path)
        r = capture(meshctl.snapshot_cmd_run, Args(name="snap-1"))
        assert "detail" not in r["status"]

    def test_error_shape_consistent(self, tmp_path):
        path = yaml_file(tmp_path, {"metadata": {"name": "my-task"}, "spec": {"meshRef": "no-mesh", "inline": "x"}})
        r = capture(meshctl.task_cmd_create, Args(file=path))
        assert "errors" in r
        assert isinstance(r["errors"], list)
        for e in r["errors"]:
            assert set(e.keys()) >= {"field", "type", "message"}
