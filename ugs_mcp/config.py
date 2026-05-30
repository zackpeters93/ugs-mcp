import os
from pathlib import Path

UGS_HOST = os.getenv("UGS_HOST", "localhost")
UGS_PORT = os.getenv("UGS_PORT", "8080")
UGS_BASE_URL = f"http://{UGS_HOST}:{UGS_PORT}"
MACROS_DIR = Path(os.getenv("MACROS_DIR", "./macros"))
RAPID_SPEED_MM_MIN = float(os.getenv("RAPID_SPEED_MM_MIN", "5000"))

WARNING_MESSAGES = {
    "jog": "** WARNING: THIS WILL MOVE YOUR MACHINE! **",
    "return_to_zero": "** WARNING: THIS WILL MOVE YOUR MACHINE! **",
    "home": "** DANGER: HOMING DRIVES ALL AXES INTO THEIR LIMIT SWITCHES AT FULL SPEED! **",
    "run_file": "** WARNING: THIS WILL START YOUR CNC JOB - SPINDLE WILL SPIN AND THINGS WILL CUT! **",
    "cancel_job": "** CAUTION: STOPPING MID-CUT WILL LEAVE A MARK ON YOUR PART! **",
    "set_work_zero": "** CAUTION: THIS WILL CHANGE YOUR WORK COORDINATES - WRONG ZERO = CRASHED BIT! **",
    "run_macro": "** HEADS UP: THIS IS JUST LIKE RUNNING A MACRO - VERIFY THE G-CODE FIRST! **",
    "connection_issue": "** DON'T BE STUPID - FIX YOUR CONNECTION BEFORE TOUCHING ANYTHING! **",
}
