import random
import unittest

from deep_tests.upgrade_model import IncompatibleChange, assert_non_destructive_required_change, migrate, read_with_version, replay_snapshot, semantic


class TipStressUpgradeTests(unittest.TestCase):
    def test_large_v1_v3_v1_round_trip_preserves_semantics(self) -> None:
        for seed in range(100):
            rng = random.Random(20_000 + seed)
            source = {"version": 1, "id": f"id-{seed}", "name": f"name-{rng.randrange(10_000_000)}"}
            upgraded = migrate(source, 3)
            self.assertEqual(semantic(source), semantic(upgraded))
            self.assertEqual(migrate(upgraded, 1), source)

    def test_snapshot_replay_is_stable_across_many_input_orders(self) -> None:
        records = [{"version": 1, "id": f"id-{i:03d}", "name": f"name-{i}"} for i in range(40)]
        expected = replay_snapshot(records, 3)
        for seed in range(12):
            shuffled = list(records)
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(replay_snapshot(shuffled, 3), expected)

    def test_old_reader_drops_multiple_future_fields(self) -> None:
        record = {"version": 3, "id": "edge-1", "display_name": "current", "metadata": {"labels": ["a"]}, "status": "active", "future_field": {"ignored": True}, "another_future_field": [1, 2, 3]}
        self.assertEqual(read_with_version(record, 1), {"id": "edge-1", "name": "current"})

    def test_multiple_required_field_removal_is_rejected(self) -> None:
        before = {"id", "display_name", "status", "tenant_id"}
        with self.assertRaises(IncompatibleChange):
            assert_non_destructive_required_change(before, {"id", "status"})


if __name__ == "__main__":
    unittest.main()
