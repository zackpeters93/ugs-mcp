import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class GCodeWord:
    letter: str
    value: float


@dataclass
class GCodeLine:
    line_number: int
    raw: str
    words: List[GCodeWord] = field(default_factory=list)
    comment: Optional[str] = None


_WORD_PATTERN = re.compile(r"([A-Za-z])(-?\d+(?:\.\d+)?)")
_PAREN_COMMENT = re.compile(r"\(([^)]*)\)")
_SEMI_COMMENT = re.compile(r";(.*)")


def parse_line(line: str, line_number: int = 0) -> GCodeLine:
    raw = line.strip()
    comment = None

    # Extract parenthesis comment
    paren_match = _PAREN_COMMENT.search(raw)
    if paren_match:
        comment = paren_match.group(1).strip()
        raw = _PAREN_COMMENT.sub("", raw).strip()

    # Extract semicolon comment
    semi_match = _SEMI_COMMENT.search(raw)
    if semi_match:
        if comment is None:
            comment = semi_match.group(1).strip()
        raw = raw[: semi_match.start()].strip()

    words = [
        GCodeWord(letter=m.group(1).upper(), value=float(m.group(2)))
        for m in _WORD_PATTERN.finditer(raw)
    ]

    return GCodeLine(line_number=line_number, raw=line.strip(), words=words, comment=comment)


def parse_string(gcode: str) -> List[GCodeLine]:
    return [
        parse_line(line, line_number=i + 1)
        for i, line in enumerate(gcode.splitlines())
    ]


def parse_file(path: str) -> List[GCodeLine]:
    return parse_string(Path(path).read_text())


def load_gcode(file_path_or_code: str) -> List[GCodeLine]:
    """Auto-detect: if string is an existing file path, read it; else parse as raw G-code."""
    p = Path(file_path_or_code)
    if p.exists() and p.is_file():
        return parse_file(file_path_or_code)
    return parse_string(file_path_or_code)
