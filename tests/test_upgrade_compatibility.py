import random
import unittest

from deep_tests.upgrade_model import (
    IncompatibleChange,
    assert_non_destructive_required_change,
    migrate,
    negotiate,
    read_with_version,
    replay_snapshot,
    semantic,
)


class UpgradeCompatibilityTests(unittest.TestCase):
    def test_lossless_v1_v3_v1_round_trip_across_many_records(self) -> None:
        for seed in range(50):
            randomizer = random.Random(seed)
            source = {
                "version": 1,
                "id": f"id-{seed}",
                "name": f"name-{randomizer.randrange(1_000_000)}",
            }
            upgraded = migrate(source, 3)
            downgraded = migrate(upgraded, 1)
            self.assertEqual(source, downgraded)
            self.assertEqual(semantic(source), semantic(upgraded))

    def test_lossy_downgrade_requires_explicit_handling(self) -> None:
        v2 = {"version": 2, "id": "1", "display_name": "one", "labels": ["protected"]}
        with self.assertRaises(IncompatibleChange):
            migrate(v2, 1)

    def test_new_writer_remains_readable_by_old_reader(self) -> None:
        v3 = {
            "version": 3,
            "id": "1",
            "display_name": "one",
            "metadata": {"labels": ["a", "b"]},
            "status": "active",
            "future_field": {"ignored": True},
        }
        self.assertEqual(read_with_version(v3, 1), {"id": "1", "name": "one"})

    def test_version_negotiation_chooses_highest_common_and_fails_closed(self) -> None:
        self.assertEqual(negotiate([1, 2, 3], [2, 3, 4]), 3)
        with self.assertRaises(IncompatibleChange):
            negotiate([1], [2, 3])

    def test_required_field_removal_is_rejected(self) -> None:
        assert_non_destructive_required_change({"id", "name"}, {"id", "name", "status"})
        with self.assertRaises(IncompatibleChange):
            assert_non_destructive_required_change({"id", "name"}, {"id"})

    def test_snapshot_replay_is_deterministic(self) -> None:
        records = [
            {"version": 1, "id": "b", "name": "two"},
            {"version": 1, "id": "a", "name": "one"},
        ]
        first = replay_snapshot(records, 3)
        second = replay_snapshot(reversed(records), 3)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
