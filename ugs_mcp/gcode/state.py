import copy
from dataclasses import dataclass, field
from typing import Optional
from .parser import GCodeLine


@dataclass
class ModalState:
    units: str = "mm"
    positioning: str = "absolute"
    plane: str = "XY"
    feedrate_mode: str = "units_per_min"
    feedrate: float = 0.0
    spindle_state: str = "off"
    spindle_speed: float = 0.0
    tool: Optional[int] = None
    coord_system: str = "G54"
    position: dict = field(default_factory=lambda: {"X": 0.0, "Y": 0.0, "Z": 0.0})
    homed: bool = False
    work_zero_set: bool = False

    def copy(self) -> "ModalState":
        return copy.deepcopy(self)


def apply_line(state: ModalState, line: GCodeLine) -> ModalState:
    """Return a new ModalState after applying all words in a G-code line."""
    s = state.copy()

    # Build a dict for non-G, non-M words (these are single-valued per line)
    scalar_words = {w.letter: w.value for w in line.words if w.letter not in ("G", "M")}

    # Collect all G and M values (a line can have multiple)
    g_values = [w.value for w in line.words if w.letter == "G"]
    m_values = [w.value for w in line.words if w.letter == "M"]

    # Spindle speed, tool, feedrate (single-valued)
    if "S" in scalar_words:
        s.spindle_speed = scalar_words["S"]
    if "T" in scalar_words:
        s.tool = int(scalar_words["T"])
    if "F" in scalar_words:
        s.feedrate = scalar_words["F"]

    # Process all G-codes
    for g in g_values:
        if g == 20:
            s.units = "inch"
        elif g == 21:
            s.units = "mm"
        elif g == 90:
            s.positioning = "absolute"
        elif g == 91:
            s.positioning = "relative"
        elif g == 17:
            s.plane = "XY"
        elif g == 18:
            s.plane = "XZ"
        elif g == 19:
            s.plane = "YZ"
        elif g == 94:
            s.feedrate_mode = "units_per_min"
        elif g == 95:
            s.feedrate_mode = "units_per_rev"
        elif g in (54, 55, 56, 57, 58, 59):
            s.coord_system = f"G{int(g)}"
        elif g == 28:
            s.homed = True
        elif g == 92:
            s.work_zero_set = True

    # Process all M-codes
    for m in m_values:
        if m == 3:
            s.spindle_state = "cw"
        elif m == 4:
            s.spindle_state = "ccw"
        elif m == 5:
            s.spindle_state = "off"

    # Position update - check if any motion G-code was on this line
    motion_g = next((g for g in g_values if g in (0, 1, 2, 3)), None)
    if motion_g is not None:
        for axis in ("X", "Y", "Z"):
            if axis in scalar_words:
                if s.positioning == "absolute":
                    s.position[axis] = scalar_words[axis]
                else:
                    s.position[axis] += scalar_words[axis]

    return s
