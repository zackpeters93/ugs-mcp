# ugs_mcp/tools/connection.py
import serial.tools.list_ports
from ugs_client import get_status, is_pendant_reachable, send_gcode
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
    """Connect UGS to CNC machine via serial port.
    NOTE: UGS pendant connection API endpoint needs verification during hardware testing.
    The CONNECT command may require a dedicated REST endpoint rather than sendGcode.
    """
    result = await send_gcode(f"CONNECT:{port}:{baud_rate}:{firmware}")
    if result["status"] == "error":
        return f"{WARNING_MESSAGES['connection_issue']}\n\nFailed to connect: {result['message']}\n\nIf this fails, connect manually via the UGS UI and use this server for control only."
    return f"Connection initiated to {port} at {baud_rate} baud ({firmware} firmware).\nCheck UGS for connection status."


async def tool_disconnect() -> str:
    """Disconnect UGS from the CNC machine."""
    result = await send_gcode("DISCONNECT")
    if result["status"] == "error":
        return f"Disconnect failed: {result['message']}"
    return "Disconnected from CNC machine."
