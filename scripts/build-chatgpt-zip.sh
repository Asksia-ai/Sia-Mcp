#!/usr/bin/env bash
set -euo pipefail

target_env=preview
if [[ $# -gt 0 ]]; then
    case "$1" in
        --help|-h)
            echo "Usage: $0 [--env preview|production]"
            echo "Build a portable plugin ZIP; preview is the default. No upload is performed."
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
if destination.is_symlink():
    raise SystemExit("Refusing to overwrite a symlinked archive.")

with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for relative in package.ARCHIVE_FILES:
        data = package.package_file(root, relative).read_bytes()
        if relative == "mcp.json":
            metadata = json.loads(data)
            metadata["mcpServers"]["asksia"]["url"] = package.ENDPOINTS[environment]
            data = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        entry = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, data)

with zipfile.ZipFile(destination) as archive:
    assert archive.namelist() == list(package.ARCHIVE_FILES)
    assert archive.testzip() is None
    assert json.loads(archive.read("mcp.json"))["mcpServers"]["asksia"]["url"] == package.ENDPOINTS[environment]
print(destination)
print(f"MCP endpoint: {package.ENDPOINTS[environment]}")
PY
