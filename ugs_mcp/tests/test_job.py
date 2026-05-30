# ugs_mcp/tests/test_job.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from tools.job import tool_run_file, tool_cancel_job, tool_pause_job, tool_get_job_status

_IDLE_STATUS = {
    "status": "ok", "state": "Idle",
    "machine_position": {"x": 0, "y": 0, "z": 0},
    "work_position": {"x": 0, "y": 0, "z": 0},
    "feed_speed": 0, "spindle_speed": 0
}


@pytest.mark.asyncio
async def test_run_file_preview_returns_warning(tmp_path):
    f = tmp_path / "test.nc"
    f.write_text("G21\nG90\nM3 S18000\nG1 X10 F500\nM5\n")
    with patch("tools.job.get_status", new=AsyncMock(return_value=_IDLE_STATUS)):
        result = await tool_run_file(str(f), confirmed=False)
    assert "WARNING" in result
    assert "SPINDLE" in result or "CUT" in result


@pytest.mark.asyncio
async def test_run_file_preview_includes_safety_check(tmp_path):
    f = tmp_path / "unsafe.nc"
    f.write_text("G0 X10\nM5\nG1 X20 F500\n")
    with patch("tools.job.get_status", new=AsyncMock(return_value=_IDLE_STATUS)):
        result = await tool_run_file(str(f), confirmed=False)
    assert "SPINDLE_OFF_DURING_CUT" in result or "spindle" in result.lower()


@pytest.mark.asyncio
async def test_run_file_missing_file():
    result = await tool_run_file("/nonexistent/path.nc", confirmed=False)
    assert "not found" in result.lower() or "does not exist" in result.lower()


@pytest.mark.asyncio
async def test_cancel_job_preview_returns_caution():
    with patch("tools.job.get_status", new=AsyncMock(return_value={
        **_IDLE_STATUS, "state": "Run", "feed_speed": 500, "spindle_speed": 18000
    })):
        result = await tool_cancel_job(confirmed=False)
    assert "CAUTION" in result
    assert "MID-CUT" in result or "mark" in result.lower()


@pytest.mark.asyncio
async def test_pause_job_sends_command():
    send_mock = AsyncMock(return_value={"status": "ok"})
    with patch("tools.job.send_gcode", new=send_mock):
        result = await tool_pause_job()
    send_mock.assert_called_once()
    assert "pause" in result.lower() or "paused" in result.lower()
