"""可在 PyCharm 右键运行，也可 python -m unittest -v。"""

import unittest
from lab.experiments import run_suite
from lab.driver import Driver
from deepagents.backends import StateBackend


class BackendLabTests(unittest.TestCase):
    def test_full_comparison(self):
        report, result = run_suite(verbose=False)
        self.assertGreaterEqual(result["total"], 85)
        for row in result["checks"]:
            with self.subTest(group=row["group"], name=row["name"]):
                self.assertTrue(row["passed"], row["observed"])
        self.assertTrue((report.root / "REPORT.md").is_file())
        self.assertTrue((report.root / "results.json").is_file())

    def test_driver_rejects_shell_and_delegation(self):
        driver = Driver(StateBackend())
        for tool in ("execute", "task", "unknown"):
            with self.subTest(tool=tool), self.assertRaises(ValueError):
                driver.call(tool)


if __name__ == "__main__":
    unittest.main(verbosity=2)
