from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MESHCTL = ROOT / "meshctl.py"


class MeshCtlCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = self.root / "store.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_meshctl(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["MESHCTL_STORE"] = str(self.store)
        return subprocess.run(
            [sys.executable, str(MESHCTL), *args],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def write_yaml(self, content: str) -> Path:
        path = self.root / "mesh.yaml"
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
        return path

    def assert_json_stdout(self, result: subprocess.CompletedProcess[str]):
        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.returncode)
        return json.loads(result.stdout)

    def create_mesh(self, name: str, instances: int = 1):
        return self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        f"""
                        metadata:
                          name: {name}
                        spec:
                          instances: {instances}
                        """
                    )
                ),
            )
        )

    def test_create_describe_list_and_delete(self) -> None:
        alpha = self.write_yaml(
            """
            metadata:
              name: alpha
            spec:
              instances: 2
              runtime: 3.1.1
              resources:
                memory:
                  limit: 2Gi
                  request: 1Gi
                cpu:
                  limit: 1000m
                  request: 500m
              access:
                authentication:
                  enabled: false
              migration:
                strategy: FullStop
            """
        )

        created = self.assert_json_stdout(
            self.run_meshctl("mesh", "create", "-f", str(alpha))
        )
        self.assertEqual("alpha", created["metadata"]["name"])
        self.assertEqual("Running", created["status"]["state"])
        self.assertEqual(False, created["spec"]["access"]["authentication"]["enabled"])

        beta = self.write_yaml(
            """
            metadata:
              name: beta
            spec:
              instances: 1
            """
        )
        self.assert_json_stdout(self.run_meshctl("mesh", "create", "-f", str(beta)))

        described = self.assert_json_stdout(
            self.run_meshctl("mesh", "describe", "alpha")
        )
        self.assertEqual(created, described)

        listed = self.assert_json_stdout(self.run_meshctl("mesh", "list"))
        self.assertEqual(
            [
                {"name": "alpha", "status": {"state": "Running"}},
                {"name": "beta", "status": {"state": "Running"}},
            ],
            listed,
        )

        deleted = self.assert_json_stdout(self.run_meshctl("mesh", "delete", "alpha"))
        self.assertEqual({"name": "alpha"}, deleted["metadata"])
        self.assertTrue(deleted["message"])
        listed_after_delete = self.assert_json_stdout(self.run_meshctl("mesh", "list"))
        self.assertEqual(["beta"], [item["name"] for item in listed_after_delete])

    def test_defaults_and_absent_optional_fields(self) -> None:
        path = self.write_yaml(
            """
            metadata:
              name: minimal
            spec:
            """
        )

        created = self.assert_json_stdout(
            self.run_meshctl("mesh", "create", "-f", str(path))
        )

        self.assertEqual(1, created["spec"]["instances"])
        self.assertEqual(
            {"limit": "1Gi", "request": "1Gi"},
            created["spec"]["resources"]["memory"],
        )
        self.assertEqual(
            {
                "authentication": {"enabled": True, "digestAlgorithm": "SHA-256"},
                "permissions": {"enabled": False},
                "encryption": {"source": "None", "clientMode": "None"},
            },
            created["spec"]["access"],
        )
        self.assertEqual("FullStop", created["spec"]["migration"]["strategy"])
        self.assertEqual(
            {"size": "1Gi", "ephemeral": False},
            created["spec"]["network"]["storage"],
        )
        self.assertEqual(1, created["spec"]["network"]["replicationFactor"])
        self.assertNotIn("runtime", created["spec"])
        self.assertNotIn("cpu", created["spec"]["resources"])

        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "minimal"))
        self.assertEqual(created["spec"]["access"], described["spec"]["access"])

    def test_access_authentication_validation_and_output(self) -> None:
        credentialed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: credentialed
                        spec:
                          access:
                            credentialRef: mesh-secret
                            authentication:
                              digestAlgorithm: SHA-512
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"enabled": True, "digestAlgorithm": "SHA-512"},
            credentialed["spec"]["access"]["authentication"],
        )
        self.assertEqual("mesh-secret", credentialed["spec"]["access"]["credentialRef"])

        invalid_digest = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-digest
                        spec:
                          access:
                            authentication:
                              digestAlgorithm: MD5
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.access.authentication.digestAlgorithm", "invalid")},
            {(item["field"], item["type"]) for item in invalid_digest["errors"]},
        )

        disabled = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: disabled-auth
                        spec:
                          access:
                            authentication:
                              enabled: false
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"enabled": False},
            disabled["spec"]["access"]["authentication"],
        )
        self.assertNotIn("credentialRef", disabled["spec"]["access"])

        forbidden = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: forbidden-auth
                        spec:
                          access:
                            credentialRef: mesh-secret
                            authentication:
                              enabled: false
                              digestAlgorithm: SHA-256
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                ("spec.access.authentication.digestAlgorithm", "forbidden"),
                ("spec.access.credentialRef", "forbidden"),
            },
            {(item["field"], item["type"]) for item in forbidden["errors"]},
        )

    def test_access_permissions_validation_and_output(self) -> None:
        role_based = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: role-based
                        spec:
                          access:
                            permissions:
                              enabled: true
                              roles: [{"name": "admin", "permissions": ["read", "write"]}]
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                "enabled": True,
                "roles": [{"name": "admin", "permissions": ["read", "write"]}],
            },
            role_based["spec"]["access"]["permissions"],
        )

        missing_roles = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: no-roles
                        spec:
                          access:
                            permissions:
                              enabled: true
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.access.permissions.roles", "required")},
            {(item["field"], item["type"]) for item in missing_roles["errors"]},
        )

        invalid_roles = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-roles
                        spec:
                          access:
                            permissions:
                              enabled: true
                              roles: [{"name": "", "permissions": []}, {"name": "admin", "permissions": ["read"]}, {"name": "admin", "permissions": ["write"]}]
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                ("spec.access.permissions.roles", "duplicate"),
                ("spec.access.permissions.roles[0].name", "required"),
                ("spec.access.permissions.roles[0].permissions", "required"),
            },
            {(item["field"], item["type"]) for item in invalid_roles["errors"]},
        )

    def test_access_encryption_validation_and_output(self) -> None:
        secret = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: secret-encryption
                        spec:
                          access:
                            encryption:
                              source: Secret
                              certRef: mesh-cert
                              clientMode: Authenticate
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"source": "Secret", "clientMode": "Authenticate", "certRef": "mesh-cert"},
            secret["spec"]["access"]["encryption"],
        )

        service = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: service-encryption
                        spec:
                          access:
                            encryption:
                              source: Service
                              certServiceRef: cert-service
                              clientMode: Validate
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                "source": "Service",
                "clientMode": "Validate",
                "certServiceRef": "cert-service",
            },
            service["spec"]["access"]["encryption"],
        )

        invalid = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-encryption
                        spec:
                          access:
                            encryption:
                              source: None
                              certRef: mesh-cert
                              certServiceRef: cert-service
                              clientMode: Authenticate
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                ("spec.access.encryption.certRef", "forbidden"),
                ("spec.access.encryption.certServiceRef", "forbidden"),
                ("spec.access.encryption.clientMode", "invalid"),
            },
            {(item["field"], item["type"]) for item in invalid["errors"]},
        )

        missing_secret_ref = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-cert
                        spec:
                          access:
                            encryption:
                              source: Secret
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.access.encryption.certRef", "required")},
            {(item["field"], item["type"]) for item in missing_secret_ref["errors"]},
        )

    def test_access_update_validation_is_atomic_and_errors_are_sorted(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: access-atomic
                        spec:
                          access:
                            encryption:
                              source: Secret
                              certRef: original-cert
                        """
                    )
                ),
            )
        )
        self.assertEqual("Secret", created["spec"]["access"]["encryption"]["source"])

        invalid_update = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: access-atomic
                        spec:
                          access:
                            authentication:
                              enabled: false
                              digestAlgorithm: SHA-256
                            encryption:
                              source: None
                              clientMode: Authenticate
                        """
                    )
                ),
            )
        )
        error_pairs = [(item["field"], item["type"]) for item in invalid_update["errors"]]
        self.assertEqual(sorted(error_pairs), error_pairs)
        self.assertIn(
            ("spec.access.authentication.digestAlgorithm", "forbidden"),
            error_pairs,
        )
        self.assertIn(("spec.access.encryption.certRef", "forbidden"), error_pairs)
        self.assertIn(("spec.access.encryption.clientMode", "invalid"), error_pairs)

        described = self.assert_json_stdout(
            self.run_meshctl("mesh", "describe", "access-atomic")
        )
        self.assertEqual(created["spec"]["access"], described["spec"]["access"])

    def test_validation_errors_and_no_stderr(self) -> None:
        path = self.write_yaml(
            """
            metadata:
              name: Bad_Name
            spec:
              instances: -1
              runtime: 1.2
              resources:
                memory:
                  limit: 1Gi
                  request: 2Gi
                cpu:
                  limit: 100m
                  request: 1
              migration:
                strategy: Rolling
            """
        )

        payload = self.assert_json_stdout(
            self.run_meshctl("mesh", "create", "-f", str(path))
        )
        errors = {(item["field"], item["type"]) for item in payload["errors"]}
        self.assertIn(("metadata.name", "invalid"), errors)
        self.assertIn(("spec.instances", "invalid"), errors)
        self.assertIn(("spec.runtime", "invalid"), errors)
        self.assertIn(("spec.resources.memory.request", "invalid"), errors)
        self.assertIn(("spec.resources.cpu.request", "invalid"), errors)
        self.assertIn(("spec.migration.strategy", "invalid"), errors)
        self.assertFalse(self.store.exists())

    def test_runtime_catalog_validation_and_warnings(self) -> None:
        supported = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: supported-runtime
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        self.assertEqual("3.1.1", supported["spec"]["runtime"])
        self.assertNotIn("warnings", supported)

        deprecated = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: deprecated-runtime
                        spec:
                          runtime: 3.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            [
                {
                    "field": "spec.runtime",
                    "message": "runtime version '3.0.0' is deprecated",
                }
            ],
            deprecated["warnings"],
        )

        skipped = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: skipped-runtime
                        spec:
                          runtime: 3.1.0
                        """
                    )
                ),
            )
        )
        self.assertIn(
            {
                "field": "spec.runtime",
                "message": "runtime version '3.1.0' is skipped and cannot be targeted",
                "type": "invalid",
            },
            skipped["errors"],
        )

        unknown = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: unknown-runtime
                        spec:
                          runtime: 9.9.9
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.runtime", "invalid"),
            {(item["field"], item["type"]) for item in unknown["errors"]},
        )

        warning_suppressed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-deprecated-runtime
                        spec:
                          instances: -1
                          runtime: 3.0.0
                        """
                    )
                ),
            )
        )
        self.assertIn("errors", warning_suppressed)
        self.assertNotIn("warnings", warning_suppressed)

        absent = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: absent-runtime
                        spec:
                        """
                    )
                ),
            )
        )
        self.assertNotIn("runtime", absent["spec"])

    def test_migration_strategy_and_version_change_validation(self) -> None:
        for name, strategy in (
            ("strategy-fullstop", "FullStop"),
            ("strategy-live", "LiveMigration"),
            ("strategy-rolling", "RollingPatch"),
        ):
            created = self.assert_json_stdout(
                self.run_meshctl(
                    "mesh",
                    "create",
                    "-f",
                    str(
                        self.write_yaml(
                            f"""
                            metadata:
                              name: {name}
                            spec:
                              migration:
                                strategy: {strategy}
                            """
                        )
                    ),
                )
            )
            self.assertEqual(strategy, created["spec"]["migration"]["strategy"])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: downgrade
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        downgrade = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: downgrade
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        self.assertIn(
            {
                "field": "spec.runtime",
                "message": "version downgrade from '4.0.0' to '3.1.1' is not allowed",
                "type": "invalid",
            },
            downgrade["errors"],
        )

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-fail
                        spec:
                          runtime: 3.0.0
                        """
                    )
                ),
            )
        )
        rolling_fail = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-fail
                        spec:
                          runtime: 3.1.1
                          migration:
                            strategy: RollingPatch
                        """
                    )
                ),
            )
        )
        runtime_errors = [
            item
            for item in rolling_fail["errors"]
            if item["field"] == "spec.runtime" and item["type"] == "invalid"
        ]
        self.assertGreaterEqual(len(runtime_errors), 2)

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-ok
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        rolling_ok = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-ok
                        spec:
                          runtime: 4.0.1
                          migration:
                            strategy: RollingPatch
                        """
                    )
                ),
            )
        )
        self.assertEqual("Migrate", rolling_ok["status"]["migration"]["stage"])

        live_regions = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-regions
                        spec:
                          regions: us-east
                          migration:
                            strategy: LiveMigration
                        """
                    )
                ),
            )
        )
        self.assertIn(
            {
                "field": "spec.migration.strategy",
                "message": "LiveMigration strategy is not supported with multi-region topology",
                "type": "invalid",
            },
            live_regions["errors"],
        )

    def test_required_limits_and_name(self) -> None:
        path = self.write_yaml(
            """
            metadata:
              name:
            spec:
              resources:
                memory:
                  request: 1Gi
                cpu:
                  request: 100m
            """
        )

        payload = self.assert_json_stdout(
            self.run_meshctl("mesh", "create", "-f", str(path))
        )
        errors = {(item["field"], item["type"]) for item in payload["errors"]}
        self.assertIn(("metadata.name", "required"), errors)
        self.assertIn(("spec.resources.memory.limit", "required"), errors)
        self.assertIn(("spec.resources.cpu.limit", "required"), errors)

    def test_duplicate_does_not_overwrite(self) -> None:
        first = self.write_yaml(
            """
            metadata:
              name: duplicate
            spec:
              instances: 1
            """
        )
        self.assert_json_stdout(self.run_meshctl("mesh", "create", "-f", str(first)))

        second = self.write_yaml(
            """
            metadata:
              name: duplicate
            spec:
              instances: 3
            """
        )
        payload = self.assert_json_stdout(
            self.run_meshctl("mesh", "create", "-f", str(second))
        )
        self.assertEqual(
            {("metadata.name", "duplicate")},
            {(item["field"], item["type"]) for item in payload["errors"]},
        )
        described = self.assert_json_stdout(
            self.run_meshctl("mesh", "describe", "duplicate")
        )
        self.assertEqual(1, described["spec"]["instances"])

    def test_parse_not_found_and_forbidden_autoscaling_errors(self) -> None:
        missing = self.assert_json_stdout(
            self.run_meshctl("mesh", "describe", "missing")
        )
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing["errors"]},
        )

        invalid_yaml = self.root / "invalid.yaml"
        invalid_yaml.write_text("metadata\n  name: nope\n", encoding="utf-8")
        parse_error = self.assert_json_stdout(
            self.run_meshctl("mesh", "create", "-f", str(invalid_yaml))
        )
        self.assertEqual(
            {("", "parse")},
            {(item["field"], item["type"]) for item in parse_error["errors"]},
        )

        autoscaling = self.write_yaml(
            """
            metadata:
              name: forbidden
            spec:
              nested:
                autoScaling:
                  enabled: true
            """
        )
        forbidden = self.assert_json_stdout(
            self.run_meshctl("mesh", "create", "-f", str(autoscaling))
        )
        self.assertIn(
            ("spec.nested.autoScaling", "forbidden"),
            {(item["field"], item["type"]) for item in forbidden["errors"]},
        )

    def test_delete_not_found_error(self) -> None:
        payload = self.assert_json_stdout(self.run_meshctl("mesh", "delete", "gone"))
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in payload["errors"]},
        )

    def test_update_merges_nested_fields_and_preserves_omitted_values(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: mergeable
                        spec:
                          instances: 2
                          network:
                            storage:
                              size: 5Gi
                              className: slow
                            replicationFactor: 2
                        """
                    )
                ),
            )
        )
        self.assertEqual("5Gi", created["spec"]["network"]["storage"]["size"])

        updated = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: mergeable
                        spec:
                          network:
                            storage:
                              className: fast
                        """
                    )
                ),
            )
        )

        self.assertEqual(2, updated["spec"]["instances"])
        self.assertEqual("fast", updated["spec"]["network"]["storage"]["className"])
        self.assertEqual("5Gi", updated["spec"]["network"]["storage"]["size"])
        self.assertEqual(2, updated["spec"]["network"]["replicationFactor"])

    def test_update_errors_are_atomic(self) -> None:
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: atomic
                        spec:
                          instances: 2
                          network:
                            storage:
                              size: 4Gi
                        """
                    )
                ),
            )
        )

        invalid_yaml = self.root / "invalid-update.yaml"
        invalid_yaml.write_text("metadata\n  name: nope\n", encoding="utf-8")
        parse_error = self.assert_json_stdout(
            self.run_meshctl("mesh", "update", "-f", str(invalid_yaml))
        )
        self.assertEqual(
            {("", "parse")},
            {(item["field"], item["type"]) for item in parse_error["errors"]},
        )

        missing = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing
                        spec:
                          instances: 1
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing["errors"]},
        )

        immutable = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: atomic
                        spec:
                          instances: 1
                          network:
                            storage:
                              size: 8Gi
                        """
                    )
                ),
            )
        )
        errors = immutable["errors"]
        self.assertIn(
            ("spec.network.storage.size", "immutable"),
            {(item["field"], item["type"]) for item in errors},
        )
        self.assertIn("field 'spec.network.storage.size' is immutable after creation", [item["message"] for item in errors])

        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "atomic"))
        self.assertEqual(2, described["spec"]["instances"])
        self.assertEqual("4Gi", described["spec"]["network"]["storage"]["size"])

    def test_storage_output_projection_and_canonical_size(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: cache
                        spec:
                          instances: 1
                          network:
                            storage:
                              size: 10Gi
                              ephemeral: true
                        """
                    )
                ),
            )
        )
        storage = created["spec"]["network"]["storage"]
        self.assertEqual({"ephemeral": True}, storage)

        store = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertEqual("10Gi", store["meshes"]["cache"]["spec"]["network"]["storage"]["size"])

        updated = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: cache
                        spec:
                          network:
                            storage:
                              className: local
                        """
                    )
                ),
            )
        )
        self.assertEqual(True, updated["spec"]["network"]["storage"]["ephemeral"])
        self.assertEqual("local", updated["spec"]["network"]["storage"]["className"])
        self.assertNotIn("size", updated["spec"]["network"]["storage"])
        store = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertEqual("10Gi", store["meshes"]["cache"]["spec"]["network"]["storage"]["size"])

    def test_legacy_flat_store_shape_is_loaded_and_saved_as_collections(self) -> None:
        self.store.write_text(
            json.dumps(
                {
                    "legacy": {
                        "metadata": {"name": "legacy"},
                        "spec": {"instances": 1},
                        "status": {},
                    }
                }
            ),
            encoding="utf-8",
        )

        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "legacy"))
        self.assertEqual("legacy", described["metadata"]["name"])
        persisted = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertIn("legacy", persisted["meshes"])
        self.assertEqual({}, persisted["vaults"])

    def test_replication_factor_defaults_and_validation(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: replicas
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        self.assertEqual(2, created["spec"]["network"]["replicationFactor"])

        invalid_create = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-replicas
                        spec:
                          instances: 2
                          network:
                            replicationFactor: 0
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.network.replicationFactor", "invalid"),
            {(item["field"], item["type"]) for item in invalid_create["errors"]},
        )

        invalid_update = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: replicas
                        spec:
                          network:
                            replicationFactor: 3
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.network.replicationFactor", "invalid"),
            {(item["field"], item["type"]) for item in invalid_update["errors"]},
        )
        self.assertIn("3", invalid_update["errors"][0]["message"])
        self.assertIn("2", invalid_update["errors"][0]["message"])

    def test_status_conditions_and_lifecycle_transitions(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: lifecycle
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        self.assertEqual("Running", created["status"]["state"])
        self.assertEqual(True, created["status"]["stable"])
        self.assertEqual({"ready": 2, "starting": 0, "stopped": 0}, created["status"]["instances"])
        self.assertEqual(["Healthy", "PrechecksPassed"], [item["type"] for item in created["status"]["conditions"]])

        scaled_up = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: lifecycle
                        spec:
                          instances: 4
                        """
                    )
                ),
            )
        )
        self.assertEqual(False, scaled_up["status"]["stable"])
        self.assertEqual({"ready": 2, "starting": 2, "stopped": 0}, scaled_up["status"]["instances"])
        self.assertIn("Scaling", [item["type"] for item in scaled_up["status"]["conditions"]])

        described_after_scale = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "lifecycle"))
        self.assertEqual(True, described_after_scale["status"]["stable"])
        self.assertEqual({"ready": 4, "starting": 0, "stopped": 0}, described_after_scale["status"]["instances"])
        self.assertNotIn("Scaling", [item["type"] for item in described_after_scale["status"]["conditions"]])

        scaled_down = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: lifecycle
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        self.assertIn("Scaling", [item["type"] for item in scaled_down["status"]["conditions"]])
        described_after_scale_down = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "lifecycle"))
        self.assertNotIn("Scaling", [item["type"] for item in described_after_scale_down["status"]["conditions"]])

        stopped = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: lifecycle
                        spec:
                          instances: 0
                        """
                    )
                ),
            )
        )
        self.assertEqual("Stopped", stopped["status"]["state"])
        self.assertEqual(False, stopped["status"]["stable"])
        self.assertEqual(2, stopped["status"]["desiredInstancesOnResume"])
        self.assertEqual({"ready": 0, "starting": 0, "stopped": 2}, stopped["status"]["instances"])
        self.assertIn("GracefulShutdown", [item["type"] for item in stopped["status"]["conditions"]])

        described_stopped = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "lifecycle"))
        self.assertEqual(False, described_stopped["status"]["stable"])
        self.assertEqual(2, described_stopped["status"]["desiredInstancesOnResume"])
        self.assertIn("GracefulShutdown", [item["type"] for item in described_stopped["status"]["conditions"]])

        resumed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: lifecycle
                        spec:
                          network:
                            storage:
                              className: warm
                        """
                    )
                ),
            )
        )
        self.assertEqual("Running", resumed["status"]["state"])
        self.assertEqual({"ready": 0, "starting": 2, "stopped": 0}, resumed["status"]["instances"])
        self.assertNotIn("desiredInstancesOnResume", resumed["status"])
        self.assertNotIn("GracefulShutdown", [item["type"] for item in resumed["status"]["conditions"]])

        described_resumed = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "lifecycle"))
        self.assertEqual({"ready": 2, "starting": 0, "stopped": 0}, described_resumed["status"]["instances"])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: lifecycle
                        spec:
                          instances: 0
                        """
                    )
                ),
            )
        )
        explicit_resume = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: lifecycle
                        spec:
                          instances: 3
                        """
                    )
                ),
            )
        )
        self.assertEqual({"ready": 0, "starting": 3, "stopped": 0}, explicit_resume["status"]["instances"])

    def test_runtime_migration_lifecycle_and_update_guards(self) -> None:
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: first-runtime
                        spec:
                        """
                    )
                ),
            )
        )
        first_assignment = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: first-runtime
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        self.assertEqual("3.1.1", first_assignment["spec"]["runtime"])
        self.assertNotIn("migration", first_assignment["status"])
        self.assertNotIn("Migration", [item["type"] for item in first_assignment["status"]["conditions"]])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: migrating
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        started = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: migrating
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual(False, started["status"]["stable"])
        self.assertEqual(
            {"sourceRuntime": "3.1.1", "stage": "Migrate", "targetRuntime": "4.0.0"},
            started["status"]["migration"],
        )
        self.assertIn("Migration", [item["type"] for item in started["status"]["conditions"]])

        runtime_change = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: migrating
                        spec:
                          runtime: 4.0.1
                        """
                    )
                ),
            )
        )
        self.assertIn(
            {
                "field": "spec.runtime",
                "message": "cannot change runtime version while a migration is in progress",
                "type": "invalid",
            },
            runtime_change["errors"],
        )

        strategy_change = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: migrating
                        spec:
                          migration:
                            strategy: LiveMigration
                        """
                    )
                ),
            )
        )
        self.assertIn(
            {
                "field": "spec.migration.strategy",
                "message": "cannot change migration strategy while a migration is in progress",
                "type": "invalid",
            },
            strategy_change["errors"],
        )

        unrelated = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: migrating
                        spec:
                          network:
                            storage:
                              className: warm
                        """
                    )
                ),
            )
        )
        self.assertEqual("warm", unrelated["spec"]["network"]["storage"]["className"])
        self.assertEqual("Migrate", unrelated["status"]["migration"]["stage"])

    def test_mesh_migrate_command_and_rollback(self) -> None:
        missing = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "missing"))
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing["errors"]},
        )

        self.create_mesh("idle")
        idle = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "idle"))
        self.assertIn(
            {
                "field": "status.migration",
                "message": "no active migration for mesh 'idle'",
                "type": "invalid",
            },
            idle["errors"],
        )

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: fullstop
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: fullstop
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        rollback_rejected = self.assert_json_stdout(
            self.run_meshctl("mesh", "migrate", "fullstop", "--rollback")
        )
        self.assertIn(
            ("status.migration", "invalid"),
            {(item["field"], item["type"]) for item in rollback_rejected["errors"]},
        )
        completed = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "fullstop"))
        self.assertNotIn("migration", completed["status"])
        self.assertNotIn("Migration", [item["type"] for item in completed["status"]["conditions"]])
        self.assertEqual(True, completed["status"]["stable"])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live
                        spec:
                          runtime: 3.1.1
                          migration:
                            strategy: LiveMigration
                        """
                    )
                ),
            )
        )
        live_started = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual("Prepare", live_started["status"]["migration"]["stage"])
        advanced = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "live"))
        self.assertEqual("Transfer", advanced["status"]["migration"]["stage"])
        rolled_back = self.assert_json_stdout(
            self.run_meshctl("mesh", "migrate", "live", "--rollback")
        )
        self.assertNotIn("migration", rolled_back["status"])
        self.assertNotIn("Migration", [item["type"] for item in rolled_back["status"]["conditions"]])

    def test_vault_create_describe_list_update_and_delete(self) -> None:
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha
                        spec:
                          instances: 1
                        """
                    )
                ),
            )
        )

        beta = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta
                        spec:
                          meshRef: alpha
                          templateRef: ref-a
                        """
                    )
                ),
            )
        )
        self.assertEqual("beta", beta["metadata"]["name"])
        self.assertEqual("alpha", beta["spec"]["meshRef"])
        self.assertEqual("beta", beta["spec"]["vaultName"])
        self.assertEqual("retain", beta["spec"]["updatePolicy"])
        self.assertEqual("Ready", beta["status"]["state"])
        self.assertEqual(
            [{"message": "", "status": "True", "type": "Ready"}],
            beta["status"]["conditions"],
        )

        alpha_vault = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha-vault
                        spec:
                          meshRef: alpha
                          vaultName: logical-a
                          updatePolicy: recreate
                        """
                    )
                ),
            )
        )
        self.assertEqual("logical-a", alpha_vault["spec"]["vaultName"])

        described = self.assert_json_stdout(self.run_meshctl("vault", "describe", "beta"))
        self.assertEqual(beta, described)

        listed = self.assert_json_stdout(self.run_meshctl("vault", "list"))
        self.assertEqual(
            [
                {
                    "name": "alpha-vault",
                    "meshRef": "alpha",
                    "vaultName": "logical-a",
                    "status": {"state": "Ready"},
                },
                {
                    "name": "beta",
                    "meshRef": "alpha",
                    "vaultName": "beta",
                    "status": {"state": "Ready"},
                },
            ],
            listed,
        )

        updated = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta
                        spec:
                          updatePolicy: recreate
                          templateRef: ref-b
                        """
                    )
                ),
            )
        )
        self.assertEqual("recreate", updated["spec"]["updatePolicy"])
        self.assertEqual("ref-b", updated["spec"]["templateRef"])
        self.assertEqual("alpha", updated["spec"]["meshRef"])
        self.assertEqual("beta", updated["spec"]["vaultName"])

        deleted = self.assert_json_stdout(self.run_meshctl("vault", "delete", "beta"))
        self.assertEqual({"name": "beta"}, deleted["metadata"])
        self.assertTrue(deleted["message"])
        listed_after_delete = self.assert_json_stdout(self.run_meshctl("vault", "list"))
        self.assertEqual(["alpha-vault"], [item["name"] for item in listed_after_delete])

    def test_vault_parse_invalid_input_and_not_found_errors(self) -> None:
        missing_describe = self.assert_json_stdout(
            self.run_meshctl("vault", "describe", "missing")
        )
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing_describe["errors"]},
        )

        missing_delete = self.assert_json_stdout(self.run_meshctl("vault", "delete", "missing"))
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing_delete["errors"]},
        )

        missing_update = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing
                        spec:
                          updatePolicy: recreate
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing_update["errors"]},
        )

        invalid_yaml = self.root / "invalid-vault.yaml"
        invalid_yaml.write_text("metadata\n  name: nope\n", encoding="utf-8")
        parse_error = self.assert_json_stdout(
            self.run_meshctl("vault", "create", "-f", str(invalid_yaml))
        )
        self.assertEqual(
            {("", "parse")},
            {(item["field"], item["type"]) for item in parse_error["errors"]},
        )

        non_mapping = self.root / "vault-list.yaml"
        non_mapping.write_text("- nope\n", encoding="utf-8")
        invalid_root = self.assert_json_stdout(
            self.run_meshctl("vault", "create", "-f", str(non_mapping))
        )
        self.assertEqual(
            {("", "invalid")},
            {(item["field"], item["type"]) for item in invalid_root["errors"]},
        )

    def test_vault_defaults_validation_and_parent_derived_status(self) -> None:
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: parent
                        spec:
                          instances: 1
                        """
                    )
                ),
            )
        )

        missing_parent = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-parent
                        spec:
                          meshRef: absent
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.meshRef", "invalid"),
            {(item["field"], item["type"]) for item in missing_parent["errors"]},
        )
        self.assertIn("absent", missing_parent["errors"][0]["message"])

        invalid_policy = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-policy
                        spec:
                          meshRef: parent
                          updatePolicy: replace
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.updatePolicy", "invalid"),
            {(item["field"], item["type"]) for item in invalid_policy["errors"]},
        )

        both_templates = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: both-templates
                        spec:
                          meshRef: parent
                          template: inline
                          templateRef: external
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.template", "invalid"),
            {(item["field"], item["type"]) for item in both_templates["errors"]},
        )

        ready = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: follows-parent
                        spec:
                          meshRef: parent
                        """
                    )
                ),
            )
        )
        self.assertEqual("Ready", ready["status"]["state"])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: parent
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        pending = self.assert_json_stdout(
            self.run_meshctl("vault", "describe", "follows-parent")
        )
        self.assertEqual("Pending", pending["status"]["state"])
        self.assertEqual("False", pending["status"]["conditions"][0]["status"])

    def test_vault_duplicates_immutable_fields_and_atomic_update(self) -> None:
        for mesh_name in ("alpha", "beta"):
            self.assert_json_stdout(
                self.run_meshctl(
                    "mesh",
                    "create",
                    "-f",
                    str(
                        self.write_yaml(
                            f"""
                            metadata:
                              name: {mesh_name}
                            spec:
                              instances: 1
                            """
                        )
                    ),
                )
            )

        self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: locked
                        spec:
                          meshRef: alpha
                          vaultName: shared
                          updatePolicy: retain
                        """
                    )
                ),
            )
        )

        duplicate_name = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: locked
                        spec:
                          meshRef: alpha
                          vaultName: other
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("metadata.name", "duplicate"),
            {(item["field"], item["type"]) for item in duplicate_name["errors"]},
        )

        duplicate_pair = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: another
                        spec:
                          meshRef: alpha
                          vaultName: shared
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.vaultName", "duplicate"),
            {(item["field"], item["type"]) for item in duplicate_pair["errors"]},
        )

        immutable_mesh = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: locked
                        spec:
                          meshRef: beta
                          updatePolicy: recreate
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.meshRef", "immutable"),
            {(item["field"], item["type"]) for item in immutable_mesh["errors"]},
        )

        immutable_name = self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: locked
                        spec:
                          vaultName: changed
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.vaultName", "immutable"),
            {(item["field"], item["type"]) for item in immutable_name["errors"]},
        )

        described = self.assert_json_stdout(self.run_meshctl("vault", "describe", "locked"))
        self.assertEqual("retain", described["spec"]["updatePolicy"])
        self.assertEqual("alpha", described["spec"]["meshRef"])
        self.assertEqual("shared", described["spec"]["vaultName"])

    def test_mesh_delete_conflicts_with_dependent_vaults(self) -> None:
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: blocked
                        spec:
                          instances: 1
                        """
                    )
                ),
            )
        )
        self.assert_json_stdout(
            self.run_meshctl(
                "vault",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: dependent
                        spec:
                          meshRef: blocked
                        """
                    )
                ),
            )
        )

        blocked = self.assert_json_stdout(self.run_meshctl("mesh", "delete", "blocked"))
        self.assertEqual(
            {("metadata.name", "conflict")},
            {(item["field"], item["type"]) for item in blocked["errors"]},
        )
        self.assertIn("dependent", blocked["errors"][0]["message"])
        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "blocked"))
        self.assertEqual("blocked", described["metadata"]["name"])

        self.assert_json_stdout(self.run_meshctl("vault", "delete", "dependent"))
        deleted = self.assert_json_stdout(self.run_meshctl("mesh", "delete", "blocked"))
        self.assertEqual({"name": "blocked"}, deleted["metadata"])

    def test_task_create_list_describe_update_delete_and_run(self) -> None:
        self.create_mesh("alpha")

        created = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-task
                        spec:
                          meshRef: alpha
                          inline: "echo ok"
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", created["status"]["state"])
        self.assertEqual("alpha", created["spec"]["meshRef"])

        described = self.assert_json_stdout(self.run_meshctl("task", "describe", "beta-task"))
        self.assertEqual(created, described)

        self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha-task
                        spec:
                          meshRef: alpha
                          bundleRef: bundle-a
                        """
                    )
                ),
            )
        )
        listed = self.assert_json_stdout(self.run_meshctl("task", "list"))
        self.assertEqual(["alpha-task", "beta-task"], [item["name"] for item in listed])

        updated = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-task
                        status:
                          state: Initializing
                          detail: hidden
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", updated["status"]["state"])
        self.assertNotIn("detail", updated["status"])

        succeeded = self.assert_json_stdout(self.run_meshctl("task", "run", "beta-task"))
        self.assertEqual("Succeeded", succeeded["status"]["state"])
        self.assertNotIn("detail", succeeded["status"])

        rerun = self.assert_json_stdout(self.run_meshctl("task", "run", "beta-task"))
        self.assertEqual(
            {("status.state", "invalid")},
            {(item["field"], item["type"]) for item in rerun["errors"]},
        )

        deleted = self.assert_json_stdout(self.run_meshctl("task", "delete", "alpha-task"))
        self.assertEqual({"name": "alpha-task"}, deleted["metadata"])

    def test_task_validation_and_inline_failure(self) -> None:
        self.create_mesh("alpha")

        invalid_mesh = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-mesh-task
                        spec:
                          meshRef: absent
                          inline: "echo ok"
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.meshRef", "invalid"),
            {(item["field"], item["type"]) for item in invalid_mesh["errors"]},
        )

        exclusive = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: both-sources
                        spec:
                          meshRef: alpha
                          inline: "echo ok"
                          bundleRef: bundle-a
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec", "invalid")},
            {(item["field"], item["type"]) for item in exclusive["errors"]},
        )
        self.assertEqual(
            "exactly one of 'spec.inline' or 'spec.bundleRef' must be set",
            exclusive["errors"][0]["message"],
        )

        self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: failing-task
                        spec:
                          meshRef: alpha
                          inline: "FAIL: exploded"
                        """
                    )
                ),
            )
        )
        failed = self.assert_json_stdout(self.run_meshctl("task", "run", "failing-task"))
        self.assertEqual("Failed", failed["status"]["state"])
        self.assertEqual("command 1 failed: exploded", failed["status"]["detail"])

    def test_snapshot_defaults_scope_run_immutability_and_dependency_protection(self) -> None:
        self.create_mesh("alpha")

        created = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: snap-alpha
                        spec:
                          meshRef: alpha
                          scope:
                            stores: ["primary"]
                            procedures: ["restore"]
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", created["status"]["state"])
        self.assertEqual(
            {"limit": "1Gi", "request": "1Gi"},
            created["spec"]["resources"]["memory"],
        )
        self.assertEqual(["primary"], created["spec"]["scope"]["stores"])

        succeeded = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "snap-alpha"))
        self.assertEqual("Succeeded", succeeded["status"]["state"])
        self.assertTrue(succeeded["status"]["storageRef"])
        self.assertNotIn("detail", succeeded["status"])

        immutable = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: snap-alpha
                        spec:
                          storage:
                            size: 2Gi
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec", "immutable")},
            {(item["field"], item["type"]) for item in immutable["errors"]},
        )

        self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: recovery-alpha
                        spec:
                          meshRef: alpha
                          snapshotRef: snap-alpha
                        """
                    )
                ),
            )
        )
        blocked = self.assert_json_stdout(self.run_meshctl("snapshot", "delete", "snap-alpha"))
        self.assertEqual(
            {("metadata.name", "conflict")},
            {(item["field"], item["type"]) for item in blocked["errors"]},
        )
        self.assertIn("recovery-alpha", blocked["errors"][0]["message"])

        self.assert_json_stdout(self.run_meshctl("recovery", "delete", "recovery-alpha"))
        deleted = self.assert_json_stdout(self.run_meshctl("snapshot", "delete", "snap-alpha"))
        self.assertEqual({"name": "snap-alpha"}, deleted["metadata"])

    def test_snapshot_validation_and_unknown_run(self) -> None:
        self.create_mesh("alpha")

        invalid_resources = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-snapshot
                        spec:
                          meshRef: alpha
                          resources:
                            memory:
                              limit: 1Gi
                              request: 2Gi
                            cpu:
                              limit: 100m
                              request: 1
                        """
                    )
                ),
            )
        )
        errors = {(item["field"], item["type"]) for item in invalid_resources["errors"]}
        self.assertIn(("spec.resources.memory.request", "invalid"), errors)
        self.assertIn(("spec.resources.cpu.request", "invalid"), errors)

        missing_mesh = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-mesh-snapshot
                        spec:
                          meshRef: absent
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.meshRef", "invalid"),
            {(item["field"], item["type"]) for item in missing_mesh["errors"]},
        )

        self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: snap-unknown
                        spec:
                          meshRef: alpha
                        """
                    )
                ),
            )
        )
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        unknown = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "snap-unknown"))
        self.assertEqual("Unknown", unknown["status"]["state"])
        self.assertTrue(unknown["status"]["detail"])
        self.assertNotIn("storageRef", unknown["status"])

    def test_recovery_validation_list_run_and_immutability(self) -> None:
        self.create_mesh("alpha")
        self.create_mesh("beta")
        for name, mesh_ref in (("snap-alpha", "alpha"), ("snap-beta", "beta")):
            self.assert_json_stdout(
                self.run_meshctl(
                    "snapshot",
                    "create",
                    "-f",
                    str(
                        self.write_yaml(
                            f"""
                            metadata:
                              name: {name}
                            spec:
                              meshRef: {mesh_ref}
                            """
                        )
                    ),
                )
            )

        missing_snapshot = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-snapshot
                        spec:
                          meshRef: alpha
                          snapshotRef: absent
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.snapshotRef", "invalid"),
            {(item["field"], item["type"]) for item in missing_snapshot["errors"]},
        )

        mismatch = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: mismatch
                        spec:
                          meshRef: alpha
                          snapshotRef: snap-beta
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.snapshotRef", "invalid")},
            {(item["field"], item["type"]) for item in mismatch["errors"]},
        )
        self.assertEqual(
            "snapshot 'snap-beta' belongs to mesh 'beta', not 'alpha'",
            mismatch["errors"][0]["message"],
        )

        for recovery_name in ("zeta-recovery", "alpha-recovery"):
            created = self.assert_json_stdout(
                self.run_meshctl(
                    "recovery",
                    "create",
                    "-f",
                    str(
                        self.write_yaml(
                            f"""
                            metadata:
                              name: {recovery_name}
                            spec:
                              meshRef: alpha
                              snapshotRef: snap-alpha
                            """
                        )
                    ),
                )
            )
            self.assertEqual("Initializing", created["status"]["state"])
            self.assertEqual(
                {"limit": "1Gi", "request": "1Gi"},
                created["spec"]["resources"]["memory"],
            )

        listed = self.assert_json_stdout(self.run_meshctl("recovery", "list"))
        self.assertEqual(["alpha-recovery", "zeta-recovery"], [item["name"] for item in listed])

        immutable = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha-recovery
                        spec:
                          scope:
                            stores: ["secondary"]
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec", "immutable")},
            {(item["field"], item["type"]) for item in immutable["errors"]},
        )

        succeeded = self.assert_json_stdout(self.run_meshctl("recovery", "run", "alpha-recovery"))
        self.assertEqual("Succeeded", succeeded["status"]["state"])
        self.assertNotIn("detail", succeeded["status"])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        unknown = self.assert_json_stdout(self.run_meshctl("recovery", "run", "zeta-recovery"))
        self.assertEqual("Unknown", unknown["status"]["state"])
        self.assertTrue(unknown["status"]["detail"])


if __name__ == "__main__":
    unittest.main()
