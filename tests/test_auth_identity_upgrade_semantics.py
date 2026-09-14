from __future__ import annotations

import copy
import unittest


REQUIRED_IDENTITY = {"tenant_id", "principal_id", "session_generation", "refresh_generation"}


def upgrade_session(record: dict[str, object]) -> dict[str, object]:
    missing = REQUIRED_IDENTITY - record.keys()
    if missing:
        raise ValueError(f"missing required identity fields: {sorted(missing)}")
    upgraded = copy.deepcopy(record)
    upgraded["version"] = 2
    upgraded.setdefault("assurance", {"aal": 1, "generation": 0})
    upgraded.setdefault("metadata", {})
    return upgraded


def project_session_to_v1(record: dict[str, object]) -> dict[str, object]:
    missing = REQUIRED_IDENTITY - record.keys()
    if missing:
        raise ValueError("cannot project record without canonical identity/generation")
    return {
        "version": 1,
        "tenant_id": record["tenant_id"],
        "principal_id": record["principal_id"],
        "session_generation": record["session_generation"],
        "refresh_generation": record["refresh_generation"],
    }


def provider_identity(record: dict[str, object]) -> tuple[object, object]:
    return record["provider_id"], record["provider_subject"]


def upgrade_provider_link(record: dict[str, object]) -> dict[str, object]:
    upgraded = copy.deepcopy(record)
    upgraded["version"] = 2
    upgraded.setdefault("link_generation", 0)
    upgraded.setdefault("provider_metadata", {})
    return upgraded


def project_authorization_to_v1(record: dict[str, object]) -> dict[str, object]:
    root_role = record.get("root_role")
    if root_role not in {"admin", "non_admin"}:
        raise ValueError("unknown root role")
    tenants = sorted(set(record.get("tenant_ids", [])))
    explicit_denies = sorted(set(record.get("explicit_denies", [])))
    app_roles = [role for role in record.get("app_roles", []) if role in {"viewer", "editor", "owner"}]
    return {
        "root_role": root_role,
        "tenant_ids": tenants,
        "app_roles": sorted(set(app_roles)),
        "explicit_denies": explicit_denies,
    }


class AuthIdentityUpgradeSemanticsTests(unittest.TestCase):
    def test_canonical_identity_and_generations_round_trip(self) -> None:
        v1 = {
            "version": 1,
            "tenant_id": "tenant-a",
            "principal_id": "principal-7",
            "session_generation": 12,
            "refresh_generation": 4,
        }
        upgraded = upgrade_session(v1)
        self.assertEqual(project_session_to_v1(upgraded), v1)
        self.assertEqual(upgraded["tenant_id"], v1["tenant_id"])
        self.assertEqual(upgraded["principal_id"], v1["principal_id"])

    def test_missing_identity_or_generation_cannot_be_projected(self) -> None:
        base = {
            "version": 1,
            "tenant_id": "tenant-a",
            "principal_id": "principal-7",
            "session_generation": 12,
            "refresh_generation": 4,
        }
        for key in REQUIRED_IDENTITY:
            broken = dict(base)
            del broken[key]
            with self.assertRaises(ValueError):
                upgrade_session(broken)
            with self.assertRaises(ValueError):
                project_session_to_v1(broken)

    def test_provider_subject_identity_does_not_alias_during_upgrade(self) -> None:
        github = {"version": 1, "provider_id": "github", "provider_subject": "42", "principal_id": "p1"}
        google = {"version": 1, "provider_id": "google", "provider_subject": "42", "principal_id": "p2"}
        self.assertNotEqual(provider_identity(github), provider_identity(google))
        self.assertEqual(provider_identity(upgrade_provider_link(github)), provider_identity(github))
        future = upgrade_provider_link(github)
        future["provider_metadata"] = {"future": {"ignored_by_old_reader": True}}
        self.assertEqual(provider_identity(future), ("github", "42"))

    def test_unlink_generation_survives_upgrade(self) -> None:
        linked = {
            "version": 1,
            "provider_id": "github",
            "provider_subject": "42",
            "principal_id": "p1",
            "link_generation": 9,
        }
        upgraded = upgrade_provider_link(linked)
        self.assertEqual(upgraded["link_generation"], 9)
        stale = dict(upgraded, link_generation=8)
        self.assertLess(stale["link_generation"], upgraded["link_generation"])

    def test_future_app_role_never_becomes_root_admin(self) -> None:
        future = {
            "root_role": "non_admin",
            "tenant_ids": ["tenant-a"],
            "app_roles": ["viewer", "future_superuser"],
            "explicit_denies": ["billing.write"],
        }
        projected = project_authorization_to_v1(future)
        self.assertEqual(projected["root_role"], "non_admin")
        self.assertEqual(projected["app_roles"], ["viewer"])
        self.assertEqual(projected["explicit_denies"], ["billing.write"])

    def test_projection_never_broadens_tenants_or_drops_explicit_deny(self) -> None:
        source = {
            "root_role": "admin",
            "tenant_ids": ["tenant-b", "tenant-a", "tenant-a"],
            "app_roles": ["owner"],
            "explicit_denies": ["secrets.read", "payments.write"],
        }
        projected = project_authorization_to_v1(source)
        self.assertEqual(projected["tenant_ids"], ["tenant-a", "tenant-b"])
        self.assertEqual(set(projected["explicit_denies"]), {"secrets.read", "payments.write"})


if __name__ == "__main__":
    unittest.main()
