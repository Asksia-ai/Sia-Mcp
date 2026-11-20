#!/usr/bin/env bash
set -euo pipefail

target_env=preview
if [[ $# -gt 0 ]]; then
    case "$1" in
        --help|-h)
            echo "Usage: $0 [--env preview|production]"
            echo "Build Claude and ChatGPT plugin ZIPs; preview is the default. No upload is performed."
            exit 0
            ;;
        --env)
            if [[ $# -ne 2 || ( "$2" != preview && "$2" != production ) ]]; then
                echo "Expected --env preview or --env production." >&2
                exit 2
            fi
            target_env=$2
            ;;
        *)
            echo "Usage: $0 [--env preview|production]" >&2
            exit 2
            ;;
    esac
fi

plugin_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python3 - "$plugin_root" "$target_env" <<'PY'
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

root = Path(sys.argv[1])
environment = sys.argv[2]
spec = importlib.util.spec_from_file_location("asksia_package", root / "scripts/validate-package.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
package.validate_package(root)

dist = root / "dist"
if dist.is_symlink():
    raise SystemExit("Refusing to write through a symlinked dist directory.")
dist.mkdir(exist_ok=True)
destination = dist / f"asksia-chatgpt-{environment}.zip"
bundle_name = f"asksia-chatgpt-{environment}-install"
bundle_destination = dist / f"{bundle_name}.zip"
claude_name = f"asksia-claude-{environment}"
claude_destination = dist / f"{claude_name}.zip"
for path in (destination, bundle_destination, claude_destination):
    if path.is_symlink():
        raise SystemExit("Refusing to overwrite a symlinked archive.")

files = {name: package.package_file(root, name).read_bytes() for name in package.ARCHIVE_FILES}
metadata = json.loads(files["mcp.json"])
endpoint = package.ENDPOINTS[environment]
metadata["mcpServers"]["asksia"]["url"] = endpoint
files["mcp.json"] = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

marketplace_name = f"asksia-{environment}"
display_name = "AskSia Preview" if environment == "preview" else "AskSia"
marketplace = {
    "name": marketplace_name,
    "interface": {"displayName": display_name},
    "plugins": [{
        "name": "asksia",
        "source": {"source": "local", "path": "./plugins/asksia"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Education & Research",
    }],
}
catalog_path = f"{bundle_name}/.agents/plugins/marketplace.json"
bundle_files = {
    catalog_path: (json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    **{f"{bundle_name}/plugins/asksia/{name}": data for name, data in files.items()},
    f"{bundle_name}/INSTALL.txt": f"""AskSia desktop plugin - {environment}
MCP endpoint: {endpoint}

Prerequisites: a compatible ChatGPT desktop app and a Codex CLI that supports
'codex plugin marketplace add'. This ZIP is a local marketplace bundle.

1. Extract this ZIP into a stable folder on the computer running ChatGPT.
   Keep the extracted folder in place while this marketplace is registered.
2. In Terminal, cd into the extracted {bundle_name} folder, then run:

   codex plugin marketplace add .

3. Restart ChatGPT desktop. Open Plugins, choose the '{display_name}' source,
   and install AskSia. Its plugin identifier is asksia@{marketplace_name}.
4. Follow the client's sign-in prompt, log in to AskSia in the browser,
   and approve the requested permissions. Keep the client open until it finishes.
5. Start a new conversation with the installed plugin enabled. The package
   includes exam-practice, vocab-review, and getting-started skills.

Install this bundle on your Mac for a Mac desktop test, not on an SSH server.
When testing the complete plugin, use its bundled connection; temporarily turn
off a duplicate manually added AskSia MCP connection to avoid mixing the tools.
These steps register only a local source; they do not publish a public listing.
""".encode("utf-8"),
}

claude_files = {
    name: package.package_file(root, name).read_bytes()
    for name in package.SOURCE_FILES if name not in ("plugin.json", "mcp.json")
}
claude_mcp = json.loads(claude_files[".mcp.json"])
claude_mcp["mcpServers"]["asksia"]["url"] = endpoint
claude_files[".mcp.json"] = (json.dumps(claude_mcp, indent=2) + "\n").encode("utf-8")
claude_marketplace = json.loads(claude_files[".claude-plugin/marketplace.json"])
claude_marketplace["name"] = marketplace_name
claude_files[".claude-plugin/marketplace.json"] = (
    json.dumps(claude_marketplace, indent=2) + "\n"
).encode("utf-8")
claude_bundle_files = {
    **{f"{claude_name}/{name}": data for name, data in claude_files.items()},
    f"{claude_name}/INSTALL.txt": f"""AskSia Claude Code plugin - {environment}
MCP endpoint: {endpoint}

Use a Claude Code version that supports plugin marketplaces and validates this
package. Extract this ZIP into a stable local folder and keep it in place.

1. In Terminal, cd into the extracted {claude_name} folder, then run:

   claude plugin marketplace add .
   claude plugin install asksia@{marketplace_name} --scope user

2. Start a new Claude Code session. Run /mcp, select the AskSia server supplied
   by this plugin, and choose Authenticate. Follow the new browser link.
3. Sign in to AskSia and approve the permissions. Keep Claude Code open until
   authorization finishes, then return to the session to use the tools.
4. The installed plugin includes exam-practice, vocab-review, and
   getting-started. Follow the acceptance checklist in README.md.

For this local test, run Claude Code and the browser on the same computer.
Temporarily disable duplicate manually added AskSia servers or older AskSia
plugin installations, so the test uses this bundle's {environment} connection.
Do not reuse an old authorization tab after the client stops waiting.
This local marketplace is separate from a public plugin-directory listing.
""".encode("utf-8"),
}


def write_archive(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)


write_archive(destination, files)
write_archive(bundle_destination, bundle_files)
write_archive(claude_destination, claude_bundle_files)

with zipfile.ZipFile(destination) as archive:
    assert archive.namelist() == list(package.ARCHIVE_FILES)
    assert archive.testzip() is None
    assert json.loads(archive.read("mcp.json"))["mcpServers"]["asksia"]["url"] == package.ENDPOINTS[environment]
with zipfile.ZipFile(bundle_destination) as archive:
    assert archive.namelist() == list(bundle_files)
    assert archive.testzip() is None
    assert json.loads(archive.read(catalog_path)) == marketplace
    for name, data in files.items():
        assert archive.read(f"{bundle_name}/plugins/asksia/{name}") == data
with zipfile.ZipFile(claude_destination) as archive:
    assert archive.namelist() == list(claude_bundle_files)
    assert archive.testzip() is None
    assert json.loads(archive.read(f"{claude_name}/.mcp.json")) == claude_mcp
    assert json.loads(archive.read(f"{claude_name}/.claude-plugin/marketplace.json")) == claude_marketplace
print(destination)
print(bundle_destination)
print(claude_destination)
print(f"MCP endpoint: {endpoint}")
PY
