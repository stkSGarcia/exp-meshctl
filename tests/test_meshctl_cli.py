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

    def condition_types(self, resource):
        return [item["type"] for item in resource["status"]["conditions"]]

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
        self.assertEqual({"enabled": False}, created["spec"]["management"])
        self.assertEqual(
            {"size": "1Gi", "ephemeral": False},
            created["spec"]["network"]["storage"],
        )
        self.assertEqual(1, created["spec"]["network"]["replicationFactor"])
        self.assertEqual(
            {"affinity": {"type": "preferred", "scope": "node"}},
            created["spec"]["placement"],
        )
        self.assertEqual({"enabled": True}, created["status"]["telemetryProbe"])
        self.assertNotIn("runtime", created["spec"])
        self.assertNotIn("cpu", created["spec"]["resources"])
        self.assertNotIn("exposure", created["spec"])
        self.assertNotIn("connectionDetails", created["status"])
        self.assertNotIn("managementConnectionDetails", created["status"])

        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "minimal"))
        self.assertEqual(created["spec"]["access"], described["spec"]["access"])

    def test_exposure_modes_and_connection_details(self) -> None:
        gateway = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: gateway-mesh
                        spec:
                          exposure:
                            type: Gateway
                            hostname: mesh.example.test
                            annotations:
                              route: public
                              owner: platform
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                "type": "Gateway",
                "hostname": "mesh.example.test",
                "annotations": {"route": "public", "owner": "platform"},
            },
            gateway["spec"]["exposure"],
        )
        self.assertEqual(
            {"host": "mesh.example.test", "port": 443, "protocol": "https"},
            gateway["status"]["connectionDetails"],
        )

        gateway_default = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: gateway-default
                        spec:
                          exposure:
                            type: Gateway
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"host": "gateway-default-gateway", "port": 443, "protocol": "https"},
            gateway_default["status"]["connectionDetails"],
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
                          name: direct-mesh
                        spec:
                          exposure:
                            type: DirectPort
                            port: 8443
                            directPort: 30443
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"type": "DirectPort", "directPort": 30443, "port": 8443},
            direct["spec"]["exposure"],
        )
        self.assertEqual(
            {"host": "direct-mesh", "port": 30443, "protocol": "https"},
            direct["status"]["connectionDetails"],
        )

        balancer = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: balancer-mesh
                        spec:
                          exposure:
                            type: Balancer
                            port: 9443
                        """
                    )
                ),
            )
        )
        self.assertEqual({"type": "Balancer", "port": 9443}, balancer["spec"]["exposure"])
        self.assertEqual(
            {"host": "balancer-mesh-external", "port": 9443, "protocol": "https"},
            balancer["status"]["connectionDetails"],
        )

        balancer_default = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: balancer-default
                        spec:
                          exposure:
                            type: Balancer
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"host": "balancer-default-external", "port": 443, "protocol": "https"},
            balancer_default["status"]["connectionDetails"],
        )

        described = self.assert_json_stdout(
            self.run_meshctl("mesh", "describe", "direct-mesh")
        )
        self.assertEqual(direct["status"]["connectionDetails"], described["status"]["connectionDetails"])

    def test_exposure_validation_errors(self) -> None:
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

        empty_type = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: empty-exposure-type
                        spec:
                          exposure:
                            type: ""
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.exposure.type", "required")},
            {(item["field"], item["type"]) for item in empty_type["errors"]},
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
                          name: forbidden-exposure
                        spec:
                          exposure:
                            type: Balancer
                            hostname: mesh.example.test
                            annotations:
                              route: public
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

    def test_management_endpoint_defaults_output_validation_and_immutability(self) -> None:
        managed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: managed-mesh
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
            {"host": "managed-mesh-admin", "port": 9990, "protocol": "https"},
            managed["status"]["managementConnectionDetails"],
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
                          name: invalid-management
                        spec:
                          management:
                            enabled: "yes"
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.management.enabled", "invalid")},
            {(item["field"], item["type"]) for item in invalid["errors"]},
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
                          name: managed-mesh
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

    def test_mesh_shell_connection_lookup(self) -> None:
        exposed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: shell-mesh
                        spec:
                          exposure:
                            type: DirectPort
                            directPort: 31443
                        """
                    )
                ),
            )
        )
        shell = self.assert_json_stdout(self.run_meshctl("mesh", "shell", "shell-mesh"))
        self.assertEqual(exposed["status"]["connectionDetails"], shell)
        self.assertNotIn("metadata", shell)
        self.assertNotIn("status", shell)

        missing = self.assert_json_stdout(self.run_meshctl("mesh", "shell", "missing-mesh"))
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing["errors"]},
        )

        self.create_mesh("unexposed")
        unexposed = self.assert_json_stdout(self.run_meshctl("mesh", "shell", "unexposed"))
        self.assertEqual(
            {("spec.exposure", "invalid", "mesh 'unexposed' has no exposure configured")},
            {(item["field"], item["type"], item["message"]) for item in unexposed["errors"]},
        )

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
            [{"field": "spec.runtime", "message": "runtime version '3.0.0' is deprecated"}],
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
        self.assertEqual(
            {("spec.runtime", "invalid", "runtime version '3.1.0' is skipped and cannot be targeted")},
            {(item["field"], item["type"], item["message"]) for item in skipped["errors"]},
        )
        self.assertNotIn("warnings", skipped)

        unsupported = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: unsupported-runtime
                        spec:
                          runtime: 3.2.0
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.runtime", "invalid")},
            {(item["field"], item["type"]) for item in unsupported["errors"]},
        )

        omitted = self.create_mesh("runtime-omitted")
        self.assertNotIn("runtime", omitted["spec"])
        self.assertNotIn("warnings", omitted)

        deprecated_update = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: runtime-omitted
                        spec:
                          runtime: 3.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual("3.0.0", deprecated_update["spec"]["runtime"])
        self.assertEqual(
            [{"field": "spec.runtime", "message": "runtime version '3.0.0' is deprecated"}],
            deprecated_update["warnings"],
        )

        malformed_update = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: runtime-omitted
                        spec:
                          runtime: 3.1
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.runtime", "invalid")},
            {(item["field"], item["type"]) for item in malformed_update["errors"]},
        )

    def test_migration_strategy_validation_and_start_rules(self) -> None:
        for strategy in ("LiveMigration", "RollingPatch"):
            created = self.assert_json_stdout(
                self.run_meshctl(
                    "mesh",
                    "create",
                    "-f",
                    str(
                        self.write_yaml(
                            f"""
                            metadata:
                              name: strategy-{strategy.lower()}
                            spec:
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
                          name: bad-strategy
                        spec:
                          migration:
                            strategy: Canary
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.migration.strategy", "invalid")},
            {(item["field"], item["type"]) for item in invalid_strategy["errors"]},
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
            ("spec.runtime", "invalid", "version downgrade from '4.0.0' to '3.1.1' is not allowed"),
            {(item["field"], item["type"], item["message"]) for item in downgrade["errors"]},
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
                          name: fullstop-upgrade
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        fullstop = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: fullstop-upgrade
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"sourceRuntime": "3.1.1", "targetRuntime": "4.0.0", "stage": "Migrate"},
            fullstop["status"]["migration"],
        )
        self.assertEqual(False, fullstop["status"]["stable"])
        self.assertIn("Migration", self.condition_types(fullstop))

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-invalid
                        spec:
                          runtime: 4.0.0
                          migration:
                            strategy: RollingPatch
                        """
                    )
                ),
            )
        )
        rolling_errors = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-invalid
                        spec:
                          runtime: 3.0.0
                        """
                    )
                ),
            )
        )
        runtime_messages = [
            item["message"]
            for item in rolling_errors["errors"]
            if item["field"] == "spec.runtime" and item["type"] == "invalid"
        ]
        self.assertIn("RollingPatch requires source and target to share major and minor version", runtime_messages)
        self.assertIn("RollingPatch requires target major version to be at least 4", runtime_messages)
        self.assertIn("version downgrade from '4.0.0' to '3.0.0' is not allowed", runtime_messages)
        self.assertNotIn("warnings", rolling_errors)

        self.assert_json_stdout(
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
                          runtime: 3.1.1
                          migration:
                            strategy: LiveMigration
                        """
                    )
                ),
            )
        )
        live_regions = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-regions
                        spec:
                          runtime: 4.0.0
                          regions: ["east", "west"]
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {(
                "spec.migration.strategy",
                "invalid",
                "LiveMigration strategy is not supported with multi-region topology",
            )},
            {
                (item["field"], item["type"], item["message"])
                for item in live_regions["errors"]
                if item["field"] == "spec.migration.strategy"
            },
        )

    def test_migration_lifecycle_and_migrate_command(self) -> None:
        self.create_mesh("first-assignment")
        assigned = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: first-assignment
                        spec:
                          runtime: 3.1.1
                        """
                    )
                ),
            )
        )
        self.assertEqual("3.1.1", assigned["spec"]["runtime"])
        self.assertNotIn("migration", assigned["status"])
        self.assertNotIn("Migration", self.condition_types(assigned))

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-valid
                        spec:
                          runtime: 4.0.0
                          migration:
                            strategy: RollingPatch
                        """
                    )
                ),
            )
        )
        rolling = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: rolling-valid
                        spec:
                          runtime: 4.0.1
                        """
                    )
                ),
            )
        )
        self.assertEqual("Migrate", rolling["status"]["migration"]["stage"])
        completed_rolling = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "rolling-valid"))
        self.assertNotIn("migration", completed_rolling["status"])
        self.assertNotIn("Migration", self.condition_types(completed_rolling))
        self.assertEqual(True, completed_rolling["status"]["stable"])

        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-stages
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
                          name: live-stages
                        spec:
                          runtime: 4.0.0
                        """
                    )
                ),
            )
        )
        self.assertEqual("Prepare", live_started["status"]["migration"]["stage"])
        live_migrate = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "live-stages"))
        self.assertEqual("Migrate", live_migrate["status"]["migration"]["stage"])
        live_finalize = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "live-stages"))
        self.assertEqual("Finalize", live_finalize["status"]["migration"]["stage"])
        live_complete = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "live-stages"))
        self.assertNotIn("migration", live_complete["status"])

        missing = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "missing"))
        self.assertEqual(
            {("metadata.name", "not_found")},
            {(item["field"], item["type"]) for item in missing["errors"]},
        )

        inactive = self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "first-assignment"))
        self.assertEqual(
            {("status.migration", "invalid", "no active migration for mesh 'first-assignment'")},
            {(item["field"], item["type"], item["message"]) for item in inactive["errors"]},
        )

    def test_active_migration_update_rules_and_one_shot_stability(self) -> None:
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
                          network:
                            storage:
                              className: slow
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
        self.assertEqual(
            {(
                "spec.runtime",
                "invalid",
                "cannot change runtime version while a migration is in progress",
            )},
            {(item["field"], item["type"], item["message"]) for item in runtime_change["errors"]},
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
        self.assertEqual(
            {(
                "spec.migration.strategy",
                "invalid",
                "cannot change migration strategy while a migration is in progress",
            )},
            {(item["field"], item["type"], item["message"]) for item in strategy_change["errors"]},
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
                              className: fast
                        """
                    )
                ),
            )
        )
        self.assertEqual("fast", unrelated["spec"]["network"]["storage"]["className"])
        self.assertEqual(
            {"sourceRuntime": "3.1.1", "targetRuntime": "4.0.0", "stage": "Migrate"},
            unrelated["status"]["migration"],
        )
        self.assertEqual(False, unrelated["status"]["stable"])

        self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: migrating-snapshot
                        spec:
                          meshRef: migrating
                        """
                    )
                ),
            )
        )
        snapshot_run = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "migrating-snapshot"))
        self.assertEqual("Unknown", snapshot_run["status"]["state"])
        self.assertIn("not stable", snapshot_run["status"]["detail"])

        self.assert_json_stdout(self.run_meshctl("mesh", "migrate", "migrating"))
        stable_snapshot = self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: stable-snapshot
                        spec:
                          meshRef: migrating
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", stable_snapshot["status"]["state"])
        self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: stable-recovery
                        spec:
                          meshRef: migrating
                          snapshotRef: stable-snapshot
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
                          name: migrating
                        spec:
                          runtime: 4.0.1
                        """
                    )
                ),
            )
        )
        recovery_run = self.assert_json_stdout(self.run_meshctl("recovery", "run", "stable-recovery"))
        self.assertEqual("Unknown", recovery_run["status"]["state"])
        self.assertIn("not stable", recovery_run["status"]["detail"])

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

    def test_metadata_tags_and_telemetry_probe_projection(self) -> None:
        tagged = self.assert_json_stdout(
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
                            mesh.io/probeTargetLabels: probe-a,probe-b
                            mesh.io/instanceLabels: node,rack
                            owner: platform
                        spec:
                        """
                    )
                ),
            )
        )

        self.assertEqual("platform", tagged["metadata"]["tags"]["owner"])
        self.assertEqual(
            {
                "enabled": True,
                "labels": {
                    "targetLabels": ["region", "env"],
                    "probeTargetLabels": ["probe-a", "probe-b"],
                    "instanceLabels": ["node", "rack"],
                },
            },
            tagged["status"]["telemetryProbe"],
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
                          name: telemetry-off
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

    def test_placement_defaults_values_and_validation(self) -> None:
        placed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: placed
                        spec:
                          placement:
                            affinity:
                              type: required
                              scope: zone
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {"affinity": {"type": "required", "scope": "zone"}},
            placed["spec"]["placement"],
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
                          name: invalid-placement
                        spec:
                          placement:
                            affinity:
                              type: hard
                              scope: rack
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                ("spec.placement.affinity.scope", "invalid"),
                ("spec.placement.affinity.type", "invalid"),
            },
            {(item["field"], item["type"]) for item in invalid["errors"]},
        )

        non_object = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: non-object-placement
                        spec:
                          placement: fast
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.placement", "invalid")},
            {(item["field"], item["type"]) for item in non_object["errors"]},
        )

    def test_multi_region_output_defaults_warnings_and_remote_order(self) -> None:
        multi = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: global
                        spec:
                          regions:
                            local:
                              name: east
                              expose:
                                type: Gateway
                              maxRelayNodes: 3
                              encryption:
                                transportKeyStore:
                                  secretRef: transport-secret
                                  alias: transport
                                  filename: transport.p12
                            remotes:
                              - name: west
                                url: https://west.example.test
                                credentialRef: west-secret
                              - name: eu
                                url: https://eu.example.test
                                namespace: eu-mesh
                                clusterRef: eu-cluster
                        """
                    )
                ),
            )
        )

        local = multi["spec"]["regions"]["local"]
        self.assertEqual("east", local["name"])
        self.assertEqual({"type": "Gateway"}, local["expose"])
        self.assertEqual(3, local["maxRelayNodes"])
        self.assertEqual("TLSv1.3", local["encryption"]["protocol"])
        self.assertEqual(
            {
                "type": "relay",
                "heartbeat": {"enabled": True, "interval": 10000, "timeout": 30000},
            },
            local["discovery"],
        )
        self.assertEqual(["west", "eu"], [item["name"] for item in multi["spec"]["regions"]["remotes"]])
        self.assertEqual(
            [
                "DiscoveryRelayReady",
                "Healthy",
                "PrechecksPassed",
                "RegionViewFormed",
            ],
            self.condition_types(multi),
        )
        self.assertEqual(True, multi["status"]["stable"])
        self.assertEqual(
            [{
                "field": "spec.regions.local.encryption.trustStore",
                "message": "trustStore is recommended for inter-region encryption",
            }],
            multi["warnings"],
        )

    def test_multi_region_validation_errors(self) -> None:
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
                          name: invalid-regions
                        spec:
                          regions:
                            local:
                              name: ""
                              expose:
                                type: Gateway
                              maxRelayNodes: 0
                              encryption:
                                protocol: SSLv3
                                relayKeyStore:
                                  secretRef: relay-secret
                              discovery:
                                type: direct
                                heartbeat:
                                  interval: 30000
                                  timeout: 30000
                            remotes:
                              - name: west
                                url: https://west.example.test
                              - name: west
                                url: https://west-2.example.test
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                ("spec.regions.local.discovery.heartbeat", "invalid"),
                ("spec.regions.local.discovery.type", "invalid"),
                ("spec.regions.local.encryption.protocol", "invalid"),
                ("spec.regions.local.encryption.relayKeyStore.alias", "required"),
                ("spec.regions.local.encryption.relayKeyStore.filename", "required"),
                ("spec.regions.local.encryption.transportKeyStore", "required"),
                ("spec.regions.local.maxRelayNodes", "invalid"),
                ("spec.regions.local.name", "required"),
                ("spec.regions.remotes[1].name", "duplicate"),
            },
            {(item["field"], item["type"]) for item in invalid["errors"]},
        )
        self.assertNotIn("warnings", invalid)

    def test_live_migration_is_rejected_with_regions_on_create_and_update(self) -> None:
        create_rejected = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-create-region
                        spec:
                          migration:
                            strategy: LiveMigration
                          regions:
                            local:
                              name: east
                              expose:
                                type: Internal
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {(
                "spec.migration.strategy",
                "invalid",
                "LiveMigration strategy is not supported with multi-region topology",
            )},
            {(item["field"], item["type"], item["message"]) for item in create_rejected["errors"]},
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
                          name: live-update-region
                        spec:
                          migration:
                            strategy: LiveMigration
                        """
                    )
                ),
            )
        )
        update_rejected = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: live-update-region
                        spec:
                          regions:
                            local:
                              name: east
                              expose:
                                type: Internal
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {(
                "spec.migration.strategy",
                "invalid",
                "LiveMigration strategy is not supported with multi-region topology",
            )},
            {(item["field"], item["type"], item["message"]) for item in update_rejected["errors"]},
        )

    def test_config_bundle_ref_create_update_and_transient_refresh(self) -> None:
        invalid = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: invalid-config-bundle
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
                          name: config-bundled
                        spec:
                          configBundleRef: bundle-a
                        """
                    )
                ),
            )
        )
        self.assertEqual("bundle-a", created["spec"]["configBundleRef"])

        preserved = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: config-bundled
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
        )
        self.assertEqual("bundle-a", preserved["spec"]["configBundleRef"])
        self.assertNotIn("configRefresh", preserved["status"])

        changed = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: config-bundled
                        spec:
                          configBundleRef: bundle-b
                        """
                    )
                ),
            )
        )
        self.assertEqual("bundle-b", changed["spec"]["configBundleRef"])
        self.assertEqual(
            {"currentRef": "bundle-b", "pending": True, "previousRef": "bundle-a"},
            changed["status"]["configRefresh"],
        )
        described = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "config-bundled"))
        self.assertNotIn("configRefresh", described["status"])

        cleared = self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: config-bundled
                        spec:
                          configBundleRef:
                        """
                    )
                ),
            )
        )
        self.assertNotIn("configBundleRef", cleared["spec"])
        self.assertEqual(
            {"currentRef": None, "pending": True, "previousRef": "bundle-b"},
            cleared["status"]["configRefresh"],
        )

    def test_extensions_order_integrity_and_source_validation(self) -> None:
        extended = self.assert_json_stdout(
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
                          extensions:
                            - url: https://example.test/ext.tgz
                              integrity: sha256-abc
                            - artifact: registry/ext:v1
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            [
                {"url": "https://example.test/ext.tgz", "integrity": "sha256-abc"},
                {"artifact": "registry/ext:v1"},
            ],
            extended["spec"]["extensions"],
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
                          extensions:
                            - url: https://example.test/ext.tgz
                              artifact: registry/ext:v1
                            - integrity: sha256-def
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {
                ("spec.extensions[0]", "invalid", "exactly one of 'url' or 'artifact' must be set"),
                ("spec.extensions[1]", "invalid", "exactly one of 'url' or 'artifact' must be set"),
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

    def test_task_lifecycle_and_validation(self) -> None:
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
                          name: alpha-task
                        spec:
                          meshRef: alpha
                          inline: "prepare\\nverify"
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", task["status"]["state"])
        self.assertEqual("prepare\nverify", task["spec"]["inline"])

        listed = self.assert_json_stdout(self.run_meshctl("task", "list"))
        self.assertEqual([{"name": "alpha-task", "status": {"state": "Initializing"}}], listed)
        described = self.assert_json_stdout(self.run_meshctl("task", "describe", "alpha-task"))
        self.assertEqual(task, described)

        unchanged = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: alpha-task
                        """
                    )
                ),
            )
        )
        self.assertEqual(task, unchanged)

        run = self.assert_json_stdout(self.run_meshctl("task", "run", "alpha-task"))
        self.assertEqual("Succeeded", run["status"]["state"])
        self.assertNotIn("detail", run["status"])

        rerun = self.assert_json_stdout(self.run_meshctl("task", "run", "alpha-task"))
        self.assertEqual(
            {("status.state", "invalid")},
            {(item["field"], item["type"]) for item in rerun["errors"]},
        )
        self.assertIn("Succeeded", rerun["errors"][0]["message"])

        failing = self.assert_json_stdout(
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
                          inline: "ok\\nFAIL: boom\\nlater"
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", failing["status"]["state"])
        failed = self.assert_json_stdout(self.run_meshctl("task", "run", "failing-task"))
        self.assertEqual(
            {"state": "Failed", "detail": "command 2 failed: boom"},
            failed["status"],
        )

        invalid_source = self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: bad-task
                        spec:
                          meshRef: alpha
                          inline:
                          bundleRef: bundle
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec", "invalid")},
            {(item["field"], item["type"]) for item in invalid_source["errors"]},
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
                          meshRef: missing
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

        deleted = self.assert_json_stdout(self.run_meshctl("task", "delete", "alpha-task"))
        self.assertEqual({"name": "alpha-task"}, deleted["metadata"])

    def test_snapshot_lifecycle_validation_and_dependency_conflict(self) -> None:
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
                          name: snap-alpha
                        spec:
                          meshRef: alpha
                          storage:
                            size: 2Gi
                            className: fast
                          scope:
                            stores: ["main"]
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
        self.assertEqual({"size": "2Gi", "className": "fast"}, snapshot["spec"]["storage"])

        listed = self.assert_json_stdout(self.run_meshctl("snapshot", "list"))
        self.assertEqual([{"name": "snap-alpha", "status": {"state": "Initializing"}}], listed)
        described = self.assert_json_stdout(self.run_meshctl("snapshot", "describe", "snap-alpha"))
        self.assertEqual(snapshot, described)

        run = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "snap-alpha"))
        self.assertEqual("Succeeded", run["status"]["state"])
        self.assertEqual("snapshot://snap-alpha", run["status"]["storageRef"])
        self.assertNotIn("detail", run["status"])

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
                            className: slow
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec", "immutable"),
            {(item["field"], item["type"]) for item in immutable["errors"]},
        )

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
                        """
                    )
                ),
            )
        )
        self.assertIn(
            ("spec.resources.memory.request", "invalid"),
            {(item["field"], item["type"]) for item in invalid_resources["errors"]},
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
                          name: snap-for-recovery
                        spec:
                          meshRef: alpha
                        """
                    )
                ),
            )
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
                          name: dependent-recovery
                        spec:
                          meshRef: alpha
                          snapshotRef: snap-for-recovery
                        """
                    )
                ),
            )
        )
        blocked = self.assert_json_stdout(self.run_meshctl("snapshot", "delete", "snap-for-recovery"))
        self.assertEqual(
            {("metadata.name", "conflict")},
            {(item["field"], item["type"]) for item in blocked["errors"]},
        )
        self.assertIn("dependent-recovery", blocked["errors"][0]["message"])
        self.assert_json_stdout(self.run_meshctl("recovery", "delete", "dependent-recovery"))
        deleted = self.assert_json_stdout(self.run_meshctl("snapshot", "delete", "snap-for-recovery"))
        self.assertEqual({"name": "snap-for-recovery"}, deleted["metadata"])

        self.create_mesh("unstable")
        self.assert_json_stdout(
            self.run_meshctl(
                "mesh",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: unstable
                        spec:
                          instances: 2
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
                          name: unstable-snapshot
                        spec:
                          meshRef: unstable
                        """
                    )
                ),
            )
        )
        unknown = self.assert_json_stdout(self.run_meshctl("snapshot", "run", "unstable-snapshot"))
        self.assertEqual("Unknown", unknown["status"]["state"])
        self.assertTrue(unknown["status"]["detail"])
        self.assertNotIn("storageRef", unknown["status"])

    def test_recovery_lifecycle_and_validation(self) -> None:
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
                          name: alpha-snapshot
                        spec:
                          meshRef: alpha
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
                          name: restore-alpha
                        spec:
                          meshRef: alpha
                          snapshotRef: alpha-snapshot
                          scope:
                            definitions: ["orders"]
                          resources:
                            cpu:
                              limit: 1
                              request: 500m
                        """
                    )
                ),
            )
        )
        self.assertEqual("Initializing", recovery["status"]["state"])
        self.assertEqual({"limit": "1Gi", "request": "1Gi"}, recovery["spec"]["resources"]["memory"])
        listed = self.assert_json_stdout(self.run_meshctl("recovery", "list"))
        self.assertEqual([{"name": "restore-alpha", "status": {"state": "Initializing"}}], listed)
        described = self.assert_json_stdout(self.run_meshctl("recovery", "describe", "restore-alpha"))
        self.assertEqual(recovery, described)

        run = self.assert_json_stdout(self.run_meshctl("recovery", "run", "restore-alpha"))
        self.assertEqual({"state": "Succeeded"}, run["status"])

        unchanged = self.assert_json_stdout(
            self.run_meshctl(
                "recovery",
                "update",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: restore-alpha
                        """
                    )
                ),
            )
        )
        self.assertEqual(run, unchanged)

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
                          snapshotRef: missing
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
                          name: wrong-mesh
                        spec:
                          meshRef: beta
                          snapshotRef: alpha-snapshot
                        """
                    )
                ),
            )
        )
        self.assertEqual(
            {("spec.snapshotRef", "invalid")},
            {(item["field"], item["type"]) for item in mismatch["errors"]},
        )
        self.assertIn("belongs to mesh 'alpha', not 'beta'", mismatch["errors"][0]["message"])

        self.create_mesh("unstable-recovery")
        self.assert_json_stdout(
            self.run_meshctl(
                "snapshot",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: unstable-recovery-snapshot
                        spec:
                          meshRef: unstable-recovery
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
                          name: unstable-recovery
                        spec:
                          instances: 2
                        """
                    )
                ),
            )
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
                          name: unknown-recovery
                        spec:
                          meshRef: unstable-recovery
                          snapshotRef: unstable-recovery-snapshot
                        """
                    )
                ),
            )
        )
        unknown = self.assert_json_stdout(self.run_meshctl("recovery", "run", "unknown-recovery"))
        self.assertEqual("Unknown", unknown["status"]["state"])
        self.assertTrue(unknown["status"]["detail"])

        deleted = self.assert_json_stdout(self.run_meshctl("recovery", "delete", "restore-alpha"))
        self.assertEqual({"name": "restore-alpha"}, deleted["metadata"])

    def test_mesh_and_vault_work_with_extended_store_shape(self) -> None:
        self.create_mesh("store-parent")
        self.assert_json_stdout(
            self.run_meshctl(
                "task",
                "create",
                "-f",
                str(
                    self.write_yaml(
                        """
                        metadata:
                          name: store-task
                        spec:
                          meshRef: store-parent
                          bundleRef: bundle
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
                          name: store-vault
                        spec:
                          meshRef: store-parent
                        """
                    )
                ),
            )
        )

        store = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertEqual({"meshes", "vaults", "tasks", "snapshots", "recoveries"}, set(store))
        self.assertIn("store-task", store["tasks"])
        mesh = self.assert_json_stdout(self.run_meshctl("mesh", "describe", "store-parent"))
        self.assertEqual("store-parent", mesh["metadata"]["name"])
        vault = self.assert_json_stdout(self.run_meshctl("vault", "describe", "store-vault"))
        self.assertEqual("Ready", vault["status"]["state"])


if __name__ == "__main__":
    unittest.main()
