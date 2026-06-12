# ugs-mcp

[![PyPI version](https://img.shields.io/pypi/v/ugs-mcp.svg)](https://pypi.org/project/ugs-mcp/)
[![CI](https://github.com/zackpeters93/ugs-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/zackpeters93/ugs-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![ugs-mcp MCP server](https://glama.ai/mcp/servers/zackpeters93/ugs-mcp/badges/score.svg)](https://glama.ai/mcp/servers/zackpeters93/ugs-mcp)

**MCP server for controlling CNC machines via Universal GCode Sender.**

Lets Claude (or any MCP-compatible AI assistant) connect to a CNC machine, inspect G-code,
and issue motion commands — all through the UGS Pendant REST API.

---

## ⚠️ STOP. READ THIS FIRST.

**This software controls machines that can damage equipment, destroy parts, and injure or kill people.**

CNC machines move fast and don't know where your hands are. Before you use this:

- Read [SAFETY.md](SAFETY.md). All of it.
- Understand the [token confirmation system](#the-token-system) that prevents Claude from moving your machine autonomously.
- Know where your E-stop is.

If you skim the safety docs and something goes wrong, that's on you. We warned you.

---

## What it does

- **Connection tools** — Connect/disconnect UGS to your CNC, troubleshoot serial port issues
- **Status tools** — Read machine state, position, feed rate, spindle speed
- **Motion tools** (token-protected) — Jog axes, home, return to work zero, run G-code files and macros
- **G-code inspector** — Translate G-code to English, safety check, cycle time estimate, tool list

Every motion command uses a **two-step token protocol**: Claude generates a token, shows it to you,
and the machine only moves when you read the token back. Claude cannot bypass this — tokens are
generated and validated server-side.

---

## Requirements

- Universal GCode Sender 2.x ([winder.github.io/ugs_website](https://winder.github.io/ugs_website/))
- UGS Pendant plugin installed and active (Tools → Plugins → Installed)
- Pendant running at `http://localhost:8080` (default)
- Python 3.11+

---

## Installation

### Via pip

```bash
pip install ugs-mcp
```

### From source

```bash
git clone https://github.com/zackpeters93/ugs-mcp.git
cd ugs-mcp
pip install -e .
```

---

## Claude Code setup

```bash
claude mcp add ugs-cnc ugs-mcp
```

Or from source (without pip install):

```bash
claude mcp add ugs-cnc /path/to/ugs-mcp/ugs_mcp/run_server.sh
```

---

## Claude Desktop setup

In `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ugs-cnc": {
      "command": "ugs-mcp"
    }
  }
}
```

Or from source:

```json
{
  "mcpServers": {
    "ugs-cnc": {
      "command": "/opt/homebrew/opt/python@3.11/libexec/bin/python3",
      "args": ["-m", "ugs_mcp.server"],
      "cwd": "/path/to/ugs-mcp"
    }
  }
}
```

---

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|---|---|---|
| `UGS_HOST` | `localhost` | UGS Pendant host |
| `UGS_PORT` | `8080` | UGS Pendant port |
| `MACROS_DIR` | `ugs_mcp/macros/` | Directory for saved G-code macros |
| `RAPID_SPEED_MM_MIN` | `5000` | Rapid speed used in return-to-zero |

Copy `.env.example` to `.env` to customize.

---

## The token system

Every motion tool uses a mandatory two-step confirmation:

**Step 1** — Call the tool without a token. Claude shows you a preview (axis, distance,
resulting position, safety warnings) and a token like `[A3F8B2C1]`.

**Step 2** — Read the preview. If you agree, tell Claude the token. Claude calls the tool
again with `confirmation_token="A3F8B2C1"`. The machine moves.

Tokens are generated server-side via `uuid4()`, expire in 2 minutes, and are single-use.
Claude cannot predict, fabricate, or reuse them. The only way movement happens is if you
type the token back.

---

## Tools

See [USER_GUIDE.md](USER_GUIDE.md) for the full tool reference with parameters, examples,
and typical workflows.

| Category | Tools |
|---|---|
| Connection | `ugs_connect`, `ugs_disconnect`, `ugs_troubleshoot_connection` |
| Status | `ugs_get_status`, `ugs_get_job_status` |
| Job | `ugs_run_file`, `ugs_pause_job`, `ugs_cancel_job` |
| Motion | `ugs_jog`, `ugs_home`, `ugs_return_to_zero`, `ugs_set_work_zero` |
| G-code | `gcode_safety_check`, `gcode_estimate_time`, `gcode_translate`, `gcode_list_tools`, `gcode_save_macro`, `gcode_list_macros`, `gcode_run_macro` |

---

## Tested with

- SainSmart Genmitsu 3018 Pro (GRBL)
- UGS 2.x with Pendant plugin
- macOS / Python 3.11

Likely works with any GRBL-based machine. TinyG/FluidNC/Smoothieware untested.

---

## License

MIT — see [LICENSE](LICENSE).

**No warranty. No liability. Read [SAFETY.md](SAFETY.md).**

<!-- mcp-name: io.github.zackpeters93/ugs-mcp -->
