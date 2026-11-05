"""Check the build guards with real, temporary Git repositories (no network)."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_submodules", ROOT / "scripts/submodules.py")
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True,
                                   stderr=subprocess.PIPE).strip()


class SubmoduleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        git(self.root, "init", "-q")
        self.source = self.root / "zmk"
        self.source.mkdir()
        git(self.source, "init", "-q")
        (self.source / "example.c").write_text("first version\n")
        self.commit()
        self.revision = git(self.source, "rev-parse", "HEAD")
        git(self.root, "update-index", "--add", "--cacheinfo", f"160000,{self.revision},zmk")
        self.root_patch = patch.object(sources, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def commit(self, stage=True):
        if stage:
            git(self.source, "add", ".")
        git(self.source, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture")

    def test_build_requires_the_recorded_commit_without_changing_it(self):
        self.assertEqual(sources.verify(("zmk",)), {"zmk": self.revision})
        (self.source / "example.c").write_text("second version\n")
        self.commit()
        new_revision = git(self.source, "rev-parse", "HEAD")
        with self.assertRaisesRegex(RuntimeError, "differs from the staged gitlink"):
            sources.verify(("zmk",))
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), new_revision)
        git(self.root, "update-index", "--cacheinfo", f"160000,{new_revision},zmk")
        self.assertEqual(sources.verify(("zmk",))["zmk"], new_revision)

    def test_missing_nested_dependency_is_rejected(self):
        git(self.source, "config", "--file", ".gitmodules", "submodule.vendor.path", "vendor")
        git(self.source, "config", "--file", ".gitmodules", "submodule.vendor.url",
            "https://example.invalid/vendor.git")
        git(self.source, "update-index", "--add", "--cacheinfo", f"160000,{self.revision},vendor")
        git(self.source, "add", ".gitmodules")
        self.commit(stage=False)
        revision = git(self.source, "rev-parse", "HEAD")
        git(self.root, "update-index", "--cacheinfo", f"160000,{revision},zmk")
        with self.assertRaisesRegex(RuntimeError, "nested submodule is uninitialized"):
            sources.verify(("zmk",))
