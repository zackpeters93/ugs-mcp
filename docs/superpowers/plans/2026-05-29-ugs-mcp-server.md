# UGS MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server that lets Claude Code control a CNC machine via Universal G-Code Sender (UGS), including machine controls, a G-code inspector, and macro management.

**Architecture:** Thin REST bridge over UGS's web pendant API (`localhost:8080`) using `httpx`. G-code inspector runs entirely locally via a purpose-built parser and modal state machine. FastMCP handles tool registration and stdio transport.

**Tech Stack:** Python 3.11+, `mcp` (FastMCP), `httpx`, `pyserial`, `pytest`, `pytest-asyncio`

---

## File Map

```
ugs_mcp/
├── server.py              -- FastMCP entry point, registers all 19 tools
├── config.py              -- env vars, WARNING_MESSAGES dict
├── ugs_client.py          -- async httpx wrapper for UGS pendant REST API
├── tools/
│   ├── __init__.py
│   ├── connection.py      -- ugs_connect, ugs_disconnect, ugs_troubleshoot_connection
│   ├── motion.py          -- ugs_jog, ugs_home, ugs_set_work_zero, ugs_return_to_zero
│   ├── job.py             -- ugs_run_file, ugs_pause_job, ugs_cancel_job, ugs_get_job_status
│   ├── status.py          -- ugs_get_status
│   └── inspector.py       -- gcode_translate, gcode_safety_check, gcode_estimate_time,
│                             gcode_list_tools, gcode_save_macro, gcode_run_macro, gcode_list_macros
├── gcode/
│   ├── __init__.py
│   ├── parser.py          -- parse_line, parse_string, parse_file, load_gcode
│   ├── state.py           -- ModalState dataclass, apply_line
│   ├── commands.py        -- GCODE_DESCRIPTIONS dict, describe_word
│   └── analyzer.py        -- translate, safety_check, estimate_time, list_tools
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_state.py
│   ├── test_commands.py
│   ├── test_analyzer.py
│   ├── test_ugs_client.py
│   ├── test_connection.py
│   ├── test_status.py
│   ├── test_motion.py
│   ├── test_job.py
│   └── test_inspector.py
├── macros/                -- saved .nc macro files (created at runtime)
├── requirements.txt
└── .env.example
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `ugs_mcp/requirements.txt`
- Create: `ugs_mcp/.env.example`
- Create: `ugs_mcp/config.py`
- Create: `ugs_mcp/gcode/__init__.py`
- Create: `ugs_mcp/tools/__init__.py`
- Create: `ugs_mcp/tests/__init__.py`
- Create: `ugs_mcp/macros/.gitkeep`

- [ ] **Step 1: Create project directories**

```bash
cd /Users/techdev/Projects/ClaudeDC/UGS_MCP
mkdir -p ugs_mcp/tools ugs_mcp/gcode ugs_mcp/tests ugs_mcp/macros
touch ugs_mcp/tools/__init__.py ugs_mcp/gcode/__init__.py ugs_mcp/tests/__init__.py ugs_mcp/macros/.gitkeep
```

- [ ] **Step 2: Write requirements.txt**

```text
mcp>=1.0.0
httpx>=0.27.0
pyserial>=3.5
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

Save to `ugs_mcp/requirements.txt`.

- [ ] **Step 3: Write .env.example**

```text
UGS_HOST=localhost
UGS_PORT=8080
MACROS_DIR=./macros
RAPID_SPEED_MM_MIN=5000
```

Save to `ugs_mcp/.env.example`.

- [ ] **Step 4: Write config.py**

```python
import os
from pathlib import Path

UGS_HOST = os.getenv("UGS_HOST", "localhost")
UGS_PORT = os.getenv("UGS_PORT", "8080")
UGS_BASE_URL = f"http://{UGS_HOST}:{UGS_PORT}"
MACROS_DIR = Path(os.getenv("MACROS_DIR", "./macros"))
RAPID_SPEED_MM_MIN = float(os.getenv("RAPID_SPEED_MM_MIN", "5000"))

WARNING_MESSAGES = {
    "jog": "** WARNING: THIS WILL MOVE YOUR MACHINE! **",
    "return_to_zero": "** WARNING: THIS WILL MOVE YOUR MACHINE! **",
    "home": "** DANGER: HOMING DRIVES ALL AXES INTO THEIR LIMIT SWITCHES AT FULL SPEED! **",
    "run_file": "** WARNING: THIS WILL START YOUR CNC JOB - SPINDLE WILL SPIN AND THINGS WILL CUT! **",
    "cancel_job": "** CAUTION: STOPPING MID-CUT WILL LEAVE A MARK ON YOUR PART! **",
    "set_work_zero": "** CAUTION: THIS WILL CHANGE YOUR WORK COORDINATES - WRONG ZERO = CRASHED BIT! **",
    "run_macro": "** HEADS UP: THIS IS JUST LIKE RUNNING A MACRO - VERIFY THE G-CODE FIRST! **",
    "connection_issue": "** DON'T BE STUPID - FIX YOUR CONNECTION BEFORE TOUCHING ANYTHING! **",
}
```

Save to `ugs_mcp/config.py`.

- [ ] **Step 5: Install dependencies**

```bash
cd ugs_mcp
pip install -r requirements.txt
```

- [ ] **Step 6: Write conftest.py**

```python
# ugs_mcp/conftest.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
```

Save to `ugs_mcp/conftest.py`. This ensures pytest finds `gcode.*` and `tools.*` as top-level packages.

- [ ] **Step 7: Verify pytest runs**

```bash
cd ugs_mcp
pytest tests/ -v
```

Expected: "no tests ran" or "0 passed" - empty suite is fine.

- [ ] **Step 8: Commit**

```bash
git init
git add .
git commit -m "feat: project scaffold for ugs_mcp server"
```

---

## Task 2: G-code Parser

**Files:**

- Create: `ugs_mcp/gcode/parser.py`
- Create: `ugs_mcp/tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_parser.py
import pytest
from gcode.parser import parse_line, parse_string, load_gcode, GCodeWord, GCodeLine

def test_parse_simple_g0():
    line = parse_line("G0 X10 Y20", line_number=1)
    assert line.line_number == 1
    assert GCodeWord("G", 0.0) in line.words
    assert GCodeWord("X", 10.0) in line.words
    assert GCodeWord("Y", 20.0) in line.words

def test_parse_g1_with_feedrate():
    line = parse_line("G1 X25.4 Y10.0 F500", line_number=12)
    assert GCodeWord("G", 1.0) in line.words
    assert GCodeWord("F", 500.0) in line.words

def test_parse_comment_parentheses():
    line = parse_line("G0 X0 (go to origin)", line_number=1)
    assert line.comment == "go to origin"
    assert GCodeWord("X", 0.0) in line.words

def test_parse_comment_semicolon():
    line = parse_line("G21 ; set metric", line_number=1)
    assert line.comment == "set metric"
    assert GCodeWord("G", 21.0) in line.words

def test_parse_negative_value():
    line = parse_line("G0 Z-5.0", line_number=1)
    assert GCodeWord("Z", -5.0) in line.words

def test_parse_case_insensitive():
    line = parse_line("g1 x10 y20 f300", line_number=1)
    assert GCodeWord("G", 1.0) in line.words
    assert GCodeWord("X", 10.0) in line.words

def test_parse_empty_line():
    line = parse_line("", line_number=5)
    assert line.words == []
    assert line.comment is None

def test_parse_comment_only():
    line = parse_line("(this is setup)", line_number=1)
    assert line.words == []
    assert line.comment == "this is setup"

def test_parse_string_multiline():
    code = "G21\nG90\nG0 X0 Y0"
    lines = parse_string(code)
    assert len(lines) == 3
    assert GCodeWord("G", 21.0) in lines[0].words
    assert GCodeWord("G", 90.0) in lines[1].words

def test_load_gcode_from_string():
    raw = "G21\nG1 X10"
    lines = load_gcode(raw)
    assert len(lines) == 2

def test_load_gcode_from_file(tmp_path):
    f = tmp_path / "test.nc"
    f.write_text("G21\nG0 X0\n")
    lines = load_gcode(str(f))
    assert len(lines) == 2

def test_parse_m_code():
    line = parse_line("M3 S18000", line_number=1)
    assert GCodeWord("M", 3.0) in line.words
    assert GCodeWord("S", 18000.0) in line.words
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_parser.py -v
```

Expected: ImportError or similar - `gcode.parser` does not exist yet.

- [ ] **Step 3: Write parser.py**

