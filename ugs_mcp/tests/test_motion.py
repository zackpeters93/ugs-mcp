# ugs_mcp/tests/test_motion.py
import pytest
from unittest.mock import AsyncMock, patch
from ugs_mcp.tools.motion import tool_jog, tool_home, tool_set_work_zero, tool_return_to_zero

_IDLE_STATUS = {
    "status": "ok", "state": "Idle",
    "machine_position": {"x": 0, "y": 0, "z": 0},
    "work_position": {"x": 0, "y": 0, "z": 0},
    "feed_speed": 0, "spindle_speed": 0
}

_ALARM_STATUS = {**_IDLE_STATUS, "state": "Alarm"}


@pytest.mark.asyncio
async def test_jog_preview_returns_banner():
    with patch("ugs_mcp.tools.motion.get_status", new=AsyncMock(return_value=_IDLE_STATUS)):
        result = await tool_jog("X", 10.0, 500)
    assert "WARNING" in result
    assert "MOVE" in result


@pytest.mark.asyncio
async def test_jog_preview_does_not_send_gcode():
    send_mock = AsyncMock()
    with patch("ugs_mcp.tools.motion.get_status", new=AsyncMock(return_value=_IDLE_STATUS)):
        with patch("ugs_mcp.tools.motion.send_gcode", new=send_mock):
            await tool_jog("X", 10.0, 500)
    send_mock.assert_not_called()


@pytest.mark.asyncio
async def test_jog_confirmed_sends_gcode():
    send_mock = AsyncMock(return_value={"status": "ok"})
    with patch("ugs_mcp.tools.motion.consume_token", return_value="Jog X 10.0mm at 500.0mm/min"):
        with patch("ugs_mcp.tools.motion.get_status", new=AsyncMock(return_value=_IDLE_STATUS)):
            with patch("ugs_mcp.tools.motion.send_gcode", new=send_mock):
                await tool_jog("X", 10.0, 500, "FAKETOKEN")
    send_mock.assert_called_once()


@pytest.mark.asyncio
async def test_jog_blocked_in_alarm_state():
    with patch("ugs_mcp.tools.motion.consume_token", return_value="Jog X 10.0mm at 500.0mm/min"):
        with patch("ugs_mcp.tools.motion.get_status", new=AsyncMock(return_value=_ALARM_STATUS)):
            result = await tool_jog("X", 10.0, 500, "FAKETOKEN")
    assert "alarm" in result.lower()
    assert "cannot" in result.lower() or "blocked" in result.lower() or "unlock" in result.lower() or "ALARM" in result


@pytest.mark.asyncio
async def test_home_preview_returns_danger_banner():
    result = await tool_home()
    assert "DANGER" in result
    assert "LIMIT" in result or "SPEED" in result or "limit" in result.lower()


@pytest.mark.asyncio
async def test_set_work_zero_preview_returns_caution():
    with patch("ugs_mcp.tools.motion.get_status", new=AsyncMock(return_value={
        **_IDLE_STATUS, "machine_position": {"x": 10, "y": 20, "z": 0}
    })):
        result = await tool_set_work_zero(["X", "Y", "Z"], confirmed=False)
    assert "CAUTION" in result
    assert "ZERO" in result or "COORDINATE" in result or "zero" in result.lower()


@pytest.mark.asyncio
async def test_return_to_zero_preview_returns_banner():
    result = await tool_return_to_zero()
    assert "WARNING" in result
