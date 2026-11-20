#!/usr/bin/env python3
"""Validate this plugin's portable and Claude package contracts offline."""

import argparse
import json
from pathlib import Path
import re
import sys


REPOSITORY = "https://github.com/Asksia-ai/Sia-Mcp"
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
ENDPOINTS = {
    "preview": "https://api1.asksia.ai/mcp",
    "production": "https://api.asksia.ai/mcp",
}
SKILLS = ("exam-practice", "vocab-review", "getting-started")
ARCHIVE_FILES = (
    "plugin.json",
    "mcp.json",
    *(f"skills/{name}/SKILL.md" for name in SKILLS),
    "assets/asksia.png",
    "README.md",
    "LICENSE",
)
SOURCE_FILES = (*ARCHIVE_FILES, ".claude-plugin/plugin.json",
                ".claude-plugin/marketplace.json", ".mcp.json")


class PackageError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PackageError(message)


def package_file(root, relative):
    """Package only regular files whose resolved target remains inside the root."""
    root = Path(root).resolve()
    path = root / relative
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise PackageError(f"Path leaves the plugin: {relative}") from exc
    require(path.is_file(), f"Missing package file: {relative}")
    return path


def read_json(root, relative):
    try:
        value = json.loads(package_file(root, relative).read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"Invalid UTF-8 JSON: {relative}") from exc
    require(isinstance(value, dict), f"Expected a JSON object: {relative}")
    return value


def validate_package(root):
    root = Path(root).resolve()
    for relative in SOURCE_FILES:
        package_file(root, relative)
    portable = read_json(root, "plugin.json")
    claude = read_json(root, ".claude-plugin/plugin.json")
    require(portable.get("$schema") == PLUGIN_SCHEMA, "Use the portable Agent Plugins schema.")
    for manifest in (portable, claude):
        require(manifest.get("name") == "asksia", "The plugin name must remain asksia.")
        require(manifest.get("repository") == REPOSITORY, "Use the current Sia-Mcp repository.")
        require(isinstance(manifest.get("version"), str) and manifest["version"], "A plugin version is required.")
        require(isinstance(manifest.get("description"), str) and manifest["description"], "A plugin description is required.")
    require(portable["version"] == claude["version"], "Portable and Claude versions must match.")
    require(claude.get("displayName") == "AskSia", "Claude displayName must be AskSia.")
    require(claude.get("icon") == "./assets/asksia.png", "Use the bundled AskSia icon.")

    extension = portable.get("extensions", {}).get("com.openai", {})
    require(isinstance(extension, dict), "The OpenAI extension must be an object.")
    interface = extension.get("interface", {})
    require(isinstance(interface, dict), "The OpenAI interface must be an object.")
    require(interface.get("displayName") == "AskSia", "OpenAI displayName must be AskSia.")
    for field in ("composerIcon", "logo"):
        require(interface.get(field) == "./assets/asksia.png", f"Use the bundled asset for {field}.")
    require(not any(key in extension for key in ("hooks", "apps")), "This package needs no hooks or app references.")

    marketplace = read_json(root, ".claude-plugin/marketplace.json")
    require(marketplace.get("name") == "asksia", "The marketplace name must be asksia.")
    entries = marketplace.get("plugins")
    require(isinstance(entries, list) and len(entries) == 1, "The marketplace must contain only this plugin.")
    require(isinstance(entries[0], dict) and entries[0].get("name") == "asksia"
            and entries[0].get("source") == "./", "The marketplace must point to this repository root.")

    for filename, transport in ((".mcp.json", "http"), ("mcp.json", "streamable-http")):
        config = read_json(root, filename)
        servers = config.get("mcpServers")
        require(isinstance(servers, dict) and set(servers) == {"asksia"}, f"Expected only the asksia MCP server in {filename}.")
        server = servers["asksia"]
        require(isinstance(server, dict), f"The asksia server must be an object in {filename}.")
        require(set(server) == {"type", "url"}, f"Unexpected MCP fields or embedded credentials in {filename}.")
        require(server["type"] == transport, f"Incorrect transport type in {filename}.")
        require(server["url"] == ENDPOINTS["production"], f"Source {filename} must use the production endpoint; builds select preview separately.")
        if filename == "mcp.json":
            require(config.get("$schema") == MCP_SCHEMA, "Use the portable MCP schema.")

    require(package_file(root, "assets/asksia.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
            "The bundled icon must be a PNG.")
    for name in SKILLS:
        content = package_file(root, f"skills/{name}/SKILL.md").read_text(encoding="utf-8")
        header = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", content, flags=re.DOTALL)
        require(header is not None, f"Missing skill frontmatter: {name}")
        fields = dict(re.findall(r"^(name|description):[ \t]*(.+)$", header.group(1), flags=re.MULTILINE))
        require(fields.get("name") == name, f"Skill name must match its directory: {name}")
        require(bool(fields.get("description", "").strip()), f"Skill description is required: {name}")
        require(bool(content[header.end():].strip()), f"Skill instructions are required: {name}")
    return portable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Plugin root (defaults to this script's parent directory)")
    args = parser.parse_args()
    try:
        manifest = validate_package(args.path)
    except (PackageError, OSError, UnicodeError, TypeError, AttributeError) as exc:
        print(f"Package validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated AskSia {manifest['version']}: Claude and portable package files are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
