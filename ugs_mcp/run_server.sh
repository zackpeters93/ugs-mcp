#!/bin/bash
cd "$(dirname "$0")"
exec /opt/homebrew/opt/python@3.11/libexec/bin/python3 -m server
