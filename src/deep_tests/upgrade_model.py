from __future__ import annotations

import copy
from typing import Any, Iterable


class IncompatibleChange(ValueError):
    pass


def semantic(record: dict[str, Any]) -> dict[str, Any]:
    version = record["version"]
    if version == 1:
        return {"id": record["id"], "name": record["name"], "labels": []}
    if version == 2:
        return {
            "id": record["id"],
            "name": record["display_name"],
            "labels": sorted(record.get("labels", [])),
        }
    if version == 3:
        return {
            "id": record["id"],
            "name": record["display_name"],
            "labels": sorted(record.get("metadata", {}).get("labels", [])),
        }
    raise IncompatibleChange(f"unsupported version: {version}")


def migrate_one(record: dict[str, Any], direction: int) -> dict[str, Any]:
    source = copy.deepcopy(record)
    version = source["version"]
    if direction == 1 and version == 1:
        return {
            "version": 2,
            "id": source["id"],
            "display_name": source["name"],
            "labels": [],
        }
    if direction == 1 and version == 2:
        return {
            "version": 3,
            "id": source["id"],
            "display_name": source["display_name"],
            "metadata": {"labels": sorted(source.get("labels", []))},
            "status": "active",
        }
    if direction == -1 and version == 3:
        return {
            "version": 2,
            "id": source["id"],
            "display_name": source["display_name"],
            "labels": sorted(source.get("metadata", {}).get("labels", [])),
        }
    if direction == -1 and version == 2:
        labels = sorted(source.get("labels", []))
        if labels:
            raise IncompatibleChange("v1 cannot represent labels without explicit loss approval")
        return {"version": 1, "id": source["id"], "name": source["display_name"]}
    raise IncompatibleChange(f"cannot migrate version={version} direction={direction}")


def migrate(record: dict[str, Any], target: int) -> dict[str, Any]:
    if target not in {1, 2, 3}:
        raise IncompatibleChange("target version is unsupported")
    current = copy.deepcopy(record)
    while current["version"] < target:
        current = migrate_one(current, 1)
    while current["version"] > target:
        current = migrate_one(current, -1)
    return current


def negotiate(local: Iterable[int], remote: Iterable[int]) -> int:
    common = sorted(set(local) & set(remote))
    if not common:
        raise IncompatibleChange("no common protocol version")
    return common[-1]


def assert_non_destructive_required_change(old_required: set[str], new_required: set[str]) -> None:
    removed = old_required - new_required
    if removed:
        raise IncompatibleChange(f"required fields removed: {sorted(removed)}")


def read_with_version(record: dict[str, Any], reader_version: int) -> dict[str, Any]:
    # Newer writers may add fields; readers consume only their representable semantic view.
    source_semantic = semantic(record)
    if reader_version == 1:
        return {"id": source_semantic["id"], "name": source_semantic["name"]}
    if reader_version in {2, 3}:
        return source_semantic
    raise IncompatibleChange("reader version is unsupported")


def replay_snapshot(records: Iterable[dict[str, Any]], target_version: int) -> tuple[dict[str, Any], ...]:
    migrated = [migrate(record, target_version) for record in records]
    return tuple(sorted(migrated, key=lambda item: item["id"]))
