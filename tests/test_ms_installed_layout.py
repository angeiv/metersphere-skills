import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_SOURCE_DIR = REPO_ROOT / "skills"
SYSTEM_PYTHON = Path("/usr/bin/python3")


class InstalledLayoutEntrypointTests(unittest.TestCase):
    def interpreter(self) -> str:
        if SYSTEM_PYTHON.exists():
            return str(SYSTEM_PYTHON)
        return sys.executable

    def copy_skill_tree(self) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="metersphere-skill-"))
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        skill_dir = temp_dir / "metersphere"
        shutil.copytree(SKILL_SOURCE_DIR, skill_dir, ignore=shutil.ignore_patterns("__pycache__"))
        return skill_dir

    def test_ms_help_runs_from_installed_layout(self):
        skill_dir = self.copy_skill_tree()
        result = subprocess.run(
            [self.interpreter(), str(skill_dir / "scripts" / "ms.py"), "--help"],
            cwd=skill_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("workspace", result.stdout)

    def test_ms_generate_runs_from_installed_layout(self):
        skill_dir = self.copy_skill_tree()
        result = subprocess.run(
            [self.interpreter(), str(skill_dir / "scripts" / "ms_generate.py"), "functional-cases", "p1", "node1", "用户登录"],
            cwd=skill_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data)
        self.assertEqual(data[0]["nodeId"], "node1")

    def test_case_report_entrypoint_imports_resolve_from_installed_layout(self):
        skill_dir = self.copy_skill_tree()
        result = subprocess.run(
            [self.interpreter(), str(skill_dir / "scripts" / "ms.py"), "case-report"],
            cwd=skill_dir,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("用法: ms case-report <projectId> <caseId>", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)


if __name__ == "__main__":
    unittest.main()
