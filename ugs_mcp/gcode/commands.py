# ugs_mcp/gcode/commands.py

GCODE_DESCRIPTIONS: dict = {
    "G0": "Rapid positioning move (no cutting, fastest speed)",
    "G1": "Linear cutting move at programmed feedrate",
    "G2": "Clockwise arc cutting move",
    "G3": "Counter-clockwise arc cutting move",
    "G4": "Dwell (pause for specified time)",
    "G10": "Set coordinate system offset",
    "G17": "Select XY cutting plane",
    "G18": "Select XZ cutting plane",
    "G19": "Select YZ cutting plane",
    "G20": "Switch units to inches",
    "G21": "Switch units to millimeters (metric)",
    "G28": "Return to machine home position",
    "G28.1": "Set machine home to current position",
    "G38.2": "Probe toward workpiece (alarm if not found)",
    "G38.3": "Probe toward workpiece (no alarm if not found)",
    "G54": "Activate work coordinate system 1 (G54)",
    "G55": "Activate work coordinate system 2 (G55)",
    "G56": "Activate work coordinate system 3 (G56)",
    "G57": "Activate work coordinate system 4 (G57)",
    "G58": "Activate work coordinate system 5 (G58)",
    "G59": "Activate work coordinate system 6 (G59)",
    "G80": "Cancel any active canned cycle",
    "G81": "Simple drilling canned cycle",
    "G82": "Drilling canned cycle with dwell at bottom",
    "G83": "Peck drilling canned cycle",
    "G90": "Switch to absolute positioning mode",
    "G91": "Switch to relative (incremental) positioning mode",
    "G92": "Set position offset at current location",
    "G92.1": "Clear all G92 offsets",
    "G94": "Set feedrate in units per minute",
    "G95": "Set feedrate in units per spindle revolution",
    "M0": "Pause program (operator must press start to continue)",
    "M1": "Optional program pause",
    "M2": "End of program",
    "M3": "Start spindle clockwise (forward)",
    "M4": "Start spindle counter-clockwise (reverse)",
    "M5": "Stop spindle",
    "M6": "Execute tool change",
    "M7": "Turn on mist coolant",
    "M8": "Turn on flood coolant",
    "M9": "Turn off all coolant",
    "M30": "End of program and return to start",
}


def describe_word(letter: str, value: float) -> str:
    """Return plain English description for a G/M/F/S/T/other word."""
    letter = letter.upper()

    if letter in ("G", "M"):
        int_val = int(value)
        frac = value - int_val
        key = f"{letter}{int_val}.{int(round(frac * 10))}" if frac > 0.05 else f"{letter}{int_val}"
        return GCODE_DESCRIPTIONS.get(key, f"Unknown {letter}-code {value}")

    if letter == "F":
        return f"Set feedrate to {value}"
    if letter == "S":
        return f"Set spindle speed to {int(value)} RPM"
    if letter == "T":
        return f"Select tool {int(value)}"
    if letter in ("X", "Y", "Z"):
        return f"Move {letter}-axis to {value}"
    if letter == "N":
        return f"Line number {int(value)}"

    return f"{letter}{value}"
