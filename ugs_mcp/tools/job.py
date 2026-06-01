# ugs_mcp/tools/job.py
from pathlib import Path
from ugs_mcp.ugs_client import send_gcode, get_status, send_file, cancel_file
from ugs_mcp.config import WARNING_MESSAGES
from ugs_mcp.gcode.analyzer import safety_check
from ugs_mcp.confirmation import generate_token, consume_token, TOKEN_TTL_SECONDS

_TTL_MIN = TOKEN_TTL_SECONDS // 60


def _token_instructions(token: str) -> str:
    return (
        f"\n\nTo execute, show the user this confirmation token: [{token}]\n"
        f"Ask them to confirm by reading the token back to you.\n"
        f"Then call this tool again with confirmation_token=\"{token}\".\n"
        f"Token expires in {_TTL_MIN} minutes and is single-use."
    )


def _invalid_token_error(banner: str) -> str:
    return (
        f"{banner}\n\n"
        "INVALID OR EXPIRED TOKEN - job blocked.\n"
        "Call this tool without a token to generate a new preview and token."
    )


async def tool_run_file(file_path: str, confirmation_token: str = "") -> str:
    """
    Stream a G-code file to the CNC machine.

    TWO-STEP SAFETY PROTOCOL - machine will NOT run without a user-provided token:
    Step 1: Call with no token -> runs safety check, shows preview, returns a token.
            Show the token to the user and ask them to confirm.
    Step 2: Call again with the token the user confirmed -> job starts.
    Claude cannot self-confirm. The token must come from the user.
    """
    banner = WARNING_MESSAGES["run_file"]
    p = Path(file_path)

    if not p.exists():
        return f"File not found: {file_path}"

    if confirmation_token:
        desc = consume_token(confirmation_token)
        if desc is None:
            return _invalid_token_error(banner)
        result = await send_file(file_path)
        if result["status"] == "error":
            return f"{banner}\n\nFailed to start job: {result['message']}"
        return f"{banner}\n\nJob started: {p.name}"

    warnings = safety_check(file_path)
    status = await get_status()

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
        lines.append("\nReview all warnings before confirming.")
    else:
        lines.append("Safety check: PASSED (no issues found)")

    token = generate_token(f"Run file: {p.name}")
    lines.append(_token_instructions(token))
    return "\n".join(lines)


async def tool_pause_job() -> str:
    """Pause the currently running G-code job (sends feed hold). No confirmation required - stopping is always safe."""
    result = await send_gcode("!")
    if result["status"] == "error":
        return f"Pause failed: {result['message']}"
    return "Job paused (feed hold sent). Resume from UGS or send ~ to continue."


async def tool_cancel_job(confirmed: bool = False) -> str:
    """
    Cancel the currently running G-code job.
    Uses simple confirmed=True/False (not token) because stopping movement is always safer
    than continuing - adding token friction to an emergency stop would be dangerous.
    ALWAYS call with confirmed=False first to show the user a preview.
    """
    banner = WARNING_MESSAGES["cancel_job"]

    if confirmed:
        result = await cancel_file()
        if result["status"] == "error":
            return f"{banner}\n\nCancel failed: {result['message']}"
        return f"{banner}\n\nJob cancelled. Machine stopped."

    status = await get_status()
    mp = status.get("machine_position", {})
    lines = [
        banner,
        "",
        "PREVIEW - job is still running:",
        f"  Current position: X={mp.get('x', 0):.3f} Y={mp.get('y', 0):.3f} Z={mp.get('z', 0):.3f}",
        "  Cancelling stops the cutter mid-path and may leave a mark on the part.",
        "  The spindle will NOT stop automatically - send M5 afterward if needed.",
        "\n\nCall again with confirmed=True to cancel.",
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
        "(For detailed job progress percentage, check UGS directly)"
    )
