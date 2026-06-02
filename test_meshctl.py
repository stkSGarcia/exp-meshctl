#!/usr/bin/env python3
"""Tests for mesh migration strategies (checkpoint 6)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import meshctl


def _run(monkeypatch_store, store_data, fn, *args):
    """Run a command handler with a pre-seeded store."""
    store_data_copy = json.loads(json.dumps(store_data))
    captured = []

    def fake_load():
        return json.loads(json.dumps(store_data_copy))

    def fake_save(s):
        store_data_copy.clear()
        store_data_copy.update(s)

    original_print = meshctl.print_json

    def capture_print(obj):
        captured.append(obj)

    meshctl.print_json = capture_print
    orig_load = meshctl.load_store
    orig_save = meshctl.save_store
    meshctl.load_store = fake_load
    meshctl.save_store = fake_save
    try:
        fn(*args)
    finally:
        meshctl.print_json = original_print
        meshctl.load_store = orig_load
        meshctl.save_store = orig_save

    return captured[0] if captured else None, store_data_copy


def _yaml_file(content):
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def _fresh_mesh(runtime=None, strategy="FullStop", instances=2, regions=None):
    spec = {
        "instances": instances,
        "resources": {"memory": {"limit": "1Gi", "request": "1Gi"}},
        "access": {
            "authentication": {"enabled": True, "digestAlgorithm": "SHA-256"},
            "permissions": {"enabled": False},
            "encryption": {"source": "None", "clientMode": "None"},
        },
        "migration": {"strategy": strategy},
        "network": {"storage": {"size": "1Gi", "ephemeral": False}, "replicationFactor": min(instances, 3)},
    }
    if runtime:
        spec["runtime"] = runtime
    if regions:
        spec["regions"] = regions
    return {
        "metadata": {"name": "test-mesh"},
        "spec": spec,
        "status": {
            "state": "Running",
            "stable": True,
            "instances": {"ready": instances, "starting": 0, "stopped": 0},
            "conditions": [
                {"type": "Healthy", "status": "True", "message": ""},
                {"type": "PrechecksPassed", "status": "True", "message": ""},
            ],
        },
    }


class TestCatalogValidation(unittest.TestCase):
    """9.1 Test catalog validation."""

    def _create(self, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, _ = _run(None, {}, meshctl.cmd_create, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result

    def test_unknown_version_rejected(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: 1\n  runtime: '9.9.9'\n")
        self.assertIn("errors", r)
        self.assertEqual(r["errors"][0]["field"], "spec.runtime")
        self.assertEqual(r["errors"][0]["type"], "invalid")

    def test_skipped_version_rejected(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: 1\n  runtime: '3.1.0'\n")
        self.assertIn("errors", r)
        self.assertIn("skipped", r["errors"][0]["message"])

    def test_deprecated_version_accepted_with_warning(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: 1\n  runtime: '3.0.0'\n")
        self.assertNotIn("errors", r)
        self.assertIn("warnings", r)
        self.assertEqual(r["warnings"][0]["field"], "spec.runtime")
        self.assertIn("deprecated", r["warnings"][0]["message"])

    def test_supported_version_no_warning(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: 1\n  runtime: '4.0.0'\n")
        self.assertNotIn("errors", r)
        self.assertNotIn("warnings", r)

    def test_absent_runtime_skips_catalog(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: 1\n")
        self.assertNotIn("errors", r)
        self.assertNotIn("warnings", r)


class TestWarningShape(unittest.TestCase):
    """9.2 Test warning output shape."""

    def _create(self, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, _ = _run(None, {}, meshctl.cmd_create, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result

    def test_warning_present_for_deprecated(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: 1\n  runtime: '3.0.0'\n")
        self.assertIn("warnings", r)
        w = r["warnings"][0]
        self.assertIn("field", w)
        self.assertIn("message", w)

    def test_warnings_absent_when_none(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: 1\n")
        self.assertNotIn("warnings", r)

    def test_warnings_suppressed_when_error(self):
        r = self._create("metadata:\n  name: my-mesh\nspec:\n  instances: -1\n  runtime: '3.0.0'\n")
        self.assertIn("errors", r)
        self.assertNotIn("warnings", r)


class TestStrategyAcceptance(unittest.TestCase):
    """9.3 Test strategy acceptance."""

    def _create_yaml(self, strategy, instances=1):
        return f"metadata:\n  name: my-mesh\nspec:\n  instances: {instances}\n  migration:\n    strategy: '{strategy}'\n"

    def _create(self, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, _ = _run(None, {}, meshctl.cmd_create, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result

    def test_fullstop_accepted(self):
        r = self._create(self._create_yaml("FullStop"))
        self.assertNotIn("errors", r)

    def test_livemigration_accepted(self):
        r = self._create(self._create_yaml("LiveMigration"))
        self.assertNotIn("errors", r)

    def test_rollingpatch_accepted(self):
        r = self._create(self._create_yaml("RollingPatch"))
        self.assertNotIn("errors", r)

    def test_invalid_strategy_rejected(self):
        r = self._create(self._create_yaml("RollingUpdate"))
        self.assertIn("errors", r)
        self.assertEqual(r["errors"][0]["field"], "spec.migration.strategy")
        self.assertEqual(r["errors"][0]["type"], "invalid")


class TestDowngradeRejection(unittest.TestCase):
    """9.4 Test downgrade rejection across all strategies."""

    def _update(self, store, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, new_store = _run(None, store, meshctl.cmd_update, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result, new_store

    def test_downgrade_rejected_fullstop(self):
        store = {"test-mesh": _fresh_mesh(runtime="4.0.0", strategy="FullStop")}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '3.1.1'\n")
        self.assertIn("errors", r)
        self.assertIn("downgrade", r["errors"][0]["message"])

    def test_downgrade_rejected_livemigration(self):
        store = {"test-mesh": _fresh_mesh(runtime="4.0.0", strategy="LiveMigration")}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '3.1.1'\n")
        self.assertIn("errors", r)
        self.assertIn("downgrade", r["errors"][0]["message"])


class TestRollingPatchConstraints(unittest.TestCase):
    """9.5 Test RollingPatch constraints independently and both failing."""

    def _update(self, store, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, new_store = _run(None, store, meshctl.cmd_update, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result, new_store

    def test_constraint1_only_diff_major_minor(self):
        # 3.1.1 → 4.0.0: diff major.minor AND major >= 4; only constraint 1 fails
        store = {"test-mesh": _fresh_mesh(runtime="3.1.1", strategy="RollingPatch")}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '4.0.0'\n")
        self.assertIn("errors", r)
        msgs = [e["message"] for e in r["errors"]]
        self.assertTrue(any("major.minor" in m for m in msgs))
        self.assertFalse(any("major version" in m for m in msgs))

    def test_constraint2_only_target_major_lt4(self):
        # 3.1.0 → not in catalog; use 3.0.0 → 3.1.1: same major.minor? no, 3.0 ≠ 3.1
        # Use a catalog-valid scenario where same major.minor but target major < 4
        # 3.1.1 → 3.1.1 would be same version, not a change
        # Actually we need same major.minor AND target major < 4:
        # 3.0.0 → 3.0.x but there are only 3.0.0 in catalog (deprecated)
        # Let's inject a fake version into the catalog for this test
        meshctl.RUNTIME_CATALOG["3.0.1"] = "supported"
        store = {"test-mesh": _fresh_mesh(runtime="3.0.0", strategy="RollingPatch")}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '3.0.1'\n")
        del meshctl.RUNTIME_CATALOG["3.0.1"]
        self.assertIn("errors", r)
        msgs = [e["message"] for e in r["errors"]]
        self.assertTrue(any("major version" in m for m in msgs))
        self.assertFalse(any("major.minor" in m for m in msgs))

    def test_both_constraints_fail(self):
        # 3.0.0 → 3.1.1: diff major.minor (3.0 ≠ 3.1) AND target major=3 < 4
        store = {"test-mesh": _fresh_mesh(runtime="3.0.0", strategy="RollingPatch")}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '3.1.1'\n")
        self.assertIn("errors", r)
        self.assertEqual(len(r["errors"]), 2)


class TestLiveMigrationMultiRegion(unittest.TestCase):
    """9.6 Test LiveMigration multi-region rejection."""

    def _create(self, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, _ = _run(None, {}, meshctl.cmd_create, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result

    def test_livemigration_with_regions_rejected(self):
        yaml = (
            "metadata:\n  name: my-mesh\n"
            "spec:\n  instances: 1\n"
            "  migration:\n    strategy: LiveMigration\n"
            "  regions:\n    - us-east\n    - eu-west\n"
        )
        r = self._create(yaml)
        self.assertIn("errors", r)
        self.assertEqual(r["errors"][0]["field"], "spec.migration.strategy")
        self.assertIn("multi-region", r["errors"][0]["message"])

    def test_livemigration_without_regions_accepted(self):
        yaml = (
            "metadata:\n  name: my-mesh\n"
            "spec:\n  instances: 1\n"
            "  migration:\n    strategy: LiveMigration\n"
        )
        r = self._create(yaml)
        self.assertNotIn("errors", r)


class TestMigrationLifecycle(unittest.TestCase):
    """9.7 Test first runtime assignment vs version change."""

    def _update(self, store, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, new_store = _run(None, store, meshctl.cmd_update, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result, new_store

    def test_first_assignment_no_migration(self):
        store = {"test-mesh": _fresh_mesh()}  # no runtime
        r, s = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '4.0.0'\n")
        self.assertNotIn("errors", r)
        self.assertNotIn("migration", r.get("status", {}))
        cond_types = [c["type"] for c in r["status"]["conditions"]]
        self.assertNotIn("Migration", cond_types)

    def test_version_change_starts_migration(self):
        store = {"test-mesh": _fresh_mesh(runtime="3.1.1")}
        r, s = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '4.0.0'\n")
        self.assertNotIn("errors", r)
        self.assertIn("migration", r["status"])
        self.assertEqual(r["status"]["migration"]["sourceRuntime"], "3.1.1")
        self.assertEqual(r["status"]["migration"]["targetRuntime"], "4.0.0")
        cond_types = [c["type"] for c in r["status"]["conditions"]]
        self.assertIn("Migration", cond_types)
        self.assertFalse(r["status"]["stable"])


class TestMeshMigrateCommand(unittest.TestCase):
    """9.8 Test mesh migrate happy path."""

    def _migrate(self, store, name):
        result, new_store = _run(None, store, meshctl.cmd_migrate, type("a", (), {"name": name})())
        return result, new_store

    def _mesh_with_migration(self, strategy="FullStop", runtime="3.1.1", target="4.0.0"):
        stages = meshctl.MIGRATION_STAGES[strategy]
        m = _fresh_mesh(runtime=target, strategy=strategy)
        m["status"]["conditions"].append({"type": "Migration", "status": "True", "message": ""})
        m["status"]["conditions"].sort(key=lambda c: c["type"])
        m["status"]["stable"] = False
        m["status"]["migration"] = {
            "sourceRuntime": runtime,
            "targetRuntime": target,
            "stage": stages[0],
        }
        m["spec"]["runtime"] = target
        return m

    def test_fullstop_single_stage_completes(self):
        store = {"test-mesh": self._mesh_with_migration("FullStop")}
        r, s = self._migrate(store, "test-mesh")
        self.assertNotIn("errors", r)
        self.assertNotIn("migration", r["status"])
        cond_types = [c["type"] for c in r["status"]["conditions"]]
        self.assertNotIn("Migration", cond_types)
        self.assertTrue(r["status"]["stable"])

    def test_livemigration_advance_stage(self):
        store = {"test-mesh": self._mesh_with_migration("LiveMigration")}
        r, s = self._migrate(store, "test-mesh")
        self.assertNotIn("errors", r)
        self.assertEqual(r["status"]["migration"]["stage"], "Migrate")

    def test_full_resource_printed(self):
        store = {"test-mesh": self._mesh_with_migration("FullStop")}
        r, _ = self._migrate(store, "test-mesh")
        self.assertIn("metadata", r)
        self.assertIn("spec", r)
        self.assertIn("status", r)


class TestMeshMigrateErrors(unittest.TestCase):
    """9.9 Test mesh migrate error cases."""

    def _migrate(self, store, name):
        result, new_store = _run(None, store, meshctl.cmd_migrate, type("a", (), {"name": name})())
        return result, new_store

    def test_not_found(self):
        r, _ = self._migrate({}, "nonexistent")
        self.assertIn("errors", r)
        self.assertEqual(r["errors"][0]["field"], "metadata.name")
        self.assertEqual(r["errors"][0]["type"], "not_found")

    def test_no_active_migration(self):
        store = {"test-mesh": _fresh_mesh(runtime="4.0.0")}
        r, _ = self._migrate(store, "test-mesh")
        self.assertIn("errors", r)
        self.assertEqual(r["errors"][0]["field"], "status.migration")
        self.assertEqual(r["errors"][0]["type"], "invalid")
        self.assertIn("no active migration", r["errors"][0]["message"])


class TestActiveMigrationGuards(unittest.TestCase):
    """9.10 Test active migration guards."""

    def _update(self, store, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, new_store = _run(None, store, meshctl.cmd_update, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result, new_store

    def _mesh_with_active_migration(self):
        m = _fresh_mesh(runtime="4.0.0")
        m["status"]["conditions"].append({"type": "Migration", "status": "True", "message": ""})
        m["status"]["conditions"].sort(key=lambda c: c["type"])
        m["status"]["stable"] = False
        m["status"]["migration"] = {"sourceRuntime": "3.1.1", "targetRuntime": "4.0.0", "stage": "Migrate"}
        return m

    def test_runtime_change_blocked(self):
        store = {"test-mesh": self._mesh_with_active_migration()}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '3.1.1'\n")
        self.assertIn("errors", r)
        self.assertEqual(r["errors"][0]["field"], "spec.runtime")
        self.assertIn("migration is in progress", r["errors"][0]["message"])

    def test_strategy_change_blocked(self):
        store = {"test-mesh": self._mesh_with_active_migration()}
        r, _ = self._update(
            store,
            "metadata:\n  name: test-mesh\nspec:\n  migration:\n    strategy: LiveMigration\n",
        )
        self.assertIn("errors", r)
        self.assertEqual(r["errors"][0]["field"], "spec.migration.strategy")
        self.assertIn("migration is in progress", r["errors"][0]["message"])

    def test_other_fields_allowed(self):
        store = {"test-mesh": self._mesh_with_active_migration()}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  instances: 3\n")
        self.assertNotIn("errors", r)


class TestStabilityDuringMigration(unittest.TestCase):
    """9.11 Test status.stable = false during active migration."""

    def _update(self, store, yaml_content):
        path = _yaml_file(yaml_content)
        try:
            result, new_store = _run(None, store, meshctl.cmd_update, type("a", (), {"file": path})())
        finally:
            os.unlink(path)
        return result, new_store

    def test_stable_false_when_migration_active(self):
        store = {"test-mesh": _fresh_mesh(runtime="3.1.1")}
        r, _ = self._update(store, "metadata:\n  name: test-mesh\nspec:\n  runtime: '4.0.0'\n")
        self.assertFalse(r["status"]["stable"])

    def test_stable_true_after_migration_completes(self):
        m = _fresh_mesh(runtime="4.0.0")
        m["status"]["conditions"].append({"type": "Migration", "status": "True", "message": ""})
        m["status"]["conditions"].sort(key=lambda c: c["type"])
        m["status"]["stable"] = False
        m["status"]["migration"] = {"sourceRuntime": "3.1.1", "targetRuntime": "4.0.0", "stage": "Migrate"}
        store = {"test-mesh": m}
        result, _ = _run(None, store, meshctl.cmd_migrate, type("a", (), {"name": "test-mesh"})())
        self.assertTrue(result["status"]["stable"])


class TestMigrationCompletion(unittest.TestCase):
    """9.12 Test migration completion clears status.migration and Migration condition."""

    def _migrate(self, store, name):
        result, new_store = _run(None, store, meshctl.cmd_migrate, type("a", (), {"name": name})())
        return result, new_store

    def test_completion_clears_migration_condition(self):
        m = _fresh_mesh(runtime="4.0.0")
        m["status"]["conditions"].append({"type": "Migration", "status": "True", "message": ""})
        m["status"]["conditions"].sort(key=lambda c: c["type"])
        m["status"]["migration"] = {"sourceRuntime": "3.1.1", "targetRuntime": "4.0.0", "stage": "Migrate"}
        store = {"test-mesh": m}
        r, _ = self._migrate(store, "test-mesh")
        cond_types = [c["type"] for c in r["status"]["conditions"]]
        self.assertNotIn("Migration", cond_types)

    def test_completion_clears_status_migration(self):
        m = _fresh_mesh(runtime="4.0.0")
        m["status"]["conditions"].append({"type": "Migration", "status": "True", "message": ""})
        m["status"]["conditions"].sort(key=lambda c: c["type"])
        m["status"]["migration"] = {"sourceRuntime": "3.1.1", "targetRuntime": "4.0.0", "stage": "Migrate"}
        store = {"test-mesh": m}
        r, _ = self._migrate(store, "test-mesh")
        self.assertNotIn("migration", r["status"])


if __name__ == "__main__":
    unittest.main()