```python
# ugs_mcp/gcode/parser.py
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class GCodeWord:
    letter: str
    value: float

    def __eq__(self, other):
        if not isinstance(other, GCodeWord):
            return False
        return self.letter == other.letter and abs(self.value - other.value) < 1e-9


@dataclass
class GCodeLine:
    line_number: int
    raw: str
    words: List[GCodeWord] = field(default_factory=list)
    comment: Optional[str] = None


_WORD_PATTERN = re.compile(r"([A-Za-z])(-?\d+(?:\.\d+)?)")
_PAREN_COMMENT = re.compile(r"\(([^)]*)\)")
_SEMI_COMMENT = re.compile(r";(.*)")


def parse_line(line: str, line_number: int = 0) -> GCodeLine:
    raw = line.strip()
    comment = None

    # Extract parenthesis comment
    paren_match = _PAREN_COMMENT.search(raw)
    if paren_match:
        comment = paren_match.group(1).strip()
        raw = _PAREN_COMMENT.sub("", raw).strip()

    # Extract semicolon comment
    semi_match = _SEMI_COMMENT.search(raw)
    if semi_match:
        if comment is None:
            comment = semi_match.group(1).strip()
        raw = raw[: semi_match.start()].strip()

    words = [
        GCodeWord(letter=m.group(1).upper(), value=float(m.group(2)))
        for m in _WORD_PATTERN.finditer(raw)
    ]

    return GCodeLine(line_number=line_number, raw=line.strip(), words=words, comment=comment)


def parse_string(gcode: str) -> List[GCodeLine]:
    return [
        parse_line(line, line_number=i + 1)
        for i, line in enumerate(gcode.splitlines())
    ]


def parse_file(path: str) -> List[GCodeLine]:
    return parse_string(Path(path).read_text())


def load_gcode(file_path_or_code: str) -> List[GCodeLine]:
    """Auto-detect: if string is an existing file path, read it; else parse as raw G-code."""
    p = Path(file_path_or_code)
    if p.exists() and p.is_file():
        return parse_file(file_path_or_code)
    return parse_string(file_path_or_code)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_parser.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gcode/parser.py tests/test_parser.py
git commit -m "feat: G-code line parser with comment extraction"
```

---

## Task 3: Modal State Machine

**Files:**
- Create: `ugs_mcp/gcode/state.py`
- Create: `ugs_mcp/tests/test_state.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_state.py
from gcode.parser import parse_line
from gcode.state import ModalState, apply_line


def test_initial_state():
    s = ModalState()
    assert s.units == "mm"
    assert s.positioning == "absolute"
    assert s.spindle_state == "off"
    assert s.feedrate == 0.0


def test_g20_switches_to_inches():
    s = apply_line(ModalState(), parse_line("G20"))
    assert s.units == "inch"


def test_g21_switches_to_mm():
    s = apply_line(ModalState(), parse_line("G21"))
    assert s.units == "mm"


def test_g90_absolute():
    s = apply_line(ModalState(), parse_line("G90"))
    assert s.positioning == "absolute"


def test_g91_relative():
    s = apply_line(ModalState(), parse_line("G91"))
    assert s.positioning == "relative"


def test_m3_spindle_cw():
    s = apply_line(ModalState(), parse_line("M3 S18000"))
    assert s.spindle_state == "cw"
    assert s.spindle_speed == 18000.0


def test_m5_spindle_off():
    s = ModalState(spindle_state="cw", spindle_speed=18000.0)
    s = apply_line(s, parse_line("M5"))
    assert s.spindle_state == "off"


def test_feedrate_persists():
    s = apply_line(ModalState(), parse_line("G1 X10 F500"))
    assert s.feedrate == 500.0
    s2 = apply_line(s, parse_line("G1 X20"))
    assert s2.feedrate == 500.0


def test_tool_change():
    s = apply_line(ModalState(), parse_line("T2 M6"))
    assert s.tool == 2


def test_position_updates_on_g0():
    s = apply_line(ModalState(), parse_line("G0 X10 Y20 Z-5"))
    assert s.position["X"] == 10.0
    assert s.position["Y"] == 20.0
    assert s.position["Z"] == -5.0


def test_g17_sets_xy_plane():
    s = apply_line(ModalState(), parse_line("G17"))
    assert s.plane == "XY"


def test_g54_sets_coord_system():
    s = apply_line(ModalState(), parse_line("G54"))
    assert s.coord_system == "G54"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_state.py -v
```

Expected: ImportError - `gcode.state` does not exist.

- [ ] **Step 3: Write state.py**

```python
# ugs_mcp/gcode/state.py
from dataclasses import dataclass, field
from typing import Optional
from .parser import GCodeLine, GCodeWord


@dataclass
class ModalState:
    units: str = "mm"
    positioning: str = "absolute"
    plane: str = "XY"
    feedrate_mode: str = "units_per_min"
    feedrate: float = 0.0
    spindle_state: str = "off"
    spindle_speed: float = 0.0
    tool: Optional[int] = None
    coord_system: str = "G54"
    position: dict = field(default_factory=lambda: {"X": 0.0, "Y": 0.0, "Z": 0.0})
    homed: bool = False
    work_zero_set: bool = False

    def copy(self) -> "ModalState":
        import copy
        return copy.deepcopy(self)


def apply_line(state: ModalState, line: GCodeLine) -> ModalState:
    """Return a new ModalState after applying all words in a G-code line."""
    s = state.copy()

    words = {w.letter: w.value for w in line.words}

    # Spindle speed
    if "S" in words:
        s.spindle_speed = words["S"]

    # Tool
    if "T" in words:
        s.tool = int(words["T"])

    # Feedrate
    if "F" in words:
        s.feedrate = words["F"]

    # G-codes
    g = words.get("G")
    if g is not None:
        if g == 20:
            s.units = "inch"
        elif g == 21:
            s.units = "mm"
        elif g == 90:
            s.positioning = "absolute"
        elif g == 91:
            s.positioning = "relative"
        elif g == 17:
            s.plane = "XY"
        elif g == 18:
            s.plane = "XZ"
        elif g == 19:
            s.plane = "YZ"
        elif g == 94:
            s.feedrate_mode = "units_per_min"
        elif g == 95:
            s.feedrate_mode = "units_per_rev"
        elif g in (54, 55, 56, 57, 58, 59):
            s.coord_system = f"G{int(g)}"
        elif g == 28:
            s.homed = True

    # M-codes
    m = words.get("M")
    if m is not None:
        if m == 3:
            s.spindle_state = "cw"
        elif m == 4:
            s.spindle_state = "ccw"
        elif m == 5:
            s.spindle_state = "off"
        elif m == 6:
            pass  # tool already updated from T word

    # Position update for motion commands
    if g in (0, 1, 2, 3):
        for axis in ("X", "Y", "Z"):
            if axis in words:
                if s.positioning == "absolute":
                    s.position[axis] = words[axis]
                else:
                    s.position[axis] += words[axis]

    return s
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_state.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gcode/state.py tests/test_state.py
git commit -m "feat: modal state machine for G-code context tracking"
```

---

## Task 4: G-code Commands Glossary

**Files:**
- Create: `ugs_mcp/gcode/commands.py`
- Create: `ugs_mcp/tests/test_commands.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_commands.py
from gcode.commands import describe_word, GCODE_DESCRIPTIONS


def test_g0_description():
    result = describe_word("G", 0)
    assert "rapid" in result.lower() or "positioning" in result.lower()


def test_g1_description():
    result = describe_word("G", 1)
    assert "linear" in result.lower() or "cut" in result.lower()


def test_m3_description():
    result = describe_word("M", 3)
    assert "spindle" in result.lower()


def test_m5_description():
    result = describe_word("M", 5)
    assert "spindle" in result.lower() or "stop" in result.lower()


def test_unknown_code_returns_string():
    result = describe_word("G", 999)
    assert "999" in result


def test_g21_metric():
    result = describe_word("G", 21)
    assert "mm" in result.lower() or "millimeter" in result.lower() or "metric" in result.lower()


def test_feedrate_word():
    result = describe_word("F", 500)
    assert "feedrate" in result.lower() or "500" in result


def test_spindle_speed_word():
    result = describe_word("S", 18000)
    assert "spindle" in result.lower() or "18000" in result


def test_all_common_codes_present():
    for code in ["G0", "G1", "G2", "G3", "G20", "G21", "G90", "G91", "M3", "M5"]:
        assert code in GCODE_DESCRIPTIONS, f"{code} missing from glossary"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_commands.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write commands.py**

```python
# ugs_mcp/gcode/commands.py

