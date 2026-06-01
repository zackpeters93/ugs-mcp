import pytest
from ugs_mcp.gcode.parser import parse_line, parse_string, load_gcode, GCodeWord, GCodeLine

def test_parse_simple_g0():
    line = parse_line("G0 X10 Y20", line_number=1)
    assert line.line_number == 1
    assert GCodeWord("G", 0.0) in line.words
    assert GCodeWord("X", 10.0) in line.words
    assert GCodeWord("Y", 20.0) in line.words

def test_parse_g1_with_feedrate():
    line = parse_line("G1 X25.4 Y10.0 F500", line_number=12)
    assert GCodeWord("G", 1.0) in line.words
    assert GCodeWord("F", 500.0) in line.words

def test_parse_comment_parentheses():
    line = parse_line("G0 X0 (go to origin)", line_number=1)
    assert line.comment == "go to origin"
    assert GCodeWord("X", 0.0) in line.words

def test_parse_comment_semicolon():
    line = parse_line("G21 ; set metric", line_number=1)
    assert line.comment == "set metric"
    assert GCodeWord("G", 21.0) in line.words

def test_parse_negative_value():
    line = parse_line("G0 Z-5.0", line_number=1)
    assert GCodeWord("Z", -5.0) in line.words

def test_parse_case_insensitive():
    line = parse_line("g1 x10 y20 f300", line_number=1)
    assert GCodeWord("G", 1.0) in line.words
    assert GCodeWord("X", 10.0) in line.words

def test_parse_empty_line():
    line = parse_line("", line_number=5)
    assert line.words == []
    assert line.comment is None

def test_parse_comment_only():
    line = parse_line("(this is setup)", line_number=1)
    assert line.words == []
    assert line.comment == "this is setup"

def test_parse_string_multiline():
    code = "G21\nG90\nG0 X0 Y0"
    lines = parse_string(code)
    assert len(lines) == 3
    assert GCodeWord("G", 21.0) in lines[0].words
    assert GCodeWord("G", 90.0) in lines[1].words

def test_load_gcode_from_string():
    raw = "G21\nG1 X10"
    lines = load_gcode(raw)
    assert len(lines) == 2

def test_load_gcode_from_file(tmp_path):
    f = tmp_path / "test.nc"
    f.write_text("G21\nG0 X0\n")
    lines = load_gcode(str(f))
    assert len(lines) == 2

def test_parse_m_code():
    line = parse_line("M3 S18000", line_number=1)
    assert GCodeWord("M", 3.0) in line.words
    assert GCodeWord("S", 18000.0) in line.words
