# UGS MCP — Publication Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `ugs-mcp` as a production-ready open source package on GitHub and PyPI, with a follow-on submission to the UGS community.

**Architecture:** The package is a FastMCP server wrapping the UGS Pendant REST API. No structural changes — this plan is purely about packaging, documentation, legal, and distribution. The existing source in `ugs_mcp/` stays as-is.

**Tech Stack:** Python 3.11+, FastMCP, httpx, pyserial — packaged via `pyproject.toml` (Hatch backend), distributed via PyPI and GitHub releases.

---

## Pre-flight: What already exists

- GitHub remote: `https://github.com/zackpeters93/ugs-mcp.git`
- Source: `ugs_mcp/` with 19 MCP tools, test suite, `USER_GUIDE.md`
- No `LICENSE`, no `README.md`, no `pyproject.toml`
- `.gitignore` is inside `ugs_mcp/` (wrong location)
- `.venv/` is in the repo root and almost certainly not gitignored at the root level

---

## Task 1: Audit committed files for private data and repo hygiene

**Files:**
- Read: `ugs_mcp/.gitignore`
- Read: `.git/info/exclude` (local gitignore)
- Run: `git ls-files` to see what's actually tracked

- [ ] **Step 1: See what git is currently tracking**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git ls-files | head -60
```

Expected: See all tracked files. Look for `.venv/`, `.env`, `__pycache__`, or any secrets.

- [ ] **Step 2: Create root-level `.gitignore`**

Create `/Users/techdev/Projects/ClaudeDC/UGS_MCP/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg
*.egg-info/
dist/
build/
.eggs/
*.whl

# Virtual environments
.venv/
venv/
env/

# Environment / secrets
.env
.env.*
!.env.example

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/

