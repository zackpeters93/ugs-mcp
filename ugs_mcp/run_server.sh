#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
exec /opt/homebrew/opt/python@3.11/libexec/bin/python3 -m ugs_mcp.server
