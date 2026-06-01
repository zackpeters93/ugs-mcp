# ugs_mcp/tests/test_commands.py
from ugs_mcp.gcode.commands import describe_word, GCODE_DESCRIPTIONS


def test_g0_description():
    result = describe_word("G", 0)
    assert "rapid" in result.lower() or "positioning" in result.lower()


def test_g1_description():
    result = describe_word("G", 1)
    assert "linear" in result.lower() or "cut" in result.lower()


def test_m3_description():
    result = describe_word("M", 3)
    assert "spindle" in result.lower()


def test_m5_description():
    result = describe_word("M", 5)
    assert "spindle" in result.lower() or "stop" in result.lower()


def test_unknown_code_returns_string():
    result = describe_word("G", 999)
    assert "999" in result


def test_g21_metric():
    result = describe_word("G", 21)
    assert "mm" in result.lower() or "millimeter" in result.lower() or "metric" in result.lower()


def test_feedrate_word():
    result = describe_word("F", 500)
    assert "feedrate" in result.lower() or "500" in result


def test_spindle_speed_word():
    result = describe_word("S", 18000)
    assert "spindle" in result.lower() or "18000" in result


def test_all_common_codes_present():
    for code in ["G0", "G1", "G2", "G3", "G20", "G21", "G90", "G91", "M3", "M5"]:
        assert code in GCODE_DESCRIPTIONS, f"{code} missing from glossary"