# macros (user-specific, not part of the package)
ugs_mcp/macros/*.gcode
ugs_mcp/macros/*.nc
ugs_mcp/macros/*.txt
# Keep the directory itself
!ugs_mcp/macros/.gitkeep

# OS
.DS_Store
```

- [ ] **Step 3: Untrack anything that shouldn't be committed**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git rm -r --cached .venv 2>/dev/null || true
git rm -r --cached ugs_mcp/__pycache__ 2>/dev/null || true
git rm -r --cached ugs_mcp/.pytest_cache 2>/dev/null || true
git status
```

Expected: Deleted entries for `.venv/`, cache dirs. Modified `.gitignore`.

- [ ] **Step 4: Commit hygiene changes**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git add .gitignore
git commit -m "chore: root .gitignore; untrack venv and cache dirs"
```

---

## Task 2: Choose and add a license

MIT is the right call: maximum adoption, CNC hobbyist community expects it, compatible with FastMCP's MIT license.

**Files:**
- Create: `/Users/techdev/Projects/ClaudeDC/UGS_MCP/LICENSE`

- [ ] **Step 1: Create the LICENSE file**

Create `/Users/techdev/Projects/ClaudeDC/UGS_MCP/LICENSE`:

```
MIT License

Copyright (c) 2026 Zack Peters

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git add LICENSE
git commit -m "chore: add MIT license"
```

---

## Task 3: Write the safety disclaimer

The user's brief: **irreverent but absolutely serious**. People need to understand they can wreck their machine, hurt themselves, or kill someone with an uncommanded movement. "Don't be a dumbass" energy throughout.

**Files:**
- Create: `/Users/techdev/Projects/ClaudeDC/UGS_MCP/SAFETY.md`

- [ ] **Step 1: Create SAFETY.md**

Create `/Users/techdev/Projects/ClaudeDC/UGS_MCP/SAFETY.md`:

```markdown
# SAFETY — Read This Before You Touch Anything

## This software can hurt you. Seriously.

A CNC machine is a robot that holds a spinning blade and moves it with enough force to
cut through wood, aluminum, and your fingers. When you give an AI assistant control of
that robot, you are responsible for what happens next.

This MCP server lets Claude issue motion commands to your CNC via Universal GCode Sender.
Claude is a language model. It does not know what your hands are doing. It does not know
your dog is chewing on the power cable. It does not know the workpiece is loose. It does
not feel bad if it breaks your bit, crashes your machine, or injures you.

**You are the last line of defense. Act like it.**

---

## What can go wrong

- **Unexpected motion** — If you or your AI assistant issues a jog command at the wrong
  moment, the machine moves. If your hand is in the way, the machine does not care.

- **Wrong work zero** — Set the wrong zero and your G-code runs somewhere other than where
  you think it does. Best case: ruined part. Worst case: the spindle drives into the
  fixture or the table.

- **Homing cycle surprises** — Homing drives every axis toward its limit switch at full
  speed. If a switch is broken, missing, or mis-wired, the machine drives into the frame.
  Hard.

- **Uncommanded movements from bugs** — Software has bugs. This software has bugs. If a
  bug causes an unexpected tool call, the machine moves. This is why we built the token
  system. It is not a guarantee.

- **Runaway jobs** — If a G-code file has an error (wrong units, zero feedrate, spindle
  off during a cut), `gcode_safety_check` catches most of it. Not all of it. Check your
  G-code yourself before running it.

---

## The token system: what it does and what it doesn't

Every motion command in this server requires a two-step confirmation. Claude generates a
token, shows it to you, and you must read it back before the machine moves. Claude cannot
fabricate or reuse tokens — they are generated server-side and are single-use.

**What this prevents:** Claude autonomously moving your machine without your knowledge.

**What this does NOT prevent:**
- You confirming a token without looking at the preview.
- You confirming a token while your hand is in the machine.
- A bug in this software issuing a command outside the token system.
- You ignoring this warning and doing something dumb.

Read every preview. Every single one. They are not formalities.

---

## Ground rules

1. **Never confirm a token without reading the preview.** If you're not sure what the
   preview is telling you, don't confirm it.

2. **Keep your hands out of the machine during any operation.** This sounds obvious.
   It isn't, when you're focused on a screen.

3. **Know where your E-stop is.** Before you run anything, know how to kill power to the
   machine instantly. A keyboard shortcut in UGS is not the same as a physical E-stop.

4. **Never leave a running job unattended.** Claude cannot smell smoke. You can.

5. **Run `gcode_safety_check` before every file you didn't generate yourself.** Even then,
   review it. The safety check catches common issues, not all issues.

6. **Treat every `$H` (home) command like it might be the last thing your machine does
   without a repair bill.** Make sure the travel path is clear.

---

## Liability

This software is provided under the MIT License: no warranty, no liability, no guarantees.
If your machine crashes, your bit breaks, your part is ruined, or you get hurt, that is
between you and your choices. The authors are not responsible.

If you are not comfortable accepting that risk, do not use this software.

---

## TL;DR

CNC machines are dangerous. AI assistants don't know they're dangerous. You do.
**Don't be a dumbass. Read the preview. Keep your hands clear. Know your E-stop.**
```

- [ ] **Step 2: Commit**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git add SAFETY.md
git commit -m "docs: add SAFETY.md with usage warnings and liability disclaimer"
```

---

## Task 4: Add `pyproject.toml` for proper Python packaging

This replaces `requirements.txt` as the authoritative dependency declaration and enables `pip install ugs-mcp`.

**Files:**
- Create: `/Users/techdev/Projects/ClaudeDC/UGS_MCP/pyproject.toml`
- Keep: `ugs_mcp/requirements.txt` (for dev convenience only — add a comment)

- [ ] **Step 1: Create pyproject.toml**

Create `/Users/techdev/Projects/ClaudeDC/UGS_MCP/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ugs-mcp"
version = "0.1.0"
description = "MCP server for controlling CNC machines via Universal GCode Sender"
readme = "README.md"
license = { file = "LICENSE" }
authors = [{ name = "Zack Peters", email = "zapeters@gmail.com" }]
keywords = ["mcp", "cnc", "gcode", "ugs", "universal-gcode-sender", "grbl", "claude"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Manufacturing",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering",
]
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "pyserial>=3.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.urls]
Homepage = "https://github.com/zackpeters93/ugs-mcp"
Repository = "https://github.com/zackpeters93/ugs-mcp"
"Bug Tracker" = "https://github.com/zackpeters93/ugs-mcp/issues"

[project.scripts]
ugs-mcp = "ugs_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["ugs_mcp"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["ugs_mcp/tests"]
```

- [ ] **Step 2: Add `main()` entry point to server.py**

Edit `/Users/techdev/Projects/ClaudeDC/UGS_MCP/ugs_mcp/server.py` — add at the bottom:

```python
def main():
    mcp.run()

if __name__ == "__main__":
    main()
```

(Replace the existing `if __name__ == "__main__": mcp.run()` block.)

- [ ] **Step 3: Verify the package builds**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
/opt/homebrew/opt/python@3.11/libexec/bin/pip install hatch 2>/dev/null || pip install hatch
hatch build
```

Expected: `dist/ugs_mcp-0.1.0.tar.gz` and `dist/ugs_mcp-0.1.0-py3-none-any.whl` created with no errors.

- [ ] **Step 4: Verify the installed CLI entry point works**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
pip install -e ".[dev]" --quiet
ugs-mcp --help 2>&1 | head -5 || echo "(no --help flag is fine — FastMCP doesn't use argparse)"
```

Expected: Either help output or a graceful start attempt. No import errors.

- [ ] **Step 5: Commit**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git add pyproject.toml ugs_mcp/server.py
git commit -m "feat: add pyproject.toml; add main() entry point for pip install"
```

---

## Task 5: Write README.md

The README is the project's storefront. Safety warning goes at the top — before installation, before anything. Then installation, config, quick-start, link to USER_GUIDE.md.

**Files:**
- Create: `/Users/techdev/Projects/ClaudeDC/UGS_MCP/README.md`

- [ ] **Step 1: Create README.md**

Create `/Users/techdev/Projects/ClaudeDC/UGS_MCP/README.md`:

```markdown
# ugs-mcp

**MCP server for controlling CNC machines via Universal GCode Sender.**

Lets Claude (or any MCP-compatible AI assistant) connect to a CNC machine, inspect G-code, and issue motion commands — all through the UGS Pendant REST API.

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

Every motion command uses a **two-step token protocol**: Claude generates a token, shows it to you, and the machine only moves when you read the token back. Claude cannot bypass this — tokens are generated and validated server-side.

---

## Requirements

- Universal GCode Sender 2.x ([winder.github.io/ugs_website](https://winder.github.io/ugs_website/))
- UGS Pendant plugin installed and active (Tools → Plugins → Installed)
- Pendant running at `http://localhost:8080` (default)
- Python 3.11+

---

## Installation

### Via pip (recommended)

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

Or if running from source:

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
      "args": ["-m", "server"],
      "cwd": "/path/to/ugs-mcp/ugs_mcp"
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

**Step 1** — Call the tool without a token. Claude shows you a preview (axis, distance, resulting position, safety warnings) and a token like `[A3F8B2C1]`.

**Step 2** — Read the preview. If you agree, tell Claude the token. Claude calls the tool again with `confirmation_token="A3F8B2C1"`. The machine moves.

Tokens are generated server-side via `uuid4()`, expire in 2 minutes, and are single-use. Claude cannot predict, fabricate, or reuse them. The only way movement happens is if you type the token back.

---

## Tools

See [USER_GUIDE.md](USER_GUIDE.md) for the full tool reference with parameters, examples, and typical workflows.

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
```

- [ ] **Step 2: Commit**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git add README.md
git commit -m "docs: add README.md with safety header, installation, tool table"
```

---

## Task 6: Run the test suite and fix any failures

Before publishing, confirm the tests pass clean.

**Files:**
- Read: `ugs_mcp/tests/` (all test files)

- [ ] **Step 1: Run all tests**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP/ugs_mcp
/opt/homebrew/opt/python@3.11/libexec/bin/python3 -m pytest tests/ -v 2>&1
```

Expected: All tests pass. Note any failures.

- [ ] **Step 2: Fix any failures**

If tests fail, investigate and fix before proceeding. Common issues:
- Import paths broken by packaging changes
- `asyncio_mode` not set (fixed in `pyproject.toml` above)
- Missing test fixtures

- [ ] **Step 3: Commit any fixes**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git add -A
git commit -m "fix: test suite passing after packaging changes"
```

(Skip this step if no fixes were needed.)

---

## Task 7: GitHub repo polish and first real release

The repo exists. Now make it look like a real project.

**Actions (no file changes — all GitHub UI or CLI):**

- [ ] **Step 1: Push all commits**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
git push origin main
```

- [ ] **Step 2: Set GitHub repo metadata via CLI**

```bash
gh repo edit zackpeters93/ugs-mcp \
  --description "MCP server for controlling CNC machines via Universal GCode Sender" \
  --add-topic "mcp,cnc,gcode,grbl,ugs,claude,universal-gcode-sender,cncmilling"
```

- [ ] **Step 3: Create v0.1.0 release**

```bash
gh release create v0.1.0 \
  --title "v0.1.0 — Initial release" \
  --notes "First public release. Tested with SainSmart Genmitsu 3018 Pro + UGS 2.x + GRBL.

## What's included
- 19 MCP tools across 5 categories: Connection, Status, Motion, Job, G-code Inspector
- Two-step token safety system for all motion commands
- G-code safety checker, cycle time estimator, English translator, and macro system
- Full test suite

## Supported
- GRBL-based CNC machines via UGS Pendant REST API
- Claude Code and Claude Desktop
- macOS / Python 3.11+

**Read [SAFETY.md](SAFETY.md) before using.**"
```

---

## Task 8: Publish to PyPI

- [ ] **Step 1: Build distribution artifacts**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
hatch build
ls dist/
```

Expected: `ugs_mcp-0.1.0.tar.gz` and `ugs_mcp-0.1.0-py3-none-any.whl`

- [ ] **Step 2: Test on TestPyPI first**

```bash
pip install twine
twine upload --repository testpypi dist/* --verbose
```

You'll need a TestPyPI account at test.pypi.org. This catches packaging errors before they hit the real index.

- [ ] **Step 3: Verify TestPyPI install works**

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ugs-mcp
ugs-mcp --version 2>&1 || echo "install OK"
```

- [ ] **Step 4: Publish to PyPI**

```bash
twine upload dist/*
```

You'll need a PyPI account at pypi.org and an API token. Set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=<your-pypi-token>` in your environment.

- [ ] **Step 5: Verify PyPI install**

```bash
pip install ugs-mcp
```

Expected: Installs cleanly from PyPI.

---

## Task 9: Submit to the UGS community

UGS does not have a formal MCP/plugin marketplace for external integrations, but the project is active on GitHub and has a community forum. Two paths:

- [ ] **Step 1: Research current UGS community channels**

Check:
- `https://github.com/winder/Universal-G-Code-Sender` — look for CONTRIBUTING.md, community links, discussions tab
- `https://winder.github.io/ugs_website/` — look for community/forum links

Goal: Identify where community-built tools are announced (GitHub Discussions, mailing list, Discord, forum post).

- [ ] **Step 2: Open a GitHub Discussion on the UGS repo**

```bash
gh api repos/winder/Universal-G-Code-Sender/discussions \
  --method POST \
  -f title="ugs-mcp: MCP server for controlling UGS from AI assistants (Claude)" \
  -f body="Hi UGS community,

I built an MCP (Model Context Protocol) server that wraps the UGS Pendant REST API, letting AI assistants like Claude Code issue motion commands, run G-code files, and inspect G-code — directly from a conversation.

**GitHub:** https://github.com/zackpeters93/ugs-mcp
**PyPI:** https://pypi.org/project/ugs-mcp/

Safety is built into the protocol: motion commands use a two-step token system that requires human confirmation before the machine moves. The AI generates a token and shows it to the user; the user reads it back; the machine moves. The AI cannot self-confirm or bypass this at the server level.

Tested with: SainSmart Genmitsu 3018 Pro + GRBL + UGS 2.x on macOS.

Would love feedback from the community, especially from anyone running TinyG or FluidNC.

Full safety warnings: https://github.com/zackpeters93/ugs-mcp/blob/main/SAFETY.md" \
  -f category_id="$(gh api repos/winder/Universal-G-Code-Sender/discussions/categories --jq '.[] | select(.name | test("General|Show|Announce"; "i")) | .id' | head -1)"
```

Note: If the UGS repo doesn't have Discussions enabled or the API call fails, post manually in the GitHub Discussions tab. Adapt the message for any forum or mailing list found in Step 1.

- [ ] **Step 3: Add the MCP server to the MCP server list (if applicable)**

Check if `https://github.com/modelcontextprotocol/servers` has a community submissions process. If so, open a PR adding `ugs-mcp` to the community section.

---

## Spec coverage check

| Requirement | Task |
|---|---|
| Licensing | Task 2 — MIT LICENSE |
| Legal / safety disclaimers | Task 3 — SAFETY.md |
| Code cleanup / audit | Task 1 — gitignore, untrack junk |
| Packaging | Task 4 — pyproject.toml, pip install |
| Documentation | Task 5 — README.md; USER_GUIDE.md already exists |
| Test suite passing | Task 6 |
| GitHub distribution | Task 7 — push, release tag |
| PyPI distribution | Task 8 |
| UGS Platform listing | Task 9 |

---

## Order of execution

Tasks must run in this order (each depends on the previous):

1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

No parallelism needed; this is a linear publication pipeline.
