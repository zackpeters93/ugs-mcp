from typing import Any, Dict
import httpx
from config import UGS_BASE_URL


async def send_gcode(command: str) -> Dict[str, Any]:
    """Send a single G-code command to the UGS pendant."""
    url = f"{UGS_BASE_URL}/api/v1/machine/sendGcode"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json={"commands": command})
            if response.status_code >= 400:
                return {"status": "error", "message": f"UGS returned HTTP {response.status_code}: {response.text}"}
            return {"status": "ok", "code": response.status_code}
    except httpx.ConnectError as e:
        return {"status": "error", "message": f"Cannot reach UGS pendant at {UGS_BASE_URL}: {e}"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "UGS pendant request timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def connect_machine(port: str, baud_rate: int = 115200, firmware: str = "GRBL") -> Dict[str, Any]:
    """Connect UGS to the CNC machine via serial port."""
    url = f"{UGS_BASE_URL}/api/v1/machine/connect"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={"Accept": "*/*", "Content-Type": "application/json"},
                content=f'{{"port":"{port}","baudRate":{baud_rate},"firmware":"{firmware}"}}'.encode(),
            )
            if response.status_code >= 400:
                return {"status": "error", "message": f"UGS returned HTTP {response.status_code}: {response.text}"}
            return {"status": "ok"}
    except httpx.ConnectError as e:
        return {"status": "error", "message": f"Cannot reach UGS pendant at {UGS_BASE_URL}: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def disconnect_machine() -> Dict[str, Any]:
    """Disconnect UGS from the CNC machine."""
    url = f"{UGS_BASE_URL}/api/v1/machine/disconnect"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                return {"status": "error", "message": f"UGS returned HTTP {response.status_code}: {response.text}"}
            return {"status": "ok"}
    except httpx.ConnectError as e:
        return {"status": "error", "message": f"Cannot reach UGS pendant at {UGS_BASE_URL}: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def send_file(file_path: str) -> Dict[str, Any]:
    """Stream a G-code file to the machine via multipart upload."""
    url = f"{UGS_BASE_URL}/api/v1/files/send"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(file_path, "rb") as f:
                response = await client.post(url, files={"file": (file_path.split("/")[-1], f, "text/plain")})
            if response.status_code >= 400:
                return {"status": "error", "message": f"UGS returned HTTP {response.status_code}: {response.text}"}
            return {"status": "ok"}
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except httpx.ConnectError as e:
        return {"status": "error", "message": f"Cannot reach UGS pendant at {UGS_BASE_URL}: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def cancel_file() -> Dict[str, Any]:
    """Cancel the currently running G-code file job."""
    url = f"{UGS_BASE_URL}/api/v1/files/cancel"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                return {"status": "error", "message": f"UGS returned HTTP {response.status_code}: {response.text}"}
            return {"status": "ok"}
    except httpx.ConnectError as e:
        return {"status": "error", "message": f"Cannot reach UGS pendant at {UGS_BASE_URL}: {e}"}
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
