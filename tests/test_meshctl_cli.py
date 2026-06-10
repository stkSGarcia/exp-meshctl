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

    def assert_json_stdout(self, result: subprocess.CompletedProcess[str]):
        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.returncode)
        return json.loads(result.stdout)

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
        self.assertEqual({"enabled": False}, created["spec"]["management"])
        self.assertNotIn("exposure", created["spec"])
        self.assertNotIn("connectionDetails", created["status"])
        self.assertNotIn("managementConnectionDetails", created["status"])
        self.assertNotIn("runtime", created["spec"])
        self.assertNotIn("cpu", created["spec"]["resources"])

        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "minimal"))
        self.assertEqual(created["spec"]["access"], described["spec"]["access"])

    def test_exposure_modes_connection_details_and_annotations(self) -> None:
        gateway = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: gateway
                        spec:
                          exposure:
                            type: Gateway
                            hostname: gateway.example.test
                            annotations:
                              owner: platform
                              tier: edge
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                "type": "Gateway",
                "hostname": "gateway.example.test",
                "annotations": {"owner": "platform", "tier": "edge"},
            },
            gateway["spec"]["exposure"],
        )
        self.assertEqual(
            {"host": "gateway.example.test", "port": 443, "protocol": "https"},
            gateway["status"]["connectionDetails"],
        )
        self.assertEqual(
            gateway["status"]["connectionDetails"],
            self.assert_json_stdout(self.run_meshctl("mesh", "describe", "gateway"))["status"]["connectionDetails"],
        )

        default_gateway = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: default-gateway
                        spec:
                          exposure:
                            type: Gateway
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"host": "default-gateway-gateway", "port": 443, "protocol": "https"},
            default_gateway["status"]["connectionDetails"],
        )

        direct = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: direct
                        spec:
                          exposure:
                            type: DirectPort
                            port: 443
                            directPort: 30443
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"host": "direct", "port": 30443, "protocol": "https"},
            direct["status"]["connectionDetails"],
        )
        self.assertEqual(443, direct["spec"]["exposure"]["port"])

        balancer = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: balancer
                        spec:
                          exposure:
                            type: Balancer
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"host": "balancer-external", "port": 443, "protocol": "https"},
            balancer["status"]["connectionDetails"],
        )

        store = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertNotIn("connectionDetails", store["meshes"]["gateway"]["status"])

    def test_exposure_validation_errors_are_sorted(self) -> None:
        missing_type = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-exposure-type
                        spec:
                          exposure: {}
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.exposure.type", "required")},
            {(item["field"], item["type"]) for item in missing_type["errors"]},
        )

        invalid_type = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-exposure-type
                        spec:
                          exposure:
                            type: Tunnel
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.exposure.type", "invalid")},
            {(item["field"], item["type"]) for item in invalid_type["errors"]},
        )

        forbidden = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-exposure
                        spec:
                          exposure:
                            type: Balancer
                            hostname: bad.example.test
                            annotations:
                              owner: platform
                            directPort: 30443
                        """
                    )
                ),
            )
        )
        error_pairs = [(item["field"], item["type"]) for item in forbidden["errors"]]
        self.assertEqual(sorted(error_pairs), error_pairs)
        self.assertEqual(
            [
                ("spec.exposure.annotations", "forbidden"),
                ("spec.exposure.directPort", "forbidden"),
                ("spec.exposure.hostname", "forbidden"),
            ],
            error_pairs,
        )

    def test_management_endpoint_output_and_immutability(self) -> None:
        managed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: managed
                        spec:
                          management:
                            enabled: true
                        """
                    )
                ),
            )
        )
        self.assertEqual({"enabled": True}, managed["spec"]["management"])
        self.assertEqual(
            {"host": "managed-admin", "port": 9990, "protocol": "https"},
            managed["status"]["managementConnectionDetails"],
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
                          name: managed
                        spec:
                          management:
                            enabled: false
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                (
                    "spec.management.enabled",
                    "immutable",
                    "field 'spec.management.enabled' is immutable after creation",
                )
            },
            {(item["field"], item["type"], item["message"]) for item in immutable["errors"]},
        )
        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "managed"))
        self.assertTrue(described["spec"]["management"]["enabled"])

    def test_mesh_shell_connection_details_and_errors(self) -> None:
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: shellable
                        spec:
                          exposure:
                            type: Balancer
                            port: 8443
                        """
                    )
                ),
            )
        )
        shell = self.assert_json_stdout(self.run_meshctl("mesh", "shell", "shellable"))
        self.assertEqual(
            {"host": "shellable-external", "port": 8443, "protocol": "https"},
            shell,
        )

        missing = self.assert_json_stdout(self.run_meshctl("mesh", "shell", "missing"))
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing["errors"]},
        )

        self.create_mesh("private")
        no_exposure = self.assert_json_stdout(self.run_meshctl("mesh", "shell", "private"))
        self.assertEqual(
            {
                ("spec.exposure", "invalid", "mesh 'private' has no exposure configured"),
            },
            {(item["field"], item["type"], item["message"]) for item in no_exposure["errors"]},
        )

    def test_exposure_and_management_update_validation_is_atomic(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: connectivity-atomic
                        spec:
                          exposure:
                            type: Gateway
                            hostname: original.example.test
                          management:
                            enabled: false
                        """
                    )
                ),
            )
        )

        invalid = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: connectivity-atomic
                        spec:
                          exposure:
                            type: Balancer
                            hostname: forbidden.example.test
                          management:
                            enabled: true
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.exposure.hostname", "forbidden"),
            {(item["field"], item["type"]) for item in invalid["errors"]},
        )
        self.assertIn(
            ("spec.management.enabled", "immutable"),
            {(item["field"], item["type"]) for item in invalid["errors"]},
        )
        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "connectivity-atomic"))
        self.assertEqual(created["spec"]["exposure"], described["spec"]["exposure"])
        self.assertEqual(created["spec"]["management"], described["spec"]["management"])

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
        self.assertEqual(2, stopped["status"]["desiredInstancesOnResume"])
        self.assertEqual({"ready": 0, "starting": 0, "stopped": 2}, stopped["status"]["instances"])
        self.assertIn("GracefulShutdown", [item["type"] for item in stopped["status"]["conditions"]])

        described_stopped = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "lifecycle"))
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
        self.assertNotIn("warnings", skipped)

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

        omitted = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: omitted-runtime
                        spec:
                        """
                    )
                ),
            )
        )
        self.assertNotIn("runtime", omitted["spec"])

        duplicate_deprecated = self.assert_json_stdout(
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
        self.assertIn(
            ("metadata.name", "duplicate"),
            {(item["field"], item["type"]) for item in duplicate_deprecated["errors"]},
        )
        self.assertNotIn("warnings", duplicate_deprecated)

    def test_migration_strategy_and_version_change_rules(self) -> None:
        for name, strategy in (
            ("fullstop-strategy", "FullStop"),
            ("live-strategy", "LiveMigration"),
            ("rolling-strategy", "RollingPatch"),
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
                              runtime: 3.1.1
                              migration:
                                strategy: {strategy}
                            """
                        )
                    ),
                )
            )
            self.assertEqual(strategy, created["spec"]["migration"]["strategy"])

        invalid_strategy = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-strategy
                        spec:
                          migration:
                            strategy: BlueGreen
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.migration.strategy", "invalid"),
            {(item["field"], item["type"]) for item in invalid_strategy["errors"]},
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
                          name: fullstop-strategy
                        spec:
                          runtime: 3.0.0
                        """
                    )
                ),
            )
        )
        self.assertIn(
            {
                "field": "spec.runtime",
                "message": "version downgrade from '3.1.1' to '3.0.0' is not allowed",
                "type": "invalid",
            },
            downgrade["errors"],
        )

        rolling_source = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-source
                        spec:
                          runtime: 3.0.0
                          migration:
                            strategy: RollingPatch
                        """
                    )
                ),
            )
        )
        self.assertIn("warnings", rolling_source)

        rolling_errors = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-source
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        runtime_errors = [
            item for item in rolling_errors["errors"]
            if item["field"] == "spec.runtime" and item["type"] == "invalid"
        ]
        self.assertEqual(2, len(runtime_errors))

        multi_region_live = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: multi-region-live
                        spec:
                          runtime: 3.1.1
                          regions: [us-east, us-west]
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
            multi_region_live["errors"],
        )

    def test_runtime_assignment_migration_lifecycle_and_migrate_command(self) -> None:
        self.create_mesh("runtime-flow")

        assigned = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: runtime-flow
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        self.assertEqual("3.1.1", assigned["spec"]["runtime"])
        self.assertNotIn("migration", assigned["status"])
        self.assertNotIn("Migration", [item["type"] for item in assigned["status"]["conditions"]])

        started = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: runtime-flow
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                "sourceRuntime": "3.1.1",
                "stage": "Migrate",
                "targetRuntime": "4.0.0",
            },
            started["status"]["migration"],
        )
        self.assertEqual(False, started["status"]["stable"])
        self.assertIn("Migration", [item["type"] for item in started["status"]["conditions"]])

        completed = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "runtime-flow"))
        self.assertNotIn("migration", completed["status"])
        self.assertNotIn("Migration", [item["type"] for item in completed["status"]["conditions"]])
        self.assertEqual(True, completed["status"]["stable"])

        missing = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "missing"))
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing["errors"]},
        )

        no_active = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "runtime-flow"))
        self.assertEqual(
            {
                ("status.migration", "invalid", "no active migration for mesh 'runtime-flow'"),
            },
            {(item["field"], item["type"], item["message"]) for item in no_active["errors"]},
        )

    def test_live_migration_active_updates_and_rollback(self) -> None:
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-flow
                        spec:
                          runtime: 3.1.1
                          migration:
                            strategy: LiveMigration
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
                          name: live-flow
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual("Prepare", started["status"]["migration"]["stage"])

        advanced = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "live-flow"))
        self.assertEqual("Transfer", advanced["status"]["migration"]["stage"])

        unrelated = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-flow
                        spec:
                          network:
                            storage:
                              className: fast
                        """
                    )
                ),
            )
        )
        self.assertEqual("fast", unrelated["spec"]["network"]["storage"]["className"])
        self.assertIn("migration", unrelated["status"])

        runtime_change = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-flow
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
                          name: live-flow
                        spec:
                          migration:
                            strategy: FullStop
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

        rolled_back = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-flow
                        spec:
                          migration:
                            rollback: true
                        """
                    )
                ),
            )
        )
        self.assertNotIn("migration", rolled_back["status"])
        self.assertNotIn("Migration", [item["type"] for item in rolled_back["status"]["conditions"]])
        self.assertNotIn("rollback", rolled_back["spec"]["migration"])

    def test_metadata_tags_telemetry_probe_and_placement_defaults(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: tagged
                          tags:
                            mesh.io/telemetry: "true"
                            mesh.io/targetLabels: region,env
                            mesh.io/probeTargetLabels: probe
                            mesh.io/instanceLabels: node,ordinal
                            owner: platform
                        spec:
                          placement:
                            affinity:
                              scope: zone
                        """
                    )
                ),
            )
        )
        self.assertEqual("platform", created["metadata"]["tags"]["owner"])
        self.assertEqual(
            {"type": "preferred", "scope": "zone"},
            created["spec"]["placement"]["affinity"],
        )
        self.assertEqual(
            {
                "enabled": True,
                "labels": {
                    "targetLabels": ["region", "env"],
                    "probeTargetLabels": ["probe"],
                    "instanceLabels": ["node", "ordinal"],
                },
            },
            created["status"]["telemetryProbe"],
        )

        disabled = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: tagged
                          tags:
                            mesh.io/telemetry: "false"
                            mesh.io/targetLabels: ignored
                        spec:
                        """
                    )
                ),
            )
        )
        self.assertEqual({"enabled": False}, disabled["status"]["telemetryProbe"])

        minimal = self.create_mesh("telemetry-default")
        self.assertEqual({"enabled": True}, minimal["status"]["telemetryProbe"])
        self.assertEqual(
            {"type": "preferred", "scope": "node"},
            minimal["spec"]["placement"]["affinity"],
        )

    def test_placement_validation_errors(self) -> None:
        invalid = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-placement
                        spec:
                          placement:
                            affinity:
                              type: best
                              scope: rack
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                ("spec.placement.affinity.type", "invalid"),
                ("spec.placement.affinity.scope", "invalid"),
            },
            {(item["field"], item["type"]) for item in invalid["errors"]},
        )

        invalid_shape = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-placement-shape
                        spec:
                          placement:
                            affinity: required
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.placement.affinity", "invalid")},
            {(item["field"], item["type"]) for item in invalid_shape["errors"]},
        )

    def test_multi_region_defaults_remotes_conditions_and_stability(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: regioned
                        spec:
                          regions:
                            local:
                              name: us-east
                              expose:
                                type: Internal
                              maxRelayNodes: 2
                            remotes: [{"name": "eu", "url": "https://eu.example.test", "credentialRef": "eu-secret"}, {"name": "ap", "url": "https://ap.example.test", "namespace": "mesh-ap", "clusterRef": "cluster-ap"}]
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                "enabled": True,
                "interval": 10000,
                "timeout": 30000,
            },
            created["spec"]["regions"]["local"]["discovery"]["heartbeat"],
        )
        self.assertEqual(
            ["eu", "ap"],
            [remote["name"] for remote in created["spec"]["regions"]["remotes"]],
        )
        condition_types = [item["type"] for item in created["status"]["conditions"]]
        self.assertEqual(sorted(condition_types), condition_types)
        self.assertIn("DiscoveryRelayReady", condition_types)
        self.assertIn("RegionViewFormed", condition_types)
        self.assertTrue(created["status"]["stable"])

        single = self.create_mesh("single-region")
        single_conditions = [item["type"] for item in single["status"]["conditions"]]
        self.assertNotIn("DiscoveryRelayReady", single_conditions)
        self.assertNotIn("RegionViewFormed", single_conditions)

        duplicate = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: duplicate-remote
                        spec:
                          regions:
                            local:
                              name: us
                              expose:
                                type: Internal
                            remotes: [{"name": "eu", "url": "https://one.example.test"}, {"name": "eu", "url": "https://two.example.test"}]
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.regions.remotes[1].name", "duplicate"),
            {(item["field"], item["type"]) for item in duplicate["errors"]},
        )

    def test_multi_region_validation_discovery_encryption_and_warnings(self) -> None:
        missing_local = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-local
                        spec:
                          regions: {}
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.regions.local", "required"),
            {(item["field"], item["type"]) for item in missing_local["errors"]},
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
                          name: invalid-region
                        spec:
                          regions:
                            local:
                              name: ""
                              expose:
                                type: Tunnel
                              maxRelayNodes:
                              discovery:
                                type: dns
                                heartbeat:
                                  interval: 30000
                                  timeout: 30000
                              encryption:
                                protocol: TLSv1.1
                        """
                    )
                ),
            )
        )
        errors = {(item["field"], item["type"]) for item in invalid["errors"]}
        self.assertIn(("spec.regions.local.name", "required"), errors)
        self.assertIn(("spec.regions.local.expose.type", "invalid"), errors)
        self.assertIn(("spec.regions.local.maxRelayNodes", "invalid"), errors)
        self.assertIn(("spec.regions.local.discovery.type", "invalid"), errors)
        self.assertIn(("spec.regions.local.discovery.heartbeat", "invalid"), errors)
        self.assertIn(("spec.regions.local.encryption.protocol", "invalid"), errors)
        self.assertNotIn("warnings", invalid)

        encrypted = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: encrypted-region
                        spec:
                          regions:
                            local:
                              name: us
                              expose:
                                type: Gateway
                              encryption:
                                transportKeyStore:
                                  secretRef: transport-secret
                                  alias: transport
                                  filename: transport.p12
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            "TLSv1.3",
            encrypted["spec"]["regions"]["local"]["encryption"]["protocol"],
        )
        self.assertEqual(
            [
                {
                    "field": "spec.regions.local.encryption.trustStore",
                    "message": "trustStore is recommended for region encryption",
                }
            ],
            encrypted["warnings"],
        )

        missing_transport = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-transport
                        spec:
                          regions:
                            local:
                              name: us
                              expose:
                                type: Gateway
                              encryption: {}
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.regions.local.encryption.transportKeyStore", "required"),
            {(item["field"], item["type"]) for item in missing_transport["errors"]},
        )

    def test_live_migration_rejected_with_regions_on_create_and_update(self) -> None:
        create_error = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-region-create
                        spec:
                          migration:
                            strategy: LiveMigration
                          regions:
                            local:
                              name: us
                              expose:
                                type: Internal
                        """
                    )
                ),
            )
        )
        expected = {
            "field": "spec.migration.strategy",
            "message": "LiveMigration strategy is not supported with multi-region topology",
            "type": "invalid",
        }
        self.assertIn(expected, create_error["errors"])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-region-update
                        spec:
                          migration:
                            strategy: LiveMigration
                        """
                    )
                ),
            )
        )
        update_error = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-region-update
                        spec:
                          regions:
                            local:
                              name: us
                              expose:
                                type: Internal
                        """
                    )
                ),
            )
        )
        self.assertIn(expected, update_error["errors"])

    def test_config_bundle_ref_update_refresh_is_transient(self) -> None:
        invalid = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-config-ref
                        spec:
                          configBundleRef: 42
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.configBundleRef", "invalid")},
            {(item["field"], item["type"]) for item in invalid["errors"]},
        )

        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: config-ref
                        spec:
                          configBundleRef: bundle-a
                        """
                    )
                ),
            )
        )
        self.assertEqual("bundle-a", created["spec"]["configBundleRef"])
        self.assertNotIn("configRefresh", created["status"])

        changed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: config-ref
                        spec:
                          configBundleRef: bundle-b
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"currentRef": "bundle-b", "pending": True, "previousRef": "bundle-a"},
            changed["status"]["configRefresh"],
        )
        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "config-ref"))
        self.assertNotIn("configRefresh", described["status"])
        self.assertEqual("bundle-b", described["spec"]["configBundleRef"])

        omitted = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: config-ref
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        self.assertEqual("bundle-b", omitted["spec"]["configBundleRef"])
        self.assertNotIn("configRefresh", omitted["status"])

        cleared = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: config-ref
                        spec:
                          configBundleRef:
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"currentRef": None, "pending": True, "previousRef": "bundle-b"},
            cleared["status"]["configRefresh"],
        )
        self.assertNotIn("configBundleRef", cleared["spec"])

    def test_extensions_order_integrity_and_validation(self) -> None:
        created = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: extended
                        spec:
                          extensions: [{"url": "https://example.test/ext.yaml", "integrity": "sha256-abc"}, {"artifact": "oci://registry.example.test/ext:1"}]
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            [
                {"url": "https://example.test/ext.yaml", "integrity": "sha256-abc"},
                {"artifact": "oci://registry.example.test/ext:1"},
            ],
            created["spec"]["extensions"],
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
                          name: invalid-extensions
                        spec:
                          extensions: [{"url": "https://example.test/ext.yaml", "artifact": "oci://registry.example.test/ext:1"}, {"integrity": "sha256-empty"}]
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                (
                    "spec.extensions[0]",
                    "invalid",
                    "exactly one of 'url' or 'artifact' must be set",
                ),
                (
                    "spec.extensions[1]",
                    "invalid",
                    "exactly one of 'url' or 'artifact' must be set",
                ),
            },
            {(item["field"], item["type"], item["message"]) for item in invalid["errors"]},
        )

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

    def test_task_create_list_update_delete_and_run(self) -> None:
        self.create_mesh("alpha")

        task = self.assert_json_stdout(
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
                          inline: |
                            echo ok
                            echo done
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", task["status"]["state"])
        self.assertEqual("echo ok\necho done", task["spec"]["inline"])

        bundle = self.assert_json_stdout(
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
        self.assertEqual("bundle-a", bundle["spec"]["bundleRef"])

        listed = self.assert_json_stdout(self.run_meshctl("task", "list"))
        self.assertEqual(
            [
                {"name": "alpha-task", "meshRef": "alpha", "status": {"state": "Initializing"}},
                {"name": "beta-task", "meshRef": "alpha", "status": {"state": "Initializing"}},
            ],
            listed,
        )
        self.assertEqual(task, self.assert_json_stdout(self.run_meshctl("task", "describe", "beta-task")))

        idempotent = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-task
                        spec:
                          meshRef: alpha
                          inline: |
                            echo ok
                            echo done
                        """
                    )
                ),
            )
        )
        self.assertEqual(task, idempotent)

        immutable = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-task
                        spec:
                          inline: changed
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec", "immutable")},
            {(item["field"], item["type"]) for item in immutable["errors"]},
        )

        duplicate = self.assert_json_stdout(
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
                          bundleRef: other
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("metadata.name", "duplicate"),
            {(item["field"], item["type"]) for item in duplicate["errors"]},
        )

        for yaml_text in (
            """
            metadata:
              name: no-source
            spec:
              meshRef: alpha
            """,
            """
            metadata:
              name: both-sources
            spec:
              meshRef: alpha
              inline: run
              bundleRef: bundle
            """,
            """
            metadata:
              name: empty-source
            spec:
              meshRef: alpha
              inline: ""
            """,
            """
            metadata:
              name: valid-and-empty-source
            spec:
              meshRef: alpha
              inline: run
              bundleRef: ""
            """,
        ):
            payload = self.assert_json_stdout(
                self.run_meshctl("task", "create", "-f", str(self.write_yaml(yaml_text)))
            )
            self.assertIn(
                ("spec", "invalid"),
                {(item["field"], item["type"]) for item in payload["errors"]},
            )
            self.assertIn(
                "exactly one of 'spec.inline' or 'spec.bundleRef' must be set",
                [item["message"] for item in payload["errors"]],
            )

        missing_mesh = self.assert_json_stdout(
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
                          bundleRef: bundle
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.meshRef", "invalid"),
            {(item["field"], item["type"]) for item in missing_mesh["errors"]},
        )

        ran = self.assert_json_stdout(self.run_meshctl("task", "run", "beta-task"))
        self.assertEqual("Succeeded", ran["status"]["state"])
        self.assertNotIn("detail", ran["status"])
        rerun = self.assert_json_stdout(self.run_meshctl("task", "run", "beta-task"))
        self.assertEqual(
            {("status.state", "invalid")},
            {(item["field"], item["type"]) for item in rerun["errors"]},
        )
        self.assertIn("Succeeded", rerun["errors"][0]["message"])

        failer = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: failer
                        spec:
                          meshRef: alpha
                          inline: |
                            echo ok
                            FAIL: boom
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", failer["status"]["state"])
        failed = self.assert_json_stdout(self.run_meshctl("task", "run", "failer"))
        self.assertEqual("Failed", failed["status"]["state"])
        self.assertEqual("command 2 failed: boom", failed["status"]["detail"])

        deleted = self.assert_json_stdout(self.run_meshctl("task", "delete", "alpha-task"))
        self.assertEqual({"name": "alpha-task"}, deleted["metadata"])

    def test_snapshot_create_list_update_delete_and_run(self) -> None:
        self.create_mesh("alpha")

        snapshot = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-snap
                        spec:
                          meshRef: alpha
                          storage:
                            size: 5Gi
                            className: fast
                          scope:
                            stores: ["main"]
                            procedures: ["daily"]
                          resources:
                            cpu:
                              limit: 1000m
                              request: 500m
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", snapshot["status"]["state"])
        self.assertEqual({"limit": "1Gi", "request": "1Gi"}, snapshot["spec"]["resources"]["memory"])
        self.assertEqual("5Gi", snapshot["spec"]["storage"]["size"])
        self.assertEqual({"stores": ["main"], "procedures": ["daily"]}, snapshot["spec"]["scope"])

        alpha_snapshot = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha-snap
                        spec:
                          meshRef: alpha
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", alpha_snapshot["status"]["state"])
        listed = self.assert_json_stdout(self.run_meshctl("snapshot", "list"))
        self.assertEqual(
            [
                {"name": "alpha-snap", "meshRef": "alpha", "status": {"state": "Initializing"}},
                {"name": "beta-snap", "meshRef": "alpha", "status": {"state": "Initializing"}},
            ],
            listed,
        )
        self.assertEqual(snapshot, self.assert_json_stdout(self.run_meshctl("snapshot", "describe", "beta-snap")))

        idempotent = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-snap
                        spec:
                          meshRef: alpha
                          storage:
                            size: 5Gi
                            className: fast
                          scope:
                            stores: ["main"]
                            procedures: ["daily"]
                          resources:
                            memory:
                              limit: 1Gi
                              request: 1Gi
                            cpu:
                              limit: 1000m
                              request: 500m
                        """
                    )
                ),
            )
        )
        self.assertEqual(snapshot, idempotent)

        immutable = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-snap
                        spec:
                          storage:
                            className: slow
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec", "immutable")},
            {(item["field"], item["type"]) for item in immutable["errors"]},
        )

        duplicate = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-snap
                        spec:
                          meshRef: alpha
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("metadata.name", "duplicate"),
            {(item["field"], item["type"]) for item in duplicate["errors"]},
        )

        invalid_quantity = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-snap
                        spec:
                          meshRef: alpha
                          resources:
                            memory:
                              limit: nope
                            cpu:
                              limit: 100m
                              request: 1
                        """
                    )
                ),
            )
        )
        errors = {(item["field"], item["type"]) for item in invalid_quantity["errors"]}
        self.assertIn(("spec.resources.memory.limit", "invalid"), errors)
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
                          name: missing-mesh-snap
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

        uncertain = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: uncertain-snap
                        spec:
                          meshRef: alpha
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", uncertain["status"]["state"])

        ran = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "beta-snap"))
        self.assertEqual("Succeeded", ran["status"]["state"])
        self.assertEqual("snapshot://beta-snap", ran["status"]["storageRef"])
        self.assertNotIn("detail", ran["status"])
        rerun = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "beta-snap"))
        self.assertEqual(
            {("status.state", "invalid")},
            {(item["field"], item["type"]) for item in rerun["errors"]},
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
        unknown = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "uncertain-snap"))
        self.assertEqual("Unknown", unknown["status"]["state"])
        self.assertTrue(unknown["status"]["detail"])
        self.assertNotIn("storageRef", unknown["status"])

        deleted = self.assert_json_stdout(self.run_meshctl("snapshot", "delete", "alpha-snap"))
        self.assertEqual({"name": "alpha-snap"}, deleted["metadata"])

    def test_recovery_create_list_update_delete_run_and_snapshot_conflicts(self) -> None:
        self.create_mesh("alpha")
        self.create_mesh("beta")
        self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha-snap
                        spec:
                          meshRef: alpha
                        """
                    )
                ),
            )
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
                          name: beta-snap
                        spec:
                          meshRef: beta
                        """
                    )
                ),
            )
        )

        recovery = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-recovery
                        spec:
                          meshRef: alpha
                          snapshotRef: alpha-snap
                          scope:
                            definitions: ["schema-a"]
                          resources:
                            cpu:
                              limit: 500m
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", recovery["status"]["state"])
        self.assertEqual({"limit": "1Gi", "request": "1Gi"}, recovery["spec"]["resources"]["memory"])
        self.assertEqual({"definitions": ["schema-a"]}, recovery["spec"]["scope"])

        alpha_recovery = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha-recovery
                        spec:
                          meshRef: alpha
                          snapshotRef: alpha-snap
                        """
                    )
                ),
            )
        )
        self.assertEqual("alpha-snap", alpha_recovery["spec"]["snapshotRef"])

        listed = self.assert_json_stdout(self.run_meshctl("recovery", "list"))
        self.assertEqual(
            [
                {
                    "name": "alpha-recovery",
                    "meshRef": "alpha",
                    "status": {"state": "Initializing"},
                    "snapshotRef": "alpha-snap",
                },
                {
                    "name": "beta-recovery",
                    "meshRef": "alpha",
                    "status": {"state": "Initializing"},
                    "snapshotRef": "alpha-snap",
                },
            ],
            listed,
        )
        self.assertEqual(recovery, self.assert_json_stdout(self.run_meshctl("recovery", "describe", "beta-recovery")))

        idempotent = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-recovery
                        spec:
                          meshRef: alpha
                          snapshotRef: alpha-snap
                          scope:
                            definitions: ["schema-a"]
                          resources:
                            memory:
                              limit: 1Gi
                              request: 1Gi
                            cpu:
                              limit: 500m
                              request: 500m
                        """
                    )
                ),
            )
        )
        self.assertEqual(recovery, idempotent)

        immutable = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-recovery
                        spec:
                          snapshotRef: beta-snap
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec", "immutable")},
            {(item["field"], item["type"]) for item in immutable["errors"]},
        )

        duplicate = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: beta-recovery
                        spec:
                          meshRef: alpha
                          snapshotRef: alpha-snap
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("metadata.name", "duplicate"),
            {(item["field"], item["type"]) for item in duplicate["errors"]},
        )

        missing_refs = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: missing-refs
                        spec:
                          meshRef: absent
                          snapshotRef: absent-snap
                        """
                    )
                ),
            )
        )
        error_pairs = {(item["field"], item["type"]) for item in missing_refs["errors"]}
        self.assertIn(("spec.meshRef", "invalid"), error_pairs)
        self.assertIn(("spec.snapshotRef", "invalid"), error_pairs)

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
                          snapshotRef: beta-snap
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.snapshotRef", "invalid")},
            {(item["field"], item["type"]) for item in mismatch["errors"]},
        )
        self.assertIn(
            "snapshot 'beta-snap' belongs to mesh 'beta', not 'alpha'",
            mismatch["errors"][0]["message"],
        )

        conflict = self.assert_json_stdout(self.run_meshctl("snapshot", "delete", "alpha-snap"))
        self.assertEqual(
            {("metadata.name", "conflict")},
            {(item["field"], item["type"]) for item in conflict["errors"]},
        )
        self.assertIn("alpha-recovery", conflict["errors"][0]["message"])
        self.assertIn("beta-recovery", conflict["errors"][0]["message"])
        self.assertEqual(
            "alpha-snap",
            self.assert_json_stdout(self.run_meshctl("snapshot", "describe", "alpha-snap"))["metadata"]["name"],
        )

        ran = self.assert_json_stdout(self.run_meshctl("recovery", "run", "beta-recovery"))
        self.assertEqual("Succeeded", ran["status"]["state"])
        self.assertNotIn("detail", ran["status"])
        rerun = self.assert_json_stdout(self.run_meshctl("recovery", "run", "beta-recovery"))
        self.assertEqual(
            {("status.state", "invalid")},
            {(item["field"], item["type"]) for item in rerun["errors"]},
        )

        uncertain = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: uncertain-recovery
                        spec:
                          meshRef: alpha
                          snapshotRef: alpha-snap
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", uncertain["status"]["state"])
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
        unknown = self.assert_json_stdout(self.run_meshctl("recovery", "run", "uncertain-recovery"))
        self.assertEqual("Unknown", unknown["status"]["state"])
        self.assertTrue(unknown["status"]["detail"])

        self.assert_json_stdout(self.run_meshctl("recovery", "delete", "alpha-recovery"))
        self.assert_json_stdout(self.run_meshctl("recovery", "delete", "beta-recovery"))
        self.assert_json_stdout(self.run_meshctl("recovery", "delete", "uncertain-recovery"))
        deleted = self.assert_json_stdout(self.run_meshctl("snapshot", "delete", "alpha-snap"))
        self.assertEqual({"name": "alpha-snap"}, deleted["metadata"])

    def test_one_shot_parse_invalid_input_and_not_found_errors(self) -> None:
        invalid_yaml = self.root / "invalid-one-shot.yaml"
        invalid_yaml.write_text("metadata\n  name: nope\n", encoding="utf-8")
        non_mapping = self.root / "one-shot-list.yaml"
        non_mapping.write_text("- nope\n", encoding="utf-8")

        for kind in ("task", "snapshot", "recovery"):
            parse_error = self.assert_json_stdout(
                self.run_meshctl(kind, "create", "-f", str(invalid_yaml))
            )
            self.assertEqual(
                {("", "parse")},
                {(item["field"], item["type"]) for item in parse_error["errors"]},
            )

            invalid_root = self.assert_json_stdout(
                self.run_meshctl(kind, "create", "-f", str(non_mapping))
            )
            self.assertEqual(
                {("", "invalid")},
                {(item["field"], item["type"]) for item in invalid_root["errors"]},
            )

            missing_describe = self.assert_json_stdout(self.run_meshctl(kind, "describe", "missing"))
            missing_delete = self.assert_json_stdout(self.run_meshctl(kind, "delete", "missing"))
            missing_run = self.assert_json_stdout(self.run_meshctl(kind, "run", "missing"))
            missing_update = self.assert_json_stdout(
                self.run_meshctl(
                    kind,
                    "update",
                    "-f",
                    str(
                        self.write_yaml(
                            """
                            metadata:
                              name: missing
                            spec:
                            """
                        )
                    ),
                )
            )
            for payload in (missing_describe, missing_delete, missing_run, missing_update):
                self.assertEqual(
                    {("metadata.name", "not_found")},
                    {(item["field"], item["type"]) for item in payload["errors"]},
                )


if __name__ == "__main__":
    unittest.main()
