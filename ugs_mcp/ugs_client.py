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
