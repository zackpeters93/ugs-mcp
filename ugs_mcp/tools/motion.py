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
            "CANNOT EXECUTE: Machine is in ALARM state.\n"
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

    if confirmed:
        alarm = await _check_alarm_state()
        if alarm:
            return alarm
        cmd = f"$J=G91 G21 {axis}{distance_mm} F{feedrate}"
        result = await send_gcode(cmd)
        if result["status"] == "error":
            return f"{banner}\n\nJog failed: {result['message']}"
        return f"{banner}\n\nJogging {axis} by {distance_mm}mm at {feedrate}mm/min. Command sent."

    status = await get_status()
    mp = status.get("machine_position", {})
    lines = [
        banner,
        "",
        "PREVIEW - no movement yet:",
        f"  Axis:      {axis}",
        f"  Distance:  {distance_mm}mm",
        f"  Feedrate:  {feedrate}mm/min",
        f"  Current machine pos: X={mp.get('x', 0):.3f} Y={mp.get('y', 0):.3f} Z={mp.get('z', 0):.3f}",
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
        f"    X={mp.get('x', 0):.3f}  Y={mp.get('y', 0):.3f}  Z={mp.get('z', 0):.3f}",
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
        result = await send_gcode("G0 G54 X0 Y0 Z0")
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