GCODE_DESCRIPTIONS: dict[str, str] = {
    "G0": "Rapid positioning move (no cutting, fastest speed)",
    "G1": "Linear cutting move at programmed feedrate",
    "G2": "Clockwise arc cutting move",
    "G3": "Counter-clockwise arc cutting move",
    "G4": "Dwell (pause for specified time)",
    "G10": "Set coordinate system offset",
    "G17": "Select XY cutting plane",
    "G18": "Select XZ cutting plane",
    "G19": "Select YZ cutting plane",
    "G20": "Switch units to inches",
    "G21": "Switch units to millimeters (metric)",
    "G28": "Return to machine home position",
    "G28.1": "Set machine home to current position",
    "G38.2": "Probe toward workpiece (alarm if not found)",
    "G38.3": "Probe toward workpiece (no alarm if not found)",
    "G54": "Activate work coordinate system 1 (G54)",
    "G55": "Activate work coordinate system 2 (G55)",
    "G56": "Activate work coordinate system 3 (G56)",
    "G57": "Activate work coordinate system 4 (G57)",
    "G58": "Activate work coordinate system 5 (G58)",
    "G59": "Activate work coordinate system 6 (G59)",
    "G80": "Cancel any active canned cycle",
    "G81": "Simple drilling canned cycle",
    "G82": "Drilling canned cycle with dwell at bottom",
    "G83": "Peck drilling canned cycle",
    "G90": "Switch to absolute positioning mode",
    "G91": "Switch to relative (incremental) positioning mode",
    "G92": "Set position offset at current location",
    "G92.1": "Clear all G92 offsets",
    "G94": "Set feedrate in units per minute",
    "G95": "Set feedrate in units per spindle revolution",
    "M0": "Pause program (operator must press start to continue)",
    "M1": "Optional program pause",
    "M2": "End of program",
    "M3": "Start spindle clockwise (forward)",
    "M4": "Start spindle counter-clockwise (reverse)",
    "M5": "Stop spindle",
    "M6": "Execute tool change",
    "M7": "Turn on mist coolant",
    "M8": "Turn on flood coolant",
    "M9": "Turn off all coolant",
    "M30": "End of program and return to start",
}


def describe_word(letter: str, value: float) -> str:
    """Return plain English description for a G/M/F/S/T/other word."""
    letter = letter.upper()

    if letter in ("G", "M"):
        int_val = int(value)
        frac = value - int_val
        key = f"{letter}{int_val}.{int(round(frac * 10))}" if frac > 0.05 else f"{letter}{int_val}"
        return GCODE_DESCRIPTIONS.get(key, f"Unknown {letter}-code {value}")

    if letter == "F":
        return f"Set feedrate to {value}"
    if letter == "S":
        return f"Set spindle speed to {int(value)} RPM"
    if letter == "T":
        return f"Select tool {int(value)}"
    if letter in ("X", "Y", "Z"):
        return f"Move {letter}-axis to {value}"
    if letter == "N":
        return f"Line number {int(value)}"

    return f"{letter}{value}"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_commands.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gcode/commands.py tests/test_commands.py
git commit -m "feat: G/M-code glossary with plain English descriptions"
```

---

## Task 5: G-code Analyzer - translate

**Files:**
- Create: `ugs_mcp/gcode/analyzer.py` (partial)
- Create: `ugs_mcp/tests/test_analyzer.py` (partial)

- [ ] **Step 1: Write failing tests for translate**

```python
# ugs_mcp/tests/test_analyzer.py
import pytest
from gcode.analyzer import translate, TranslatedLine


def test_translate_returns_list():
    result = translate("G21\nG0 X0 Y0")
    assert isinstance(result, list)
    assert len(result) == 2


def test_translate_includes_line_number():
    result = translate("G21")
    assert result[0]["line_number"] == 1


def test_translate_includes_raw():
    result = translate("G21")
    assert result[0]["raw"] == "G21"


def test_translate_includes_explanation():
    result = translate("G21")
    assert "mm" in result[0]["explanation"].lower() or "metric" in result[0]["explanation"].lower()


def test_translate_includes_context():
    result = translate("G21\nM3 S18000\nG1 X10 F500")
    line = result[2]
    assert "context" in line
    assert "spindle" in line["context"].lower()


def test_translate_max_lines():
    code = "\n".join(f"G0 X{i}" for i in range(20))
    result = translate(code, max_lines=5)
    assert len(result) == 5


def test_translate_skips_blank_lines():
    result = translate("G21\n\nG90")
    assert all(r["raw"] != "" for r in result)


def test_translate_comment_only_line():
    result = translate("(setup section)")
    assert len(result) == 1
    assert "comment" in result[0]["explanation"].lower() or "setup section" in result[0]["explanation"]
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_analyzer.py::test_translate_returns_list -v
```

Expected: ImportError.

- [ ] **Step 3: Write translate in analyzer.py**

```python
# ugs_mcp/gcode/analyzer.py
import math
from typing import List, Dict, Any, Optional

from .parser import load_gcode, GCodeLine
from .state import ModalState, apply_line
from .commands import describe_word


def _describe_line(line: GCodeLine, state_before: ModalState) -> str:
    """Build a plain English explanation for one G-code line."""
    if not line.words and line.comment:
        return f"Comment: {line.comment}"
    if not line.words:
        return "Empty line"

    parts = [describe_word(w.letter, w.value) for w in line.words]
    explanation = "; ".join(parts)
    if line.comment:
        explanation += f" ({line.comment})"
    return explanation


def _state_context(state: ModalState) -> str:
    """Build a brief context string from current modal state."""
    parts = []
    parts.append(f"units={state.units}")
    parts.append(f"mode={state.positioning}")
    if state.spindle_state != "off":
        parts.append(f"spindle {state.spindle_state} at {int(state.spindle_speed)} RPM")
    else:
        parts.append("spindle off")
    if state.feedrate > 0:
        parts.append(f"feed={state.feedrate}")
    return ", ".join(parts)


def translate(file_path_or_code: str, max_lines: Optional[int] = None) -> List[Dict[str, Any]]:
    """Translate G-code to plain English. Returns list of dicts per line."""
    lines = load_gcode(file_path_or_code)
    state = ModalState()
    results = []

    for line in lines:
        if not line.words and not line.comment:
            continue

        explanation = _describe_line(line, state)
        context = _state_context(state)
        results.append({
            "line_number": line.line_number,
            "raw": line.raw,
            "explanation": explanation,
            "context": context,
        })

        state = apply_line(state, line)

        if max_lines and len(results) >= max_lines:
            break

    return results
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_analyzer.py -v -k "translate"
```

Expected: all translate tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gcode/analyzer.py tests/test_analyzer.py
git commit -m "feat: G-code translator - plain English line-by-line output"
```

---

## Task 6: G-code Analyzer - safety_check

**Files:**
- Modify: `ugs_mcp/gcode/analyzer.py`
- Modify: `ugs_mcp/tests/test_analyzer.py`

- [ ] **Step 1: Add failing safety_check tests**

Append to `ugs_mcp/tests/test_analyzer.py`:

```python
from gcode.analyzer import safety_check


def test_safety_check_returns_list():
    result = safety_check("G21\nG90\nM3 S18000\nG1 X10 F500")
    assert isinstance(result, list)


def test_safety_check_no_unit_declaration():
    result = safety_check("G0 X10 Y20")
    codes = [w["code"] for w in result]
    assert "NO_UNIT_DECLARATION" in codes


def test_safety_check_spindle_off_during_cut():
    code = "G21\nG90\nM5\nG1 X10 F500"
    result = safety_check(code)
    codes = [w["code"] for w in result]
    assert "SPINDLE_OFF_DURING_CUT" in codes


def test_safety_check_zero_feedrate_on_cut():
    code = "G21\nG90\nM3 S18000\nG1 X10"
    result = safety_check(code)
    codes = [w["code"] for w in result]
    assert "ZERO_FEEDRATE_ON_CUT" in codes


def test_safety_check_clean_program():
    code = "G21\nG90\nM3 S18000\nG1 X10 F500\nM5"
    result = safety_check(code)
    assert result == []


def test_safety_check_warning_has_required_fields():
    result = safety_check("G0 X10")
    assert len(result) > 0
    w = result[0]
    assert "code" in w
    assert "line_number" in w
    assert "message" in w
    assert "severity" in w
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_analyzer.py -v -k "safety"
```

Expected: ImportError for `safety_check`.

- [ ] **Step 3: Add safety_check to analyzer.py**

Append to `ugs_mcp/gcode/analyzer.py`:

```python
def safety_check(file_path_or_code: str) -> List[Dict[str, Any]]:
    """Check G-code for safety issues. Returns list of warning dicts."""
    lines = load_gcode(file_path_or_code)
    state = ModalState()
    warnings = []
    unit_declared = False
    has_motion = False

    for line in lines:
        if not line.words:
            state = apply_line(state, line)
            continue

        words = {w.letter: w.value for w in line.words}
        g = words.get("G")
        m = words.get("M")

        if g in (20, 21):
            unit_declared = True

        is_cut_move = g in (1, 2, 3)
        is_any_move = g in (0, 1, 2, 3)

        if is_any_move:
            has_motion = True

        if is_any_move and not unit_declared:
            warnings.append({
                "code": "NO_UNIT_DECLARATION",
                "line_number": line.line_number,
                "message": "Motion command found before G20/G21 unit declaration. Units are ambiguous.",
                "severity": "WARNING",
            })
            unit_declared = True  # Only warn once

        if is_cut_move and state.spindle_state == "off":
            warnings.append({
                "code": "SPINDLE_OFF_DURING_CUT",
                "line_number": line.line_number,
                "message": f"Cut move (G{int(g)}) while spindle is off (M5). This will rub, not cut.",
                "severity": "DANGER",
            })

        if is_cut_move and state.feedrate == 0 and "F" not in words:
            warnings.append({
                "code": "ZERO_FEEDRATE_ON_CUT",
                "line_number": line.line_number,
                "message": f"Cut move (G{int(g)}) with feedrate=0. Machine may stall or behave unexpectedly.",
                "severity": "DANGER",
            })

        state = apply_line(state, line)

    return warnings
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_analyzer.py -v -k "safety"
```

