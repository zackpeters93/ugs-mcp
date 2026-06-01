# ugs_mcp/server.py
from mcp.server.fastmcp import FastMCP

from ugs_mcp.tools.connection import tool_connect, tool_disconnect, tool_troubleshoot_connection
from ugs_mcp.tools.status import tool_get_status
from ugs_mcp.tools.motion import tool_jog, tool_home, tool_set_work_zero, tool_return_to_zero
from ugs_mcp.tools.job import tool_run_file, tool_pause_job, tool_cancel_job, tool_get_job_status
from ugs_mcp.tools.inspector import (
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
async def ugs_jog(axis: str, distance_mm: float, feedrate: float, confirmation_token: str = "") -> str:
    """
    Jog a single axis (X, Y, or Z) by distance_mm at feedrate mm/min.
    Call with no token first to get a preview and confirmation token.
    The user must provide the token back before movement executes.
    Claude CANNOT self-confirm movement - the token enforces this at the server level.
    """
    return await tool_jog(axis, distance_mm, feedrate, confirmation_token)


@mcp.tool()
async def ugs_home(confirmation_token: str = "") -> str:
    """
    Run the GRBL homing cycle ($H). All axes move toward limit switches at full speed.
    Call with no token first to get a preview and confirmation token.
    The user must provide the token back before homing executes.
    Claude CANNOT self-confirm movement - the token enforces this at the server level.
    """
    return await tool_home(confirmation_token)


@mcp.tool()
async def ugs_set_work_zero(axes: list = None, confirmed: bool = False) -> str:
    """
    Set G54 work zero at the current machine position for the specified axes.
    This does NOT move the machine - only sets coordinate offsets.
    Call with confirmed=False first to preview, then confirmed=True to apply.
    """
    return await tool_set_work_zero(axes or ["X", "Y", "Z"], confirmed)


@mcp.tool()
async def ugs_return_to_zero(confirmation_token: str = "") -> str:
    """
    Rapid (G0) to G54 work zero (X0 Y0 Z0).
    Call with no token first to get a preview and confirmation token.
    The user must provide the token back before movement executes.
    Claude CANNOT self-confirm movement - the token enforces this at the server level.
    """
    return await tool_return_to_zero(confirmation_token)


@mcp.tool()
async def ugs_run_file(file_path: str, confirmation_token: str = "") -> str:
    """
    Stream a G-code file to the machine. Runs safety check in preview mode.
    Call with no token first to get the safety report and confirmation token.
    The user must provide the token back before the job starts.
    Claude CANNOT self-confirm - the token enforces this at the server level.
    """
    return await tool_run_file(file_path, confirmation_token)


@mcp.tool()
async def ugs_pause_job() -> str:
    """Pause the currently running G-code job (sends feed hold)."""
    return await tool_pause_job()


@mcp.tool()
async def ugs_cancel_job(confirmed: bool = False) -> str:
    """
    Cancel the running job. Stopping mid-cut will leave a mark on the part.
    Uses simple confirmed=True/False (not a token) because stopping is always safer
    than continuing - token friction on an emergency stop would be dangerous.
    Call with confirmed=False first to preview, then confirmed=True to cancel.
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
async def gcode_run_macro(name: str, confirmation_token: str = "") -> str:
    """
    Run a saved macro by name.
    Call with no token first to get the G-code preview, safety check, and confirmation token.
    The user must provide the token back before the macro runs.
    Claude CANNOT self-confirm - the token enforces this at the server level.
    """
    return await tool_gcode_run_macro(name, confirmation_token)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
