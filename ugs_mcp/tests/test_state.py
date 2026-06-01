from ugs_mcp.gcode.parser import parse_line
from ugs_mcp.gcode.state import ModalState, apply_line


def test_initial_state():
    s = ModalState()
    assert s.units == "mm"
    assert s.positioning == "absolute"
    assert s.spindle_state == "off"
    assert s.feedrate == 0.0


def test_g20_switches_to_inches():
    s = apply_line(ModalState(), parse_line("G20"))
    assert s.units == "inch"


def test_g21_switches_to_mm():
    s = apply_line(ModalState(), parse_line("G21"))
    assert s.units == "mm"


def test_g90_absolute():
    s = apply_line(ModalState(), parse_line("G90"))
    assert s.positioning == "absolute"


def test_g91_relative():
    s = apply_line(ModalState(), parse_line("G91"))
    assert s.positioning == "relative"


def test_m3_spindle_cw():
    s = apply_line(ModalState(), parse_line("M3 S18000"))
    assert s.spindle_state == "cw"
    assert s.spindle_speed == 18000.0


def test_m5_spindle_off():
    s = ModalState(spindle_state="cw", spindle_speed=18000.0)
    s = apply_line(s, parse_line("M5"))
    assert s.spindle_state == "off"


def test_feedrate_persists():
    s = apply_line(ModalState(), parse_line("G1 X10 F500"))
    assert s.feedrate == 500.0
    s2 = apply_line(s, parse_line("G1 X20"))
    assert s2.feedrate == 500.0


def test_tool_change():
    s = apply_line(ModalState(), parse_line("T2 M6"))
    assert s.tool == 2


def test_position_updates_on_g0():
    s = apply_line(ModalState(), parse_line("G0 X10 Y20 Z-5"))
    assert s.position["X"] == 10.0
    assert s.position["Y"] == 20.0
    assert s.position["Z"] == -5.0


def test_g17_sets_xy_plane():
    s = apply_line(ModalState(), parse_line("G17"))
    assert s.plane == "XY"


def test_g54_sets_coord_system():
    s = apply_line(ModalState(), parse_line("G54"))
    assert s.coord_system == "G54"


def test_multiple_gcodes_on_one_line():
    # G90 G0 X10 Y5 is very common in real G-code - both should be applied
    s = apply_line(ModalState(), parse_line("G90 G0 X10 Y5"))
    assert s.positioning == "absolute"
    assert s.position["X"] == 10.0
    assert s.position["Y"] == 5.0