Expected: all safety tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gcode/analyzer.py tests/test_analyzer.py
git commit -m "feat: G-code safety checker - spindle, feedrate, unit warnings"
```

---

## Task 7: G-code Analyzer - estimate_time and list_tools

**Files:**
- Modify: `ugs_mcp/gcode/analyzer.py`
- Modify: `ugs_mcp/tests/test_analyzer.py`

- [ ] **Step 1: Add failing tests**

Append to `ugs_mcp/tests/test_analyzer.py`:

```python
from gcode.analyzer import estimate_time, list_tools


def test_estimate_time_returns_string():
    result = estimate_time("G21\nG1 X100 F1000")
    assert isinstance(result, str)
    assert ":" in result


def test_estimate_time_simple_move():
    # 100mm at 1000mm/min = 0.1 min = 6 seconds
    result = estimate_time("G21\nG90\nG1 X100 F1000")
    assert result == "0:00:06"


def test_estimate_time_rapid_uses_default_speed():
    # 1000mm rapid at 5000mm/min = 0.2 min = 12 seconds
    result = estimate_time("G21\nG90\nG0 X1000", rapid_speed=5000.0)
    assert result == "0:00:12"


def test_estimate_time_empty_program():
    result = estimate_time("G21\nG90")
    assert result == "0:00:00"


def test_list_tools_returns_list():
    result = list_tools("G21\nT1 M6\nG1 X10 F500")
    assert isinstance(result, list)


def test_list_tools_finds_tool():
    result = list_tools("G21\nT1 M6\nG1 X10 F500\nT2 M6")
    tool_numbers = [t["tool"] for t in result]
    assert 1 in tool_numbers
    assert 2 in tool_numbers


def test_list_tools_records_first_use_line():
    result = list_tools("G21\nT3 M6")
    assert result[0]["first_line"] == 2


def test_list_tools_empty_program():
    result = list_tools("G21\nG0 X0")
    assert result == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_analyzer.py -v -k "time or tools"
```

Expected: ImportError for new functions.

- [ ] **Step 3: Add estimate_time and list_tools to analyzer.py**

Append to `ugs_mcp/gcode/analyzer.py`:

```python
def estimate_time(file_path_or_code: str, rapid_speed: float = 5000.0) -> str:
    """Estimate total machining time. Returns HH:MM:SS string."""
    lines = load_gcode(file_path_or_code)
    state = ModalState()
    total_seconds = 0.0

    for line in lines:
        words = {w.letter: w.value for w in line.words}
        g = words.get("G")

        if g in (0, 1, 2, 3):
            prev = state.position.copy()
            state = apply_line(state, line)
            now = state.position

            dx = now.get("X", 0) - prev.get("X", 0)
            dy = now.get("Y", 0) - prev.get("Y", 0)
            dz = now.get("Z", 0) - prev.get("Z", 0)
            distance = math.sqrt(dx**2 + dy**2 + dz**2)

            if distance == 0:
                continue

            if g == 0:
                speed = rapid_speed
            else:
                speed = state.feedrate if state.feedrate > 0 else rapid_speed

            total_seconds += (distance / speed) * 60.0
        else:
            state = apply_line(state, line)

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def list_tools(file_path_or_code: str) -> List[Dict[str, Any]]:
    """List all tools referenced in G-code. Returns list of dicts."""
    lines = load_gcode(file_path_or_code)
    tools: Dict[int, Dict] = {}

    for line in lines:
        words = {w.letter: w.value for w in line.words}
        if "T" in words:
            t = int(words["T"])
            if t not in tools:
                tools[t] = {"tool": t, "first_line": line.line_number, "use_count": 0}
            tools[t]["use_count"] += 1

    return sorted(tools.values(), key=lambda x: x["tool"])
```

- [ ] **Step 4: Run all analyzer tests**

```bash
cd ugs_mcp
pytest tests/test_analyzer.py -v
```

Expected: all analyzer tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gcode/analyzer.py tests/test_analyzer.py
git commit -m "feat: cycle time estimator and tool inventory analyzer"
```

---

## Task 8: UGS REST Client

**Files:**
- Create: `ugs_mcp/ugs_client.py`
- Create: `ugs_mcp/tests/test_ugs_client.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_ugs_client.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from ugs_client import send_gcode, get_status, is_pendant_reachable


@pytest.mark.asyncio
async def test_send_gcode_calls_correct_endpoint():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"

    with patch("ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await send_gcode("G21")

    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert "sendGcode" in call_args[0][0]
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_send_gcode_returns_error_on_failure():
    with patch("ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_class.return_value = mock_client

        result = await send_gcode("G21")

    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_get_status_parses_response():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={
        "machineCoord": {"x": 0.0, "y": 0.0, "z": 0.0},
        "workCoord": {"x": 0.0, "y": 0.0, "z": 0.0},
        "state": "Idle",
        "feedSpeed": 0,
        "spindleSpeed": 0,
    })

    with patch("ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await get_status()

    assert result["state"] == "Idle"
    assert "machine_position" in result
    assert "work_position" in result


@pytest.mark.asyncio
async def test_is_pendant_reachable_true():
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await is_pendant_reachable()

    assert result is True


@pytest.mark.asyncio
async def test_is_pendant_reachable_false_on_error():
    with patch("ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_class.return_value = mock_client

        result = await is_pendant_reachable()

    assert result is False
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_ugs_client.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write ugs_client.py**

```python
# ugs_mcp/ugs_client.py
from typing import Any, Dict
import httpx
from config import UGS_BASE_URL


