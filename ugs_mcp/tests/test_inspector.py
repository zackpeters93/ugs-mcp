# ugs_mcp/tests/test_inspector.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from tools.inspector import (
    tool_gcode_translate,
    tool_gcode_safety_check,
    tool_gcode_estimate_time,
    tool_gcode_list_tools,
    tool_gcode_save_macro,
    tool_gcode_list_macros,
    tool_gcode_run_macro,
)


def test_translate_tool_returns_string():
    result = tool_gcode_translate("G21\nG0 X0 Y0")
    assert isinstance(result, str)
    assert "G21" in result


def test_translate_tool_shows_explanation():
    result = tool_gcode_translate("G21")
    assert "mm" in result.lower() or "metric" in result.lower()


def test_safety_check_tool_returns_string():
    result = tool_gcode_safety_check("G21\nG90\nM3 S18000\nG1 X10 F500\nM5")
    assert isinstance(result, str)
    assert "passed" in result.lower() or "issue" in result.lower()


def test_safety_check_reports_warnings():
    result = tool_gcode_safety_check("G0 X10")
    assert "NO_UNIT_DECLARATION" in result or "unit" in result.lower()


def test_estimate_time_tool_returns_string():
    result = tool_gcode_estimate_time("G21\nG90\nG1 X100 F1000")
    assert isinstance(result, str)
    assert ":" in result


def test_list_tools_tool_returns_string():
    result = tool_gcode_list_tools("G21\nT1 M6\nG1 X10 F500")
    assert isinstance(result, str)
    assert "1" in result


def test_save_macro_creates_file(tmp_path):
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = tool_gcode_save_macro("probe_z", "G21\nG91\nG38.2 Z-20 F50\nG92 Z0", "Probe Z surface")
    assert "saved" in result.lower() or "probe_z" in result.lower()
    saved = tmp_path / "probe_z.nc"
    assert saved.exists()
    assert "; Macro: probe_z" in saved.read_text()


def test_list_macros_empty(tmp_path):
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = tool_gcode_list_macros()
    assert "no macros" in result.lower() or result.strip() == "" or "0" in result


def test_list_macros_shows_saved(tmp_path):
    (tmp_path / "probe_z.nc").write_text("G21\nG38.2 Z-20 F50")
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = tool_gcode_list_macros()
    assert "probe_z" in result


@pytest.mark.asyncio
async def test_run_macro_preview(tmp_path):
    (tmp_path / "probe_z.nc").write_text("G21\nG38.2 Z-20 F50")
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        result = await tool_gcode_run_macro("probe_z", confirmed=False)
    assert "HEADS UP" in result or "MACRO" in result


@pytest.mark.asyncio
async def test_run_macro_missing():
    result = await tool_gcode_run_macro("nonexistent", confirmed=False)
    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_run_macro_confirmed_sends_gcode(tmp_path):
    (tmp_path / "probe_z.nc").write_text("G21\nG38.2 Z-20 F50")
    send_mock = AsyncMock(return_value={"status": "ok"})
    with patch("tools.inspector.MACROS_DIR", tmp_path):
        with patch("tools.inspector.send_gcode", new=send_mock):
            result = await tool_gcode_run_macro("probe_z", confirmed=True)
    send_mock.assert_called_once()
    assert "started" in result.lower() or "probe_z" in result.lower()
