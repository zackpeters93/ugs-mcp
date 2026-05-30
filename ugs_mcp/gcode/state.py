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
    words = {w.letter: w.value for w in line.words}

    # Spindle speed
    if "S" in words:
        s.spindle_speed = words["S"]

    # Tool
    if "T" in words:
        s.tool = int(words["T"])

    # Feedrate
    if "F" in words:
        s.feedrate = words["F"]

    # G-codes
    g = words.get("G")
    if g is not None:
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

    # M-codes
    m = words.get("M")
    if m is not None:
        if m == 3:
            s.spindle_state = "cw"
        elif m == 4:
            s.spindle_state = "ccw"
        elif m == 5:
            s.spindle_state = "off"

    # Position update for motion commands
    if g in (0, 1, 2, 3):
        for axis in ("X", "Y", "Z"):
            if axis in words:
                if s.positioning == "absolute":
                    s.position[axis] = words[axis]
                else:
                    s.position[axis] += words[axis]

    return s