async def send_gcode(command: str) -> Dict[str, Any]:
    """Send a G-code command string to the UGS pendant API."""
    url = f"{UGS_BASE_URL}/sendGcode/"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params={"gCode": command})
            return {"status": "ok", "code": response.status_code, "body": response.text}
    except httpx.ConnectError as e:
        return {"status": "error", "message": f"Cannot reach UGS pendant at {UGS_BASE_URL}: {e}"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "UGS pendant request timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_status() -> Dict[str, Any]:
    """Get current machine status from UGS pendant."""
    url = f"{UGS_BASE_URL}/api/v1/status/getStatus"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            data = response.json()
            return {
                "status": "ok",
                "state": data.get("state", "Unknown"),
                "machine_position": data.get("machineCoord", {}),
                "work_position": data.get("workCoord", {}),
                "feed_speed": data.get("feedSpeed", 0),
                "spindle_speed": data.get("spindleSpeed", 0),
            }
    except httpx.ConnectError as e:
        return {"status": "error", "message": f"Cannot reach UGS pendant: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def is_pendant_reachable() -> bool:
    """Return True if UGS pendant API is reachable."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{UGS_BASE_URL}/api/v1/status/getStatus")
            return response.status_code < 500
    except Exception:
        return False
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_ugs_client.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ugs_client.py tests/test_ugs_client.py
git commit -m "feat: UGS pendant REST client with error handling"
```

---

## Task 9: Connection and Status Tools

**Files:**
- Create: `ugs_mcp/tools/connection.py`
- Create: `ugs_mcp/tools/status.py`
- Create: `ugs_mcp/tests/test_connection.py`
- Create: `ugs_mcp/tests/test_status.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_connection.py
import pytest
from unittest.mock import AsyncMock, patch
from tools.connection import tool_troubleshoot_connection


@pytest.mark.asyncio
async def test_troubleshoot_reports_pendant_unreachable():
    with patch("tools.connection.is_pendant_reachable", new=AsyncMock(return_value=False)):
        with patch("tools.connection.serial.tools.list_ports.comports", return_value=[]):
            result = await tool_troubleshoot_connection()
    assert "pendant" in result.lower()
    assert "not reachable" in result.lower() or "unreachable" in result.lower() or "cannot" in result.lower()


@pytest.mark.asyncio
async def test_troubleshoot_lists_serial_ports():
    mock_port = type("Port", (), {"device": "/dev/tty.usbserial-1410", "description": "USB Serial"})()

    with patch("tools.connection.is_pendant_reachable", new=AsyncMock(return_value=True)):
        with patch("tools.connection.serial.tools.list_ports.comports", return_value=[mock_port]):
            with patch("tools.connection.get_status", new=AsyncMock(return_value={"status": "ok", "state": "Idle", "machine_position": {}, "work_position": {}, "feed_speed": 0, "spindle_speed": 0})):
                result = await tool_troubleshoot_connection()
    assert "/dev/tty.usbserial-1410" in result
```

```python
# ugs_mcp/tests/test_status.py
import pytest
from unittest.mock import AsyncMock, patch
from tools.status import tool_get_status


@pytest.mark.asyncio
async def test_get_status_formats_output():
    mock_status = {
        "status": "ok",
        "state": "Idle",
        "machine_position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "work_position": {"x": 10.0, "y": 5.0, "z": 0.0},
        "feed_speed": 500,
        "spindle_speed": 18000,
    }
    with patch("tools.status.get_status", new=AsyncMock(return_value=mock_status)):
        result = await tool_get_status()
    assert "Idle" in result
    assert "18000" in result


@pytest.mark.asyncio
async def test_get_status_handles_error():
    with patch("tools.status.get_status", new=AsyncMock(return_value={"status": "error", "message": "timeout"})):
        result = await tool_get_status()
    assert "error" in result.lower() or "timeout" in result.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_connection.py tests/test_status.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write connection.py**

```python
# ugs_mcp/tools/connection.py
import serial.tools.list_ports
from ugs_client import get_status, is_pendant_reachable
from config import UGS_BASE_URL, WARNING_MESSAGES


async def tool_troubleshoot_connection() -> str:
    """Diagnose UGS connection issues and suggest fixes."""
    lines = [WARNING_MESSAGES["connection_issue"], ""]
    lines.append(f"UGS Pendant URL: {UGS_BASE_URL}")
    lines.append("")

    reachable = await is_pendant_reachable()
    if reachable:
        lines.append("Pendant status: REACHABLE")
        status = await get_status()
        if status["status"] == "ok":
            lines.append(f"Machine state: {status['state']}")
        else:
            lines.append(f"Status error: {status['message']}")
    else:
        lines.append("Pendant status: NOT REACHABLE")
        lines.append("")
        lines.append("Possible fixes:")
        lines.append("  1. Open UGS and enable the web pendant (Tools > Options > Pendant)")
        lines.append("  2. Verify UGS is running on this machine")
        lines.append(f"  3. Check that nothing else is using port {UGS_BASE_URL.split(':')[-1]}")

    lines.append("")
    lines.append("Available serial ports:")
    ports = list(serial.tools.list_ports.comports())
    if ports:
        for p in ports:
            lines.append(f"  {p.device} - {p.description}")
    else:
        lines.append("  (none found)")
        lines.append("  -> Is the CNC controller plugged in? Try a different USB port.")

    return "\n".join(lines)


async def tool_connect(port: str, baud_rate: int = 115200, firmware: str = "GRBL") -> str:
    """Connect UGS to CNC machine via serial port."""
    from ugs_client import send_gcode
    result = await send_gcode(f"CONNECT:{port}:{baud_rate}:{firmware}")
    if result["status"] == "error":
        return f"{WARNING_MESSAGES['connection_issue']}\n\nFailed to connect: {result['message']}"
    return f"Connection initiated to {port} at {baud_rate} baud ({firmware} firmware).\nCheck UGS for connection status."


async def tool_disconnect() -> str:
    """Disconnect UGS from the CNC machine."""
    from ugs_client import send_gcode
    result = await send_gcode("DISCONNECT")
    if result["status"] == "error":
        return f"Disconnect failed: {result['message']}"
    return "Disconnected from CNC machine."
```

- [ ] **Step 4: Write status.py**

```python
# ugs_mcp/tools/status.py
from ugs_client import get_status


async def tool_get_status() -> str:
    """Get current machine state from UGS."""
    result = await get_status()

    if result["status"] == "error":
        return f"Error getting status: {result['message']}"

    mp = result.get("machine_position", {})
    wp = result.get("work_position", {})

    lines = [
        f"Machine State: {result['state']}",
        "",
        "Machine Position:",
        f"  X={mp.get('x', 0):.3f}  Y={mp.get('y', 0):.3f}  Z={mp.get('z', 0):.3f}",
        "",
        "Work Position (G54):",
        f"  X={wp.get('x', 0):.3f}  Y={wp.get('y', 0):.3f}  Z={wp.get('z', 0):.3f}",
        "",
        f"Feed Speed: {result.get('feed_speed', 0)} mm/min",
        f"Spindle Speed: {result.get('spindle_speed', 0)} RPM",
    ]
    return "\n".join(lines)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_connection.py tests/test_status.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/connection.py tools/status.py tests/test_connection.py tests/test_status.py
git commit -m "feat: connection troubleshooter and machine status tool"
```

---

## Task 10: Motion Tools

**Files:**
- Create: `ugs_mcp/tools/motion.py`
- Create: `ugs_mcp/tests/test_motion.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_motion.py
import pytest
from unittest.mock import AsyncMock, patch
from tools.motion import tool_jog, tool_home, tool_set_work_zero, tool_return_to_zero


@pytest.mark.asyncio
async def test_jog_preview_returns_banner():
    with patch("tools.motion.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Idle",
        "machine_position": {"x": 0, "y": 0, "z": 0},
        "work_position": {"x": 0, "y": 0, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        result = await tool_jog("X", 10.0, 500, confirmed=False)
    assert "WARNING" in result
    assert "MOVE" in result


@pytest.mark.asyncio
async def test_jog_preview_does_not_send_gcode():
    send_mock = AsyncMock()
    with patch("tools.motion.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Idle",
        "machine_position": {"x": 0, "y": 0, "z": 0},
        "work_position": {"x": 0, "y": 0, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        with patch("tools.motion.send_gcode", new=send_mock):
            await tool_jog("X", 10.0, 500, confirmed=False)
    send_mock.assert_not_called()


@pytest.mark.asyncio
async def test_jog_confirmed_sends_gcode():
    send_mock = AsyncMock(return_value={"status": "ok"})
    with patch("tools.motion.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Idle",
        "machine_position": {"x": 0, "y": 0, "z": 0},
        "work_position": {"x": 0, "y": 0, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        with patch("tools.motion.send_gcode", new=send_mock):
            await tool_jog("X", 10.0, 500, confirmed=True)
    send_mock.assert_called_once()


@pytest.mark.asyncio
async def test_jog_blocked_in_alarm_state():
    with patch("tools.motion.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Alarm",
        "machine_position": {"x": 0, "y": 0, "z": 0},
        "work_position": {"x": 0, "y": 0, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        result = await tool_jog("X", 10.0, 500, confirmed=True)
    assert "alarm" in result.lower()
    assert "cannot" in result.lower() or "blocked" in result.lower() or "unlock" in result.lower()


@pytest.mark.asyncio
async def test_home_preview_returns_danger_banner():
    with patch("tools.motion.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Idle",
        "machine_position": {"x": 0, "y": 0, "z": 0},
        "work_position": {"x": 0, "y": 0, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        result = await tool_home(confirmed=False)
    assert "DANGER" in result
    assert "LIMIT" in result or "SPEED" in result


@pytest.mark.asyncio
async def test_set_work_zero_preview_returns_caution():
    with patch("tools.motion.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Idle",
        "machine_position": {"x": 10, "y": 20, "z": 0},
        "work_position": {"x": 10, "y": 20, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        result = await tool_set_work_zero(["X", "Y", "Z"], confirmed=False)
    assert "CAUTION" in result
    assert "ZERO" in result or "COORDINATE" in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_motion.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write motion.py**

```python
# ugs_mcp/tools/motion.py
from typing import List
from ugs_client import send_gcode, get_status
from config import WARNING_MESSAGES


def _preview_footer() -> str:
    return "\n\nThis is a PREVIEW. Call again with confirmed=True to execute."


async def _check_alarm_state() -> str | None:
    """Return error message if machine is in Alarm state, else None."""
    status = await get_status()
    if status.get("state", "").lower() == "alarm":
        return (
            "CANNOT JOG: Machine is in ALARM state.\n"
            "Run $X to unlock the alarm, then try again.\n"
            "Check UGS for the alarm reason before unlocking."
        )
    return None


async def tool_jog(axis: str, distance_mm: float, feedrate: float, confirmed: bool = False) -> str:
    """
    Jog a single axis by the given distance.
    ALWAYS call with confirmed=False first to show the user a preview.
    Only call with confirmed=True after explicit user acknowledgment.
    """
    banner = WARNING_MESSAGES["jog"]
    axis = axis.upper()
    status = await get_status()

    if confirmed:
        alarm = await _check_alarm_state()
        if alarm:
            return alarm
        cmd = f"$J=G91 {axis}{distance_mm} F{feedrate}"
        result = await send_gcode(cmd)
        if result["status"] == "error":
            return f"{banner}\n\nJog failed: {result['message']}"
        return f"{banner}\n\nJogging {axis} by {distance_mm}mm at {feedrate}mm/min. Command sent."

    mp = status.get("machine_position", {})
    lines = [
        banner,
        "",
        "PREVIEW - no movement yet:",
        f"  Axis:      {axis}",
        f"  Distance:  {distance_mm}mm",
        f"  Feedrate:  {feedrate}mm/min",
        f"  Current machine pos: X={mp.get('x',0):.3f} Y={mp.get('y',0):.3f} Z={mp.get('z',0):.3f}",
    ]
    if axis in ("X", "Y", "Z"):
        new_val = mp.get(axis.lower(), 0) + distance_mm
        lines.append(f"  New {axis} position will be approx: {new_val:.3f}mm")
    lines.append(_preview_footer())
    return "\n".join(lines)


async def tool_home(confirmed: bool = False) -> str:
    """
    Run the GRBL homing cycle ($H).
    ALWAYS call with confirmed=False first to show the user a preview.
    Only call with confirmed=True after explicit user acknowledgment.
    """
    banner = WARNING_MESSAGES["home"]

    if confirmed:
        result = await send_gcode("$H")
        if result["status"] == "error":
            return f"{banner}\n\nHoming failed: {result['message']}"
        return f"{banner}\n\nHoming cycle started. All axes will move toward limit switches."

    lines = [
        banner,
        "",
        "PREVIEW - no movement yet:",
        "  Command: $H (GRBL homing cycle)",
        "  All axes will move toward their limit switches at maximum speed.",
        "  Make sure nothing is in the machine's path before confirming.",
        _preview_footer(),
    ]
    return "\n".join(lines)


async def tool_set_work_zero(axes: List[str] = None, confirmed: bool = False) -> str:
    """
    Set G54 work zero at the current machine position.
    ALWAYS call with confirmed=False first to show the user a preview.
    Only call with confirmed=True after explicit user acknowledgment.
    """
    if axes is None:
        axes = ["X", "Y", "Z"]
    banner = WARNING_MESSAGES["set_work_zero"]
    status = await get_status()
    mp = status.get("machine_position", {})
    axes_upper = [a.upper() for a in axes]

    if confirmed:
        axis_str = "".join(f"{a}0" for a in axes_upper)
        result = await send_gcode(f"G10 L20 P1 {axis_str}")
        if result["status"] == "error":
            return f"{banner}\n\nSet zero failed: {result['message']}"
        return f"{banner}\n\nWork zero set for axes {axes_upper} at current position."

    lines = [
        banner,
        "",
        "PREVIEW - no changes yet:",
        f"  Axes to zero: {axes_upper}",
        "  Current machine position:",
        f"    X={mp.get('x',0):.3f}  Y={mp.get('y',0):.3f}  Z={mp.get('z',0):.3f}",
        "  This will set the G54 work origin to the above values for the selected axes.",
        _preview_footer(),
    ]
    return "\n".join(lines)


async def tool_return_to_zero(confirmed: bool = False) -> str:
    """
    Rapid to G54 work zero (X0 Y0 Z0).
    ALWAYS call with confirmed=False first to show the user a preview.
    Only call with confirmed=True after explicit user acknowledgment.
    """
    banner = WARNING_MESSAGES["return_to_zero"]

    if confirmed:
        alarm = await _check_alarm_state()
        if alarm:
            return alarm
        result = await send_gcode("RETURN_TO_ZERO")
        if result["status"] == "error":
            return f"{banner}\n\nReturn to zero failed: {result['message']}"
        return f"{banner}\n\nMoving to G54 work zero (X0 Y0 Z0)."

    lines = [
        banner,
        "",
        "PREVIEW - no movement yet:",
        "  Will rapid (G0) to X=0 Y=0 Z=0 in the G54 work coordinate system.",
        "  Make sure the path is clear before confirming.",
        _preview_footer(),
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_motion.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/motion.py tests/test_motion.py
git commit -m "feat: motion tools (jog, home, set-zero, return-to-zero) with preview/confirm safety"
```

---

## Task 11: Job Tools

**Files:**
- Create: `ugs_mcp/tools/job.py`
- Create: `ugs_mcp/tests/test_job.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_job.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from tools.job import tool_run_file, tool_cancel_job, tool_pause_job, tool_get_job_status


@pytest.mark.asyncio
async def test_run_file_preview_returns_warning(tmp_path):
    f = tmp_path / "test.nc"
    f.write_text("G21\nG90\nM3 S18000\nG1 X10 F500\nM5\n")
    with patch("tools.job.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Idle",
        "machine_position": {"x": 0, "y": 0, "z": 0},
        "work_position": {"x": 0, "y": 0, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        result = await tool_run_file(str(f), confirmed=False)
    assert "WARNING" in result
    assert "SPINDLE" in result or "CUT" in result


@pytest.mark.asyncio
async def test_run_file_preview_includes_safety_check(tmp_path):
    f = tmp_path / "unsafe.nc"
    f.write_text("G0 X10\nM5\nG1 X20 F500\n")
    with patch("tools.job.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Idle",
        "machine_position": {"x": 0, "y": 0, "z": 0},
        "work_position": {"x": 0, "y": 0, "z": 0},
        "feed_speed": 0, "spindle_speed": 0
    })):
        result = await tool_run_file(str(f), confirmed=False)
    assert "SPINDLE_OFF_DURING_CUT" in result or "spindle" in result.lower()


@pytest.mark.asyncio
async def test_run_file_missing_file():
    result = await tool_run_file("/nonexistent/path.nc", confirmed=False)
    assert "not found" in result.lower() or "does not exist" in result.lower()


@pytest.mark.asyncio
async def test_cancel_job_preview_returns_caution():
    with patch("tools.job.get_status", new=AsyncMock(return_value={
        "status": "ok", "state": "Run",
        "machine_position": {"x": 5, "y": 5, "z": 0},
        "work_position": {"x": 5, "y": 5, "z": 0},
        "feed_speed": 500, "spindle_speed": 18000
    })):
        result = await tool_cancel_job(confirmed=False)
    assert "CAUTION" in result
    assert "MID-CUT" in result or "mark" in result.lower()


@pytest.mark.asyncio
async def test_pause_job_sends_command():
    send_mock = AsyncMock(return_value={"status": "ok"})
    with patch("tools.job.send_gcode", new=send_mock):
        result = await tool_pause_job()
    send_mock.assert_called_once()
    assert "pause" in result.lower() or "paused" in result.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_job.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write job.py**

```python
# ugs_mcp/tools/job.py
from pathlib import Path
from ugs_client import send_gcode, get_status
from config import WARNING_MESSAGES
from gcode.analyzer import safety_check


def _preview_footer() -> str:
    return "\n\nThis is a PREVIEW. Call again with confirmed=True to execute."


async def tool_run_file(file_path: str, confirmed: bool = False) -> str:
    """
    Stream a G-code file to the CNC machine.
    ALWAYS call with confirmed=False first - this runs the safety checker and shows a preview.
    Only call with confirmed=True after explicit user acknowledgment.
    """
    banner = WARNING_MESSAGES["run_file"]
    p = Path(file_path)

    if not p.exists():
        return f"File not found: {file_path}"

    warnings = safety_check(file_path)
    status = await get_status()

    if confirmed:
        result = await send_gcode(f"SEND_FILE:{file_path}")
        if result["status"] == "error":
            return f"{banner}\n\nFailed to start job: {result['message']}"
        return f"{banner}\n\nJob started: {p.name}"

    lines = [
        banner,
        "",
        f"File: {file_path}",
        f"Machine state: {status.get('state', 'Unknown')}",
        "",
    ]

    if warnings:
        lines.append(f"SAFETY CHECK - {len(warnings)} issue(s) found:")
        for w in warnings:
            lines.append(f"  [{w['severity']}] Line {w['line_number']}: {w['code']} - {w['message']}")
        lines.append("")
        lines.append("Review warnings above before confirming.")
    else:
        lines.append("Safety check: PASSED (no issues found)")

    lines.append(_preview_footer())
    return "\n".join(lines)


async def tool_pause_job() -> str:
    """Pause the currently running G-code job."""
    result = await send_gcode("!")
    if result["status"] == "error":
        return f"Pause failed: {result['message']}"
    return "Job paused. Send ~ (feed hold release) or resume from UGS to continue."


async def tool_cancel_job(confirmed: bool = False) -> str:
    """
    Cancel the currently running G-code job.
    ALWAYS call with confirmed=False first.
    Only call with confirmed=True after explicit user acknowledgment.
    """
    banner = WARNING_MESSAGES["cancel_job"]

    if confirmed:
        result = await send_gcode("CANCEL_FILE")
        if result["status"] == "error":
            return f"{banner}\n\nCancel failed: {result['message']}"
        return f"{banner}\n\nJob cancelled. Machine stopped."

    status = await get_status()
    mp = status.get("machine_position", {})
    lines = [
        banner,
        "",
        "PREVIEW - job is still running:",
        f"  Current machine position: X={mp.get('x',0):.3f} Y={mp.get('y',0):.3f} Z={mp.get('z',0):.3f}",
        "  Cancelling will stop the cutter mid-path and may leave a mark on your part.",
        "  The spindle will NOT stop automatically - run M5 afterward if needed.",
        _preview_footer(),
    ]
    return "\n".join(lines)


async def tool_get_job_status() -> str:
    """Get the current job progress."""
    status = await get_status()
    if status["status"] == "error":
        return f"Error: {status['message']}"
    return (
        f"Machine state: {status.get('state', 'Unknown')}\n"
        f"Feed speed: {status.get('feed_speed', 0)} mm/min\n"
        f"Spindle speed: {status.get('spindle_speed', 0)} RPM\n"
        "(For detailed job progress percentage, check UGS directly - not available via pendant API)"
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_job.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/job.py tests/test_job.py
git commit -m "feat: job tools (run, pause, cancel, status) with safety check integration"
```

---

## Task 12: Inspector and Macro MCP Tools

**Files:**
- Create: `ugs_mcp/tools/inspector.py`
- Create: `ugs_mcp/tests/test_inspector.py`

- [ ] **Step 1: Write failing tests**

```python
# ugs_mcp/tests/test_inspector.py
import pytest
from pathlib import Path
from tools.inspector import (
    tool_gcode_translate,
    tool_gcode_safety_check,
    tool_gcode_estimate_time,
    tool_gcode_list_tools,
    tool_gcode_save_macro,
    tool_gcode_list_macros,
    tool_gcode_run_macro,
)
from unittest.mock import AsyncMock, patch


def test_translate_tool_returns_string():
    result = tool_gcode_translate("G21\nG0 X0 Y0")
    assert isinstance(result, str)
    assert "G21" in result


def test_translate_tool_shows_explanation():
    result = tool_gcode_translate("G21")
    assert "mm" in result.lower() or "metric" in result.lower()


def test_safety_check_tool_returns_string():
    result = tool_gcode_safety_check("G21\nG90\nM3 S18000\nG1 X10 F500\nM5")
    assert isinstance(result, str)
    assert "passed" in result.lower() or "issue" in result.lower()


def test_safety_check_reports_warnings():
    result = tool_gcode_safety_check("G0 X10")
    assert "NO_UNIT_DECLARATION" in result or "unit" in result.lower()


def test_estimate_time_tool_returns_string():
    result = tool_gcode_estimate_time("G21\nG90\nG1 X100 F1000")
    assert isinstance(result, str)
    assert ":" in result


def test_list_tools_tool_returns_string():
    result = tool_gcode_list_tools("G21\nT1 M6\nG1 X10 F500")
    assert isinstance(result, str)
    assert "1" in result


def test_save_macro_creates_file(tmp_path):
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = tool_gcode_save_macro("probe_z", "G21\nG91\nG38.2 Z-20 F50\nG92 Z0", "Probe Z surface")
    assert "saved" in result.lower() or "probe_z" in result.lower()
    assert (tmp_path / "probe_z.nc").exists()


def test_list_macros_empty(tmp_path):
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = tool_gcode_list_macros()
    assert "no macros" in result.lower() or result.strip() == "" or "0" in result


def test_list_macros_shows_saved(tmp_path):
    (tmp_path / "probe_z.nc").write_text("G21\nG38.2 Z-20 F50")
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = tool_gcode_list_macros()
    assert "probe_z" in result


@pytest.mark.asyncio
async def test_run_macro_preview(tmp_path):
    (tmp_path / "probe_z.nc").write_text("G21\nG38.2 Z-20 F50")
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = await tool_gcode_run_macro("probe_z", confirmed=False)
    assert "HEADS UP" in result or "MACRO" in result


@pytest.mark.asyncio
async def test_run_macro_missing():
    result = await tool_gcode_run_macro("nonexistent", confirmed=False)
    assert "not found" in result.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ugs_mcp
pytest tests/test_inspector.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write inspector.py**

```python
# ugs_mcp/tools/inspector.py
import json
from pathlib import Path
from typing import Optional, List

from config import MACROS_DIR, WARNING_MESSAGES
from gcode.analyzer import translate, safety_check, estimate_time, list_tools
from ugs_client import send_gcode


def tool_gcode_translate(file_path_or_code: str, max_lines: Optional[int] = None) -> str:
    """Translate G-code to plain English, line by line."""
    results = translate(file_path_or_code, max_lines=max_lines)
    if not results:
        return "No G-code lines found."
    lines = []
    for r in results:
        lines.append(f"Line {r['line_number']}: {r['raw']}")
        lines.append(f"  -> {r['explanation']}")
        lines.append(f"     [{r['context']}]")
    return "\n".join(lines)


def tool_gcode_safety_check(file_path_or_code: str) -> str:
    """Check G-code for safety issues."""
    warnings = safety_check(file_path_or_code)
    if not warnings:
        return "Safety check PASSED - no issues found."
    lines = [f"Safety check found {len(warnings)} issue(s):\n"]
    for w in warnings:
        lines.append(f"  [{w['severity']}] Line {w['line_number']}: {w['code']}")
        lines.append(f"    {w['message']}")
    return "\n".join(lines)


def tool_gcode_estimate_time(file_path_or_code: str) -> str:
    """Estimate G-code job cycle time."""
    from config import RAPID_SPEED_MM_MIN
    t = estimate_time(file_path_or_code, rapid_speed=RAPID_SPEED_MM_MIN)
    return f"Estimated cycle time: {t}"


def tool_gcode_list_tools(file_path_or_code: str) -> str:
    """List all tools referenced in a G-code file."""
    tools = list_tools(file_path_or_code)
    if not tools:
        return "No tool changes (T-word references) found in this G-code."
    lines = ["Tools required:"]
    for t in tools:
        lines.append(f"  T{t['tool']:02d} - first used on line {t['first_line']}, used {t['use_count']} time(s)")
    return "\n".join(lines)


def tool_gcode_save_macro(name: str, gcode_content: str, description: str = "") -> str:
    """Validate G-code, save as a named macro, and register in UGS Platform if available."""
    MACROS_DIR.mkdir(parents=True, exist_ok=True)
    warnings = safety_check(gcode_content)
    warn_text = ""
    if warnings:
        warn_lines = [f"  [{w['severity']}] Line {w['line_number']}: {w['message']}" for w in warnings]
        warn_text = "\nSafety warnings:\n" + "\n".join(warn_lines)

    macro_path = MACROS_DIR / f"{name}.nc"
    header = f"; Macro: {name}\n"
    if description:
        header += f"; Description: {description}\n"
    macro_path.write_text(header + gcode_content)

    lines = [f"Macro '{name}' saved to {macro_path}"]
    if description:
        lines.append(f"Description: {description}")
    if warn_text:
        lines.append(warn_text)
        lines.append("\nReview warnings before running this macro.")
    else:
        lines.append("Safety check: PASSED")
    return "\n".join(lines)


def tool_gcode_list_macros() -> str:
    """List all saved macros."""
    if not MACROS_DIR.exists():
        return "No macros directory found. Save a macro first."
    macros = sorted(MACROS_DIR.glob("*.nc"))
    if not macros:
        return "No macros saved yet."
    lines = ["Saved macros:"]
    for m in macros:
        description = ""
        for line in m.read_text().splitlines():
            if line.startswith("; Description:"):
                description = line.replace("; Description:", "").strip()
                break
        lines.append(f"  {m.stem}.nc" + (f" - {description}" if description else ""))
    return "\n".join(lines)


async def tool_gcode_run_macro(name: str, confirmed: bool = False) -> str:
    """
    Run a saved macro by name.
    ALWAYS call with confirmed=False first to show a preview.
    Only call with confirmed=True after explicit user acknowledgment.
    """
    banner = WARNING_MESSAGES["run_macro"]
    macro_path = MACROS_DIR / f"{name}.nc"

    if not macro_path.exists():
        return f"Macro '{name}' not found. Run tool_gcode_list_macros to see available macros."

    content = macro_path.read_text()
    warnings = safety_check(content)

    if confirmed:
        result = await send_gcode(f"SEND_FILE:{macro_path}")
        if result["status"] == "error":
            return f"{banner}\n\nFailed to run macro: {result['message']}"
        return f"{banner}\n\nMacro '{name}' started."

    lines = [
        banner,
        "",
        f"Macro: {name}",
        f"File: {macro_path}",
        "",
        "G-code preview:",
    ]
    for line in content.splitlines()[:10]:
        if not line.startswith(";"):
            lines.append(f"  {line}")
    if content.count("\n") > 10:
        lines.append("  ...")

    if warnings:
        lines.append(f"\nSafety issues: {len(warnings)}")
        for w in warnings:
            lines.append(f"  [{w['severity']}] {w['message']}")
    else:
        lines.append("\nSafety check: PASSED")

    lines.append(
        "\nThis is a PREVIEW. Call again with confirmed=True to run the macro."
    )
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ugs_mcp
pytest tests/test_inspector.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/inspector.py tests/test_inspector.py
git commit -m "feat: inspector and macro tools (translate, safety, time, tools, macros)"
```

---

## Task 13: FastMCP Server Assembly

**Files:**
- Create: `ugs_mcp/server.py`

No unit tests for server.py - verified by running the server and checking `/mcp` in Claude Code.

- [ ] **Step 1: Write server.py**

```python
# ugs_mcp/server.py
import asyncio
from mcp.server.fastmcp import FastMCP

from tools.connection import tool_connect, tool_disconnect, tool_troubleshoot_connection
from tools.status import tool_get_status
from tools.motion import tool_jog, tool_home, tool_set_work_zero, tool_return_to_zero
from tools.job import tool_run_file, tool_pause_job, tool_cancel_job, tool_get_job_status
from tools.inspector import (
    tool_gcode_translate,
    tool_gcode_safety_check,
    tool_gcode_estimate_time,
    tool_gcode_list_tools,
    tool_gcode_save_macro,
    tool_gcode_list_macros,
    tool_gcode_run_macro,
)

mcp = FastMCP("UGS CNC Controller")


@mcp.tool()
async def ugs_connect(port: str, baud_rate: int = 115200, firmware: str = "GRBL") -> str:
    """Connect UGS to the CNC machine via serial port."""
    return await tool_connect(port, baud_rate, firmware)


@mcp.tool()
async def ugs_disconnect() -> str:
    """Disconnect UGS from the CNC machine."""
    return await tool_disconnect()


@mcp.tool()
async def ugs_troubleshoot_connection() -> str:
    """Diagnose connection issues: lists serial ports, checks pendant reachability, suggests fixes."""
    return await tool_troubleshoot_connection()


@mcp.tool()
async def ugs_get_status() -> str:
    """Get current machine state: position, status (Idle/Run/Alarm), feed rate, spindle speed."""
    return await tool_get_status()


@mcp.tool()
async def ugs_jog(axis: str, distance_mm: float, feedrate: float, confirmed: bool = False) -> str:
    """
    Jog a single axis (X, Y, or Z) by distance_mm at feedrate mm/min.
    ALWAYS call with confirmed=False first. Show the preview to the user.
    Only pass confirmed=True after the user has explicitly said they understand the machine will move.
    """
    return await tool_jog(axis, distance_mm, feedrate, confirmed)


@mcp.tool()
async def ugs_home(confirmed: bool = False) -> str:
    """
    Run the GRBL homing cycle ($H). All axes will move toward limit switches at full speed.
    ALWAYS call with confirmed=False first. Show the preview to the user.
    Only pass confirmed=True after the user explicitly acknowledges the danger.
    """
    return await tool_home(confirmed)


@mcp.tool()
async def ugs_set_work_zero(axes: list = None, confirmed: bool = False) -> str:
    """
    Set G54 work zero at the current machine position for the specified axes.
    ALWAYS call with confirmed=False first. Show the preview to the user.
    Only pass confirmed=True after the user explicitly confirms.
    """
    return await tool_set_work_zero(axes or ["X", "Y", "Z"], confirmed)


@mcp.tool()
async def ugs_return_to_zero(confirmed: bool = False) -> str:
    """
    Rapid (G0) to G54 work zero (X0 Y0 Z0).
    ALWAYS call with confirmed=False first. Show the preview to the user.
    Only pass confirmed=True after the user explicitly confirms.
    """
    return await tool_return_to_zero(confirmed)


@mcp.tool()
async def ugs_run_file(file_path: str, confirmed: bool = False) -> str:
    """
    Stream a G-code file to the machine. Automatically runs a safety check in preview mode.
    ALWAYS call with confirmed=False first to show the safety report and preview.
    Only pass confirmed=True after the user explicitly confirms they want to start the job.
    """
    return await tool_run_file(file_path, confirmed)


@mcp.tool()
async def ugs_pause_job() -> str:
    """Pause the currently running G-code job (sends feed hold)."""
    return await tool_pause_job()


@mcp.tool()
async def ugs_cancel_job(confirmed: bool = False) -> str:
    """
    Cancel the running job. Stopping mid-cut will leave a mark on the part.
    ALWAYS call with confirmed=False first. Show the preview to the user.
    Only pass confirmed=True after the user explicitly confirms.
    """
    return await tool_cancel_job(confirmed)


@mcp.tool()
async def ugs_get_job_status() -> str:
    """Get current job progress and machine state."""
    return await tool_get_job_status()


@mcp.tool()
def gcode_translate(file_path_or_code: str, max_lines: int = None) -> str:
    """
    Translate G-code to plain English, line by line.
    Accepts either a file path or raw G-code string.
    Shows each command, its meaning, and the current machine state context.
    """
    return tool_gcode_translate(file_path_or_code, max_lines)


@mcp.tool()
def gcode_safety_check(file_path_or_code: str) -> str:
    """
    Check G-code for safety issues: spindle off during cuts, missing unit declaration,
    zero feedrate on cut moves, and other DANGER/WARNING/CAUTION issues.
    Run this before ugs_run_file for any G-code you did not write yourself.
    """
    return tool_gcode_safety_check(file_path_or_code)


@mcp.tool()
def gcode_estimate_time(file_path_or_code: str) -> str:
    """Estimate machining cycle time from G-code feedrates and distances. Returns HH:MM:SS."""
    return tool_gcode_estimate_time(file_path_or_code)


@mcp.tool()
def gcode_list_tools(file_path_or_code: str) -> str:
    """List all tools referenced in a G-code file, with first use line and usage count."""
    return tool_gcode_list_tools(file_path_or_code)


@mcp.tool()
def gcode_save_macro(name: str, gcode_content: str, description: str = "") -> str:
    """
    Save a G-code macro to the macros directory after running a safety check.
    Claude writes the G-code content; this tool handles validation and persistence.
    Use gcode_list_macros to see saved macros, gcode_run_macro to execute one.
    """
    return tool_gcode_save_macro(name, gcode_content, description)


@mcp.tool()
def gcode_list_macros() -> str:
    """List all saved macros with their names and descriptions."""
    return tool_gcode_list_macros()


@mcp.tool()
async def gcode_run_macro(name: str, confirmed: bool = False) -> str:
    """
    Run a saved macro by name.
    ALWAYS call with confirmed=False first to show G-code preview and safety check.
    Only pass confirmed=True after the user explicitly confirms.
    """
    return await tool_gcode_run_macro(name, confirmed)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Run the full test suite**

```bash
cd ugs_mcp
pytest tests/ -v
```

Expected: all tests PASS. Fix any failures before proceeding.

- [ ] **Step 3: Test server starts**

```bash
cd ugs_mcp
python server.py &
sleep 2
kill %1
```

Expected: server starts without errors (it will wait for stdio connections).

- [ ] **Step 4: Write Claude Code MCP config**

Create `ugs_mcp/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "ugs": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "UGS_HOST": "localhost",
        "UGS_PORT": "8080"
      }
    }
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add server.py .claude/mcp.json
git commit -m "feat: FastMCP server assembly - all 19 tools registered"
```

---

## Task 14: End-to-End Verification

No code to write. Manual verification steps.

- [ ] **Step 1: Confirm full test suite passes**

```bash
cd ugs_mcp
pytest tests/ -v --tb=short
```

Expected: all tests PASS with 0 failures.

- [ ] **Step 2: Start UGS with pendant enabled**

In UGS: Tools > Options > Pendant > Enable pendant on port 8080. Or launch headless:

```bash
# UGS Classic headless with pendant:
java -jar UniversalGcodeSender.jar --pendant
```

- [ ] **Step 3: Confirm pendant is reachable**

```bash
curl http://localhost:8080/api/v1/status/getStatus
```

Expected: JSON response with machine state fields.

- [ ] **Step 4: Register MCP server in Claude Code**

```bash
# From the ugs_mcp/ directory:
claude mcp add ugs python server.py
```

- [ ] **Step 5: Verify tools appear in Claude Code**

In Claude Code, type `/mcp` and confirm `ugs` server shows 19 tools.

- [ ] **Step 6: Test inspector tools (no machine needed)**

Ask Claude Code: "Use gcode_translate on this code: `G21\nG90\nM3 S18000\nG1 X100 F500\nM5`"

Expected: plain English line-by-line output.

- [ ] **Step 7: Test safety confirmation flow**

Ask Claude Code: "Jog X by 10mm at 500mm/min"

Expected:
1. Claude calls `ugs_jog("X", 10, 500, confirmed=False)` - returns preview + WARNING banner
2. Claude shows you the preview and asks for confirmation
3. You confirm, Claude calls `ugs_jog("X", 10, 500, confirmed=True)`
4. Machine moves

- [ ] **Step 8: Final commit**

```bash
git add .
git commit -m "feat: ugs_mcp server complete - 19 tools, safety system, G-code inspector"
```
