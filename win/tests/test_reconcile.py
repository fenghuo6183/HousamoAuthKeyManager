import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import reconcile


class FakeVault:
    def __init__(self, digests):
        self.entries = [{"sha256": d} for d in digests]


class ReconcileTest(unittest.TestCase):
    def test_digest_normalises_whitespace(self):
        self.assertEqual(reconcile.digest_of(b"abc\n"), reconcile.digest_of(b"  abc  "))
        self.assertEqual(len(reconcile.digest_of(b"abc")), 64)

    def test_unknown_key_prompts(self):
        flag, digest = reconcile.should_prompt(FakeVault(["00"]), b"abc", [])
        self.assertTrue(flag)

    def test_known_key_silent(self):
        digest = reconcile.digest_of(b"abc")
        flag, _ = reconcile.should_prompt(FakeVault([digest]), b"abc", [])
        self.assertFalse(flag)

    def test_ignored_key_silent(self):
        digest = reconcile.digest_of(b"abc")
        flag, _ = reconcile.should_prompt(FakeVault([]), b"abc", [digest])
        self.assertFalse(flag)


if __name__ == "__main__":
    unittest.main()
