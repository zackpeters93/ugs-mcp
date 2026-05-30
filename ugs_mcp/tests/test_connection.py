# ugs_mcp/tests/test_connection.py
import pytest
from unittest.mock import AsyncMock, patch
from tools.connection import tool_troubleshoot_connection


@pytest.mark.asyncio
async def test_troubleshoot_reports_pendant_unreachable():
    with patch("tools.connection.is_pendant_reachable", new=AsyncMock(return_value=False)):
        with patch("tools.connection.serial.tools.list_ports.comports", return_value=[]):
            result = await tool_troubleshoot_connection()
    assert "pendant" in result.lower()
    assert "not reachable" in result.lower() or "unreachable" in result.lower() or "cannot" in result.lower() or "NOT REACHABLE" in result


@pytest.mark.asyncio
async def test_troubleshoot_lists_serial_ports():
    mock_port = type("Port", (), {"device": "/dev/tty.usbserial-1410", "description": "USB Serial"})()

    with patch("tools.connection.is_pendant_reachable", new=AsyncMock(return_value=True)):
        with patch("tools.connection.serial.tools.list_ports.comports", return_value=[mock_port]):
            with patch("tools.connection.get_status", new=AsyncMock(return_value={
                "status": "ok", "state": "Idle",
                "machine_position": {}, "work_position": {},
                "feed_speed": 0, "spindle_speed": 0
            })):
                result = await tool_troubleshoot_connection()
    assert "/dev/tty.usbserial-1410" in result
