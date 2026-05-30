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
    ALWAYS call with confirmed=False first - runs safety checker and shows a preview.
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
    """Pause the currently running G-code job (sends feed hold '!')."""
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
        f"  Current machine position: X={mp.get('x', 0):.3f} Y={mp.get('y', 0):.3f} Z={mp.get('z', 0):.3f}",
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
        "(For detailed job progress percentage, check UGS directly)"
    )
