# ugs_mcp/tests/test_status.py
import pytest
from unittest.mock import AsyncMock, patch
from ugs_mcp.tools.status import tool_get_status


@pytest.mark.asyncio
async def test_get_status_formats_output():
    mock_status = {
        "status": "ok",
        "state": "Idle",
        "machine_position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "work_position": {"x": 10.0, "y": 5.0, "z": 0.0},
        "feed_speed": 500,
        "spindle_speed": 18000,
    }
    with patch("ugs_mcp.tools.status.get_status", new=AsyncMock(return_value=mock_status)):
        result = await tool_get_status()
    assert "Idle" in result
    assert "18000" in result


@pytest.mark.asyncio
async def test_get_status_handles_error():
    with patch("ugs_mcp.tools.status.get_status", new=AsyncMock(return_value={"status": "error", "message": "timeout"})):
        result = await tool_get_status()
    assert "error" in result.lower() or "timeout" in result.lower()
