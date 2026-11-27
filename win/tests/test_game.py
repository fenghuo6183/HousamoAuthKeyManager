import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import game


class GameModelTest(unittest.TestCase):
    def test_two_games(self):
        self.assertEqual([g.id for g in game.GAMES], ["housamo", "liveahero"])

    def test_housamo_paths(self):
        g = game.game_by_id("housamo")
        self.assertEqual(g.ext_dir,
                         "/sdcard/Android/data/jp.co.lifewonders.housamo/files/Data")
        self.assertEqual(g.ext_key, g.ext_dir + "/AuthKey")
        self.assertTrue(g.prefs.endswith("jp.co.lifewonders.housamo.v2.playerprefs.xml"))

    def test_liveahero_paths(self):
        g = game.game_by_id("liveahero")
        self.assertEqual(
            g.ext_key,
            "/sdcard/Android/data/jp.co.lifewonders.liveahero/files/datas/userKey")

    def test_unknown_game_falls_back(self):
        self.assertEqual(game.game_by_id("nope").id, "housamo")

    def test_candidates_have_lowercase_variant(self):
        g = game.game_by_id("liveahero")
        self.assertIn(g.ext_dir + "/userkey", g.ext_candidates)

    def test_clean_and_validate(self):
        self.assertEqual(game.clean_key(b"\xef\xbb\xbf abc \n"), b"abc")
        self.assertTrue(game.looks_like_key(b"A" * 32))
        self.assertFalse(game.looks_like_key(b"\x00\x01"))


if __name__ == "__main__":
    unittest.main()
