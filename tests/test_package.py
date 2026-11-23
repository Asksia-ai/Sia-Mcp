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
        identity = {"name": "asksia", "version": "0.2.1", "description": "Test plugin",
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
        install_path = self.root / "dist/asksia-chatgpt-preview-install.zip"
        original_install_archive = install_path.read_bytes()
        claude_path = self.root / "dist/asksia-claude-preview.zip"
        original_claude_archive = claude_path.read_bytes()
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.namelist(), list(package.ARCHIVE_FILES))
            self.assertEqual(json.loads(archive.read("mcp.json"))["mcpServers"]["asksia"]["url"],
                             package.ENDPOINTS["preview"])
            self.assertEqual(json.loads(archive.read("plugin.json"))["name"], "asksia")
            self.assertNotIn(".mcp.json", archive.namelist())
        second = self.build()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(path.read_bytes(), original_archive)
        self.assertEqual(install_path.read_bytes(), original_install_archive)
        self.assertEqual(claude_path.read_bytes(), original_claude_archive)
        self.assertEqual(source, {name: (self.root / name).read_bytes() for name in source})

    def assert_install_bundle(self, environment):
        folder = f"asksia-chatgpt-{environment}-install"
        archive_path = self.root / "dist" / f"{folder}.zip"
        portable_path = self.root / "dist" / f"asksia-chatgpt-{environment}.zip"
        catalog_relative = ".agents/plugins/marketplace.json"
        expected_files = {
            f"{folder}/{catalog_relative}",
            f"{folder}/INSTALL.txt",
            *(f"{folder}/plugins/asksia/{name}" for name in package.ARCHIVE_FILES),
        }
        with zipfile.ZipFile(archive_path) as archive, zipfile.ZipFile(portable_path) as portable:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            # No source tree, local settings, or unrelated files belong here.
            self.assertEqual(set(names), expected_files)
            self.assertIsNone(archive.testzip())
            instructions = archive.read(f"{folder}/INSTALL.txt").decode("utf-8")
            self.assertIn(package.ENDPOINTS[environment], instructions)
            self.assertIn("codex plugin marketplace add .", instructions)
            for name in package.ARCHIVE_FILES:
                self.assertEqual(archive.read(f"{folder}/plugins/asksia/{name}"),
                                 portable.read(name))
            destination = Path(self.temporary.name) / f"Mac Downloads {environment}"
            archive.extractall(destination)

        marketplace_root = destination / folder
        catalog = json.loads((marketplace_root / catalog_relative).read_text())
        self.assertEqual(catalog["name"], f"asksia-{environment}")
        self.assertEqual(catalog["interface"]["displayName"],
                         "AskSia Preview" if environment == "preview" else "AskSia")
        self.assertEqual(len(catalog["plugins"]), 1)
        plugin = catalog["plugins"][0]
        self.assertEqual(plugin["name"], "asksia")
        self.assertEqual(plugin["source"], {"source": "local", "path": "./plugins/asksia"})
        self.assertEqual(plugin["policy"], {
            "installation": "AVAILABLE", "authentication": "ON_INSTALL",
        })
        self.assertEqual(plugin["category"], "Education & Research")
        plugin_root = (marketplace_root / plugin["source"]["path"]).resolve()
        self.assertEqual(plugin_root, (marketplace_root / "plugins/asksia").resolve())
        self.assertEqual(json.loads((plugin_root / "plugin.json").read_text())["name"], "asksia")
        config = json.loads((plugin_root / "mcp.json").read_text())
        self.assertEqual(config["mcpServers"]["asksia"]["url"], package.ENDPOINTS[environment])
        self.assertEqual(sorted(p.parent.name for p in (plugin_root / "skills").glob("*/SKILL.md")),
                         sorted(package.SKILLS))

    def assert_claude_bundle(self, environment):
        folder = f"asksia-claude-{environment}"
        shared_files = tuple(name for name in package.ARCHIVE_FILES
                             if name not in {"plugin.json", "mcp.json"})
        expected_files = {
            f"{folder}/.claude-plugin/plugin.json",
            f"{folder}/.claude-plugin/marketplace.json",
            f"{folder}/.mcp.json",
            f"{folder}/INSTALL.txt",
            *(f"{folder}/{name}" for name in shared_files),
        }
        archive_path = self.root / "dist" / f"{folder}.zip"
        portable_path = self.root / "dist" / f"asksia-chatgpt-{environment}.zip"
        with zipfile.ZipFile(archive_path) as archive, zipfile.ZipFile(portable_path) as portable:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(set(names), expected_files)
            self.assertIsNone(archive.testzip())
            instructions = archive.read(f"{folder}/INSTALL.txt").decode("utf-8")
            self.assertIn(package.ENDPOINTS[environment], instructions)
            self.assertIn("plugin marketplace add", instructions)
            self.assertIn(f"asksia@asksia-{environment}", instructions)
            for name in shared_files:
                self.assertEqual(archive.read(f"{folder}/{name}"), portable.read(name))
            destination = Path(self.temporary.name) / f"Claude Downloads {environment}"
            archive.extractall(destination)

        marketplace_root = destination / folder
        catalog = json.loads((marketplace_root / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(catalog["name"], f"asksia-{environment}")
        self.assertEqual(catalog["owner"]["name"], "AskSia")
        self.assertEqual(len(catalog["plugins"]), 1)
        plugin = catalog["plugins"][0]
        self.assertEqual(plugin["name"], "asksia")
        self.assertEqual(plugin["source"], "./")
        plugin_root = (marketplace_root / plugin["source"]).resolve()
        self.assertEqual(plugin_root, marketplace_root.resolve())
        manifest = json.loads((plugin_root / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(manifest,
                         json.loads((self.root / ".claude-plugin/plugin.json").read_text()))
        self.assertTrue((plugin_root / manifest["icon"]).is_file())
        config = json.loads((plugin_root / ".mcp.json").read_text())
        self.assertEqual(config, {"mcpServers": {"asksia": {
            "type": "http", "url": package.ENDPOINTS[environment],
        }}})
        self.assertEqual(sorted(p.parent.name for p in (plugin_root / "skills").glob("*/SKILL.md")),
                         sorted(package.SKILLS))

    def test_preview_install_bundle_resolves_after_unpacking_without_copying_local_settings(self):
        self.write(".env", "TOKEN=test-only-placeholder\n")
        self.write("private.csv", "unused private data\n")
        self.write(".git/config", "test repository metadata\n")
        self.write_json(".agents/plugins/marketplace.json", {"name": "unrelated-local-marketplace"})
        self.write(".codex/config.toml", "model = 'test-only-placeholder'\n")
        tracked_inputs = (*package.SOURCE_FILES, ".agents/plugins/marketplace.json", ".codex/config.toml")
        original = {name: (self.root / name).read_bytes() for name in tracked_inputs}
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_install_bundle("preview")
        self.assert_claude_bundle("preview")
        self.assertEqual(original, {name: (self.root / name).read_bytes() for name in tracked_inputs})

    def test_production_requires_explicit_environment(self):
        result = self.build("--env", "production")
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(self.root / "dist/asksia-chatgpt-production.zip") as archive:
            self.assertEqual(json.loads(archive.read("mcp.json"))["mcpServers"]["asksia"]["url"],
                             package.ENDPOINTS["production"])
        self.assert_install_bundle("production")
        self.assert_claude_bundle("production")
        self.assertFalse((self.root / "dist/asksia-chatgpt-preview-install.zip").exists())
        self.assertFalse((self.root / "dist/asksia-claude-preview.zip").exists())

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
        self.assertFalse((self.root / "dist/asksia-chatgpt-preview-install.zip").exists())
        self.assertFalse((self.root / "dist/asksia-claude-preview.zip").exists())

    def test_symlinked_install_output_does_not_modify_the_existing_portable_archive(self):
        untouched = Path(self.temporary.name) / "untouched-install-target"
        untouched.write_text("keep this")
        (self.root / "dist").mkdir()
        portable = self.root / "dist/asksia-chatgpt-preview.zip"
        portable.write_bytes(b"previous portable artifact")
        (self.root / "dist/asksia-chatgpt-preview-install.zip").symlink_to(untouched)
        self.assertNotEqual(self.build().returncode, 0)
        self.assertEqual(untouched.read_text(), "keep this")
        self.assertEqual(portable.read_bytes(), b"previous portable artifact")
        self.assertFalse((self.root / "dist/asksia-claude-preview.zip").exists())

    def test_symlinked_claude_output_does_not_modify_either_existing_chatgpt_archive(self):
        untouched = Path(self.temporary.name) / "untouched-claude-target"
        untouched.write_text("keep this")
        (self.root / "dist").mkdir()
        previous = {
            "asksia-chatgpt-preview.zip": b"previous portable artifact",
            "asksia-chatgpt-preview-install.zip": b"previous ChatGPT install artifact",
        }
        for filename, data in previous.items():
            (self.root / "dist" / filename).write_bytes(data)
        (self.root / "dist/asksia-claude-preview.zip").symlink_to(untouched)
        self.assertNotEqual(self.build().returncode, 0)
        self.assertEqual(untouched.read_text(), "keep this")
        for filename, data in previous.items():
            self.assertEqual((self.root / "dist" / filename).read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
