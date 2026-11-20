"""Offline checks for package selection and environment-safe builds."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


SOURCE_ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("asksia_package", SOURCE_ROOT / "scripts/validate-package.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="asksia-package-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "plugin"
        self.root.mkdir()
        shutil.copytree(SOURCE_ROOT / "scripts", self.root / "scripts")
        identity = {"name": "asksia", "version": "0.1.0", "description": "Test plugin",
                    "repository": package.REPOSITORY}
        self.write_json("plugin.json", {
            **identity, "$schema": package.PLUGIN_SCHEMA,
            "extensions": {"com.openai": {"interface": {
                "displayName": "AskSia", "composerIcon": "./assets/asksia.png", "logo": "./assets/asksia.png",
            }}},
        })
        self.write_json(".claude-plugin/plugin.json", {
            **identity, "displayName": "AskSia", "icon": "./assets/asksia.png",
        })
        self.write_json(".claude-plugin/marketplace.json", {
            "name": "asksia", "owner": {"name": "AskSia"},
            "plugins": [{"name": "asksia", "source": "./"}],
        })
        self.write_json(".mcp.json", {"mcpServers": {"asksia": {
            "type": "http", "url": package.ENDPOINTS["production"],
        }}})
        self.write_json("mcp.json", {"$schema": package.MCP_SCHEMA, "mcpServers": {"asksia": {
            "type": "streamable-http", "url": package.ENDPOINTS["production"],
        }}})
        for name in package.SKILLS:
            self.write(f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: Test workflow\n---\n\nUse the selected server.\n")
        self.write("README.md", "Test package documentation.\n")
        self.write("LICENSE", "All rights reserved.\n")
        self.write("assets/asksia.png", b"\x89PNG\r\n\x1a\nfixture")

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def write_json(self, relative, value):
        self.write(relative, json.dumps(value) + "\n")

    def build(self, *arguments):
        return subprocess.run(["bash", str(self.root / "scripts/build-chatgpt-zip.sh"), *arguments],
                              capture_output=True, text=True, timeout=15)

    def test_default_preview_archive_is_reproducible_and_keeps_source_production(self):
        source = {name: (self.root / name).read_bytes() for name in package.SOURCE_FILES}
        self.write(".env", "TOKEN=test-only-placeholder\n")
        self.write("private.csv", "unused private data\n")
        self.write(".git/config", "test repository metadata\n")
        first = self.build()
        self.assertEqual(first.returncode, 0, first.stderr)
        path = self.root / "dist/asksia-chatgpt-preview.zip"
        original_archive = path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.namelist(), list(package.ARCHIVE_FILES))
            self.assertEqual(json.loads(archive.read("mcp.json"))["mcpServers"]["asksia"]["url"],
                             package.ENDPOINTS["preview"])
            self.assertEqual(json.loads(archive.read("plugin.json"))["name"], "asksia")
            self.assertNotIn(".mcp.json", archive.namelist())
        second = self.build()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(path.read_bytes(), original_archive)
        self.assertEqual(source, {name: (self.root / name).read_bytes() for name in source})

    def test_production_requires_explicit_environment(self):
        result = self.build("--env", "production")
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(self.root / "dist/asksia-chatgpt-production.zip") as archive:
            self.assertEqual(json.loads(archive.read("mcp.json"))["mcpServers"]["asksia"]["url"],
                             package.ENDPOINTS["production"])

    def test_unknown_environment_or_extra_arguments_do_not_build(self):
        for arguments in (("--env", "staging"), ("--env",), ("--production",), ("--env", "preview", "extra")):
            with self.subTest(arguments=arguments):
                self.assertNotEqual(self.build(*arguments).returncode, 0)
        self.assertFalse((self.root / "dist").exists())

    def test_asset_cannot_read_outside_plugin_through_a_symlink(self):
        secret = Path(self.temporary.name) / "outside.png"
        secret.write_bytes(b"\x89PNG\r\n\x1a\noutside")
        icon = self.root / "assets/asksia.png"
        icon.unlink()
        icon.symlink_to(secret)
        self.assertNotEqual(self.build().returncode, 0)
        self.assertFalse((self.root / "dist").exists())

    def test_credentials_and_nonportable_server_fields_are_not_distributed(self):
        original = json.loads((self.root / "mcp.json").read_text())
        for field, value in (
            ("headers", {"Authorization": "Bearer test-placeholder"}),
            ("extensions", {"com.openai": {"auth": {"type": "oauth"}}}),
        ):
            with self.subTest(field=field):
                config = json.loads(json.dumps(original))
                config["mcpServers"]["asksia"][field] = value
                self.write_json("mcp.json", config)
                self.assertNotEqual(self.build().returncode, 0)
                self.assertFalse((self.root / "dist").exists())

    def test_symlinked_output_cannot_overwrite_another_file(self):
        untouched = Path(self.temporary.name) / "untouched"
        untouched.write_text("keep this")
        (self.root / "dist").mkdir()
        (self.root / "dist/asksia-chatgpt-preview.zip").symlink_to(untouched)
        self.assertNotEqual(self.build().returncode, 0)
        self.assertEqual(untouched.read_text(), "keep this")


if __name__ == "__main__":
    unittest.main()
