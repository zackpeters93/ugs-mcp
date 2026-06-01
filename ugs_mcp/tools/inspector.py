# ugs_mcp/tools/inspector.py
from pathlib import Path
from typing import Optional

from config import MACROS_DIR, WARNING_MESSAGES, RAPID_SPEED_MM_MIN
from gcode.analyzer import translate, safety_check, estimate_time, list_tools
from ugs_client import send_file
from confirmation import generate_token, consume_token, TOKEN_TTL_SECONDS

_TTL_MIN = TOKEN_TTL_SECONDS // 60


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

    macro_path = MACROS_DIR / f"{name}.nc"
    header = f"; Macro: {name}\n"
    if description:
        header += f"; Description: {description}\n"
    macro_path.write_text(header + gcode_content)

    lines = [f"Macro '{name}' saved to {macro_path}"]
    if description:
        lines.append(f"Description: {description}")
    if warnings:
        warn_lines = [f"  [{w['severity']}] Line {w['line_number']}: {w['message']}" for w in warnings]
        lines.append("\nSafety warnings:\n" + "\n".join(warn_lines))
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


async def tool_gcode_run_macro(name: str, confirmation_token: str = "") -> str:
    """
    Run a saved macro by name.

    TWO-STEP SAFETY PROTOCOL - machine will NOT run without a user-provided token:
    Step 1: Call with no token -> shows G-code preview, safety check, and returns a token.
            Show the token to the user and ask them to confirm.
    Step 2: Call again with the token the user confirmed -> macro runs.
    Claude cannot self-confirm. The token must come from the user.
    """
    banner = WARNING_MESSAGES["run_macro"]
    macro_path = MACROS_DIR / f"{name}.nc"

    if not macro_path.exists():
        return f"Macro '{name}' not found. Use gcode_list_macros to see available macros."

    content = macro_path.read_text()
    warnings = safety_check(content)

    if confirmation_token:
        desc = consume_token(confirmation_token)
        if desc is None:
            return (
                f"{banner}\n\n"
                "INVALID OR EXPIRED TOKEN - macro blocked.\n"
                "Call this tool without a token to generate a new preview and token."
            )
        result = await send_file(str(macro_path))
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
    preview_lines = [l for l in content.splitlines() if not l.startswith(";")]
    for line in preview_lines[:10]:
        lines.append(f"  {line}")
    if len(preview_lines) > 10:
        lines.append("  ...")

    if warnings:
        lines.append(f"\nSafety issues: {len(warnings)}")
        for w in warnings:
            lines.append(f"  [{w['severity']}] {w['message']}")
    else:
        lines.append("\nSafety check: PASSED")

    token = generate_token(f"Run macro: {name}")
    lines.append(
        f"\n\nTo execute, show the user this confirmation token: [{token}]\n"
        f"Ask them to confirm by reading the token back to you.\n"
        f"Then call this tool again with confirmation_token=\"{token}\".\n"
        f"Token expires in {_TTL_MIN} minutes and is single-use."
    )
    return "\n".join(lines)
