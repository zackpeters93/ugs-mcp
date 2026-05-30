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

        scalar_words = {w.letter: w.value for w in line.words if w.letter not in ("G", "M")}
        g_values = [w.value for w in line.words if w.letter == "G"]

        if 20 in g_values or 21 in g_values:
            unit_declared = True

        is_cut_move = any(g in (1, 2, 3) for g in g_values)
        is_any_move = any(g in (0, 1, 2, 3) for g in g_values)

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
            cut_g = next(g for g in g_values if g in (1, 2, 3))
            warnings.append({
                "code": "SPINDLE_OFF_DURING_CUT",
                "line_number": line.line_number,
                "message": f"Cut move (G{int(cut_g)}) while spindle is off (M5). This will rub, not cut.",
                "severity": "DANGER",
            })

        if is_cut_move and state.feedrate == 0 and "F" not in scalar_words:
            cut_g = next(g for g in g_values if g in (1, 2, 3))
            warnings.append({
                "code": "ZERO_FEEDRATE_ON_CUT",
                "line_number": line.line_number,
                "message": f"Cut move (G{int(cut_g)}) with feedrate=0. Machine may stall or behave unexpectedly.",
                "severity": "DANGER",
            })

        state = apply_line(state, line)

    return warnings


def estimate_time(file_path_or_code: str, rapid_speed: float = 5000.0) -> str:
    """Estimate total machining time. Returns HH:MM:SS string."""
    lines = load_gcode(file_path_or_code)
    state = ModalState()
    total_seconds = 0.0

    for line in lines:
        g_values = [w.value for w in line.words if w.letter == "G"]
        motion_g = next((g for g in g_values if g in (0, 1, 2, 3)), None)

        if motion_g is not None:
            prev = state.position.copy()
            state = apply_line(state, line)
            now = state.position

            dx = now.get("X", 0) - prev.get("X", 0)
            dy = now.get("Y", 0) - prev.get("Y", 0)
            dz = now.get("Z", 0) - prev.get("Z", 0)
            distance = math.sqrt(dx**2 + dy**2 + dz**2)

            if distance > 0:
                speed = rapid_speed if motion_g == 0 else (state.feedrate if state.feedrate > 0 else rapid_speed)
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
        for w in line.words:
            if w.letter == "T":
                t = int(w.value)
                if t not in tools:
                    tools[t] = {"tool": t, "first_line": line.line_number, "use_count": 0}
                tools[t]["use_count"] += 1

    return sorted(tools.values(), key=lambda x: x["tool"])
