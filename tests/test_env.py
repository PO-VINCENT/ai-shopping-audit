from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from catalogready.env import load_local_env


class LocalEnvTests(unittest.TestCase):
    def test_loads_values_without_overriding_existing_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "# comment\n"
                "CATALOGREADY_TEST_NEW=from-file\n"
                'CATALOGREADY_TEST_QUOTED="quoted value"\n'
                "CATALOGREADY_TEST_EXISTING=should-not-win\n"
                "CATALOGREADY_TEST_EMPTY=\n"
                "not a pair\n",
                encoding="utf-8",
            )
            os.environ["CATALOGREADY_TEST_EXISTING"] = "already-set"
            try:
                load_local_env(str(env_file))
                self.assertEqual(os.environ.get("CATALOGREADY_TEST_NEW"), "from-file")
                self.assertEqual(os.environ.get("CATALOGREADY_TEST_QUOTED"), "quoted value")
                self.assertEqual(os.environ.get("CATALOGREADY_TEST_EXISTING"), "already-set")
                self.assertNotIn("CATALOGREADY_TEST_EMPTY", os.environ)
            finally:
                for name in (
                    "CATALOGREADY_TEST_NEW",
                    "CATALOGREADY_TEST_QUOTED",
                    "CATALOGREADY_TEST_EXISTING",
                ):
                    os.environ.pop(name, None)

    def test_missing_file_is_a_no_op(self) -> None:
        load_local_env("/nonexistent/.env")


if __name__ == "__main__":
    unittest.main()
