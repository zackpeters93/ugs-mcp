# ugs_mcp/tests/test_analyzer.py
import pytest
from gcode.analyzer import translate


def test_translate_returns_list():
    result = translate("G21\nG0 X0 Y0")
    assert isinstance(result, list)
    assert len(result) == 2


def test_translate_includes_line_number():
    result = translate("G21")
    assert result[0]["line_number"] == 1


def test_translate_includes_raw():
    result = translate("G21")
    assert result[0]["raw"] == "G21"


def test_translate_includes_explanation():
    result = translate("G21")
    assert "mm" in result[0]["explanation"].lower() or "metric" in result[0]["explanation"].lower()


def test_translate_includes_context():
    result = translate("G21\nM3 S18000\nG1 X10 F500")
    line = result[2]
    assert "context" in line
    assert "spindle" in line["context"].lower()


def test_translate_max_lines():
    code = "\n".join(f"G0 X{i}" for i in range(20))
    result = translate(code, max_lines=5)
    assert len(result) == 5


def test_translate_skips_blank_lines():
    result = translate("G21\n\nG90")
    assert all(r["raw"] != "" for r in result)


def test_translate_comment_only_line():
    result = translate("(setup section)")
    assert len(result) == 1
    assert "comment" in result[0]["explanation"].lower() or "setup section" in result[0]["explanation"]


from gcode.analyzer import safety_check


def test_safety_check_returns_list():
    result = safety_check("G21\nG90\nM3 S18000\nG1 X10 F500\nM5")
    assert isinstance(result, list)


def test_safety_check_no_unit_declaration():
    result = safety_check("G0 X10 Y20")
    codes = [w["code"] for w in result]
    assert "NO_UNIT_DECLARATION" in codes


def test_safety_check_spindle_off_during_cut():
    code = "G21\nG90\nM5\nG1 X10 F500"
    result = safety_check(code)
    codes = [w["code"] for w in result]
    assert "SPINDLE_OFF_DURING_CUT" in codes


def test_safety_check_zero_feedrate_on_cut():
    code = "G21\nG90\nM3 S18000\nG1 X10"
    result = safety_check(code)
    codes = [w["code"] for w in result]
    assert "ZERO_FEEDRATE_ON_CUT" in codes


def test_safety_check_clean_program():
    code = "G21\nG90\nM3 S18000\nG1 X10 F500\nM5"
    result = safety_check(code)
    assert result == []


def test_safety_check_warning_has_required_fields():
    result = safety_check("G0 X10")
    assert len(result) > 0
    w = result[0]
    assert "code" in w
    assert "line_number" in w
    assert "message" in w
    assert "severity" in w


from gcode.analyzer import estimate_time, list_tools


def test_estimate_time_returns_string():
    result = estimate_time("G21\nG1 X100 F1000")
    assert isinstance(result, str)
    assert ":" in result


def test_estimate_time_simple_move():
    # 100mm at 1000mm/min = 0.1 min = 6 seconds
    result = estimate_time("G21\nG90\nG1 X100 F1000")
    assert result == "0:00:06"


def test_estimate_time_rapid_uses_default_speed():
    # 1000mm rapid at 5000mm/min = 0.2 min = 12 seconds
    result = estimate_time("G21\nG90\nG0 X1000", rapid_speed=5000.0)
    assert result == "0:00:12"


def test_estimate_time_empty_program():
    result = estimate_time("G21\nG90")
    assert result == "0:00:00"


def test_list_tools_returns_list():
    result = list_tools("G21\nT1 M6\nG1 X10 F500")
    assert isinstance(result, list)


def test_list_tools_finds_tool():
    result = list_tools("G21\nT1 M6\nG1 X10 F500\nT2 M6")
    tool_numbers = [t["tool"] for t in result]
    assert 1 in tool_numbers
    assert 2 in tool_numbers


def test_list_tools_records_first_use_line():
    result = list_tools("G21\nT3 M6")
    assert result[0]["first_line"] == 2


def test_list_tools_empty_program():
    result = list_tools("G21\nG0 X0")
    assert result == []
