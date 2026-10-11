from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from duel_demo import valid_fixture, wait_for_client_inspection


def fixture():
    def team():
        return {"cores": [{}], "resources": {"copper": 0},
                "economy": {"nearbyCopperOreTiles": 25,
                            "duoSite": {"status": "empty"}},
                "units": [{"type": "mono"}, {"type": "poly"}],
                "production": {"factory": {"status": "idle",
                                           "stock": {"silicon": 0, "lead": 0},
                                           "supply": {"routeReady": True,
                                                      "stock": {"silicon": 10, "lead": 10}}}}}
    return {"tick": 0, "paused": True, "gameOver": False,
            "teams": {"sharded": team(), "crux": team()}}


class LauncherFixtureTests(unittest.TestCase):
    def test_client_player_unit_does_not_invalidate_prepared_fixture(self):
        state = fixture()
        self.assertTrue(valid_fixture(state))
        state["teams"]["sharded"]["units"].append({"type": "alpha"})
        self.assertFalse(valid_fixture(state))
        self.assertTrue(valid_fixture(state, initial=False))

    def test_join_check_rejects_unexpected_unit(self):
        state = fixture()
        state["teams"]["sharded"]["units"].append({"type": "flare"})
        self.assertFalse(valid_fixture(state, initial=False))

    def test_join_check_still_rejects_resource_or_build_changes(self):
        state = fixture()
        state["teams"]["crux"]["production"]["factory"]["supply"]["stock"]["lead"] = 0
        self.assertFalse(valid_fixture(state, initial=False))

    def test_closed_input_keeps_server_alive_until_interrupted(self):
        with patch("builtins.input", side_effect=EOFError), patch(
                "duel_demo.time.sleep", side_effect=KeyboardInterrupt) as sleep:
            with self.assertRaises(KeyboardInterrupt):
                wait_for_client_inspection()
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
