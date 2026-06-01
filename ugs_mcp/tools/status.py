# ugs_mcp/tools/status.py
from ugs_mcp.ugs_client import get_status


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
