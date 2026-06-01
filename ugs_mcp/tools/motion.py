# ugs_mcp/tools/motion.py
from typing import List
from ugs_client import send_gcode, get_status
from config import WARNING_MESSAGES
from confirmation import generate_token, consume_token, TOKEN_TTL_SECONDS

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
        "INVALID OR EXPIRED TOKEN - movement blocked.\n"
        "Call this tool without a token to generate a new preview and token."
    )


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


async def tool_jog(axis: str, distance_mm: float, feedrate: float, confirmation_token: str = "") -> str:
    """
    Jog a single axis by distance_mm at feedrate mm/min.

    TWO-STEP SAFETY PROTOCOL - machine will NOT move without a user-provided token:
    Step 1: Call with no token -> returns a preview and a confirmation token.
            Show the token to the user and ask them to confirm.
    Step 2: Call again with the token the user confirmed -> machine moves.
    Claude cannot self-confirm. The token must come from the user.
    """
    banner = WARNING_MESSAGES["jog"]
    axis = axis.upper()

    if confirmation_token:
        desc = consume_token(confirmation_token)
        if desc is None:
            return _invalid_token_error(banner)
        alarm = await _check_alarm_state()
        if alarm:
            return alarm
        cmd = f"$J=G91 G21 {axis}{distance_mm} F{feedrate}"
        result = await send_gcode(cmd)
        if result["status"] == "error":
            return f"{banner}\n\nJog failed: {result['message']}"
        return f"{banner}\n\nJogging {axis} by {distance_mm}mm at {feedrate}mm/min."

    status = await get_status()
    mp = status.get("machine_position", {})
    token = generate_token(f"Jog {axis} {distance_mm}mm at {feedrate}mm/min")

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
        lines.append(f"  New {axis} position (approx): {new_val:.3f}mm")
    lines.append(_token_instructions(token))
    return "\n".join(lines)


async def tool_home(confirmation_token: str = "") -> str:
    """
    Run the GRBL homing cycle ($H). ALL axes move toward limit switches at full speed.

    TWO-STEP SAFETY PROTOCOL - machine will NOT move without a user-provided token:
    Step 1: Call with no token -> returns a preview and a confirmation token.
            Show the token to the user and ask them to confirm.
    Step 2: Call again with the token the user confirmed -> homing starts.
    Claude cannot self-confirm. The token must come from the user.
    """
    banner = WARNING_MESSAGES["home"]

    if confirmation_token:
        desc = consume_token(confirmation_token)
        if desc is None:
            return _invalid_token_error(banner)
        result = await send_gcode("$H")
        if result["status"] == "error":
            return f"{banner}\n\nHoming failed: {result['message']}"
        return f"{banner}\n\nHoming cycle started. All axes moving toward limit switches."

    token = generate_token("Homing cycle ($H) - all axes")
    lines = [
        banner,
        "",
        "PREVIEW - no movement yet:",
        "  Command: $H (GRBL homing cycle)",
        "  ALL axes will move toward their limit switches at maximum speed.",
        "  Ensure nothing is in the machine's travel path before confirming.",
        _token_instructions(token),
    ]
    return "\n".join(lines)


async def tool_set_work_zero(axes: List[str] = None, confirmed: bool = False) -> str:
    """
    Set G54 work zero at the current machine position for the specified axes.
    This does NOT move the machine - it only sets coordinate offsets.
    ALWAYS call with confirmed=False first to show the user a preview.
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
        "  This sets the G54 work origin for selected axes. Machine does NOT move.",
        "\n\nCall again with confirmed=True to apply.",
    ]
    return "\n".join(lines)


async def tool_return_to_zero(confirmation_token: str = "") -> str:
    """
    Rapid (G0) to G54 work zero (X0 Y0 Z0).

    TWO-STEP SAFETY PROTOCOL - machine will NOT move without a user-provided token:
    Step 1: Call with no token -> returns a preview and a confirmation token.
            Show the token to the user and ask them to confirm.
    Step 2: Call again with the token the user confirmed -> machine moves.
    Claude cannot self-confirm. The token must come from the user.
    """
    banner = WARNING_MESSAGES["return_to_zero"]

    if confirmation_token:
        desc = consume_token(confirmation_token)
        if desc is None:
            return _invalid_token_error(banner)
        alarm = await _check_alarm_state()
        if alarm:
            return alarm
        result = await send_gcode("G0 G54 X0 Y0 Z0")
        if result["status"] == "error":
            return f"{banner}\n\nReturn to zero failed: {result['message']}"
        return f"{banner}\n\nMoving to G54 work zero (X0 Y0 Z0)."

    token = generate_token("Return to G54 work zero (G0 X0 Y0 Z0)")
    lines = [
        banner,
        "",
        "PREVIEW - no movement yet:",
        "  Will rapid (G0) to X=0 Y=0 Z=0 in the G54 work coordinate system.",
        "  Ensure the path is clear before confirming.",
        _token_instructions(token),
    ]
    return "\n".join(lines)
