# UGS MCP User Guide

This MCP server lets Claude control Universal GCode Sender (UGS) via its pendant REST API. Claude can read machine status, inspect G-code files, and issue motion commands - all from within a Claude Code session.

---

## Prerequisites

1. **Universal GCode Sender 2.x** must be running.
2. The **UGS Pendant plugin** must be installed and active (check via Tools > Plugins > Installed).
3. The pendant creates a local web server at `http://localhost:8080`. The MCP connects to this address.
4. Your CNC controller must be connected to UGS via serial port before issuing any motion commands.

---

## Tool Reference

Tools are grouped into four categories: Connection, Status/Job, Motion, and G-code Inspector.

---

### Connection Tools

#### `ugs_connect`
Connects UGS to the CNC machine via a serial port.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | string | required | Serial port path, e.g. `/dev/cu.usbserial-110` |
| `baud_rate` | int | 115200 | Serial baud rate |
| `firmware` | string | `GRBL` | Firmware type |

Note: If this fails, connect manually in the UGS UI and use the MCP for control only.

---

#### `ugs_disconnect`
Disconnects UGS from the CNC machine. No parameters.

---

#### `ugs_troubleshoot_connection`
Diagnostic tool. Lists available serial ports, checks pendant reachability, and suggests fixes. Run this when connection fails. No parameters.

---

### Status and Job Tools

#### `ugs_get_status`
Returns the current machine state, including:
- Machine state (IDLE, RUN, ALARM, DISCONNECTED)
- Machine position (absolute)
- Work position (G54 offset)
- Feed speed (mm/min)
- Spindle speed (RPM)

No parameters. Safe to call at any time.

---

#### `ugs_get_job_status`
Returns the current job progress, feed speed, and spindle speed. No parameters.

---

#### `ugs_pause_job`
Sends a feed hold (`!`) to pause the running job immediately. No confirmation required - stopping is always safe. No parameters.

---

#### `ugs_cancel_job`
Cancels the currently running job.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `confirmed` | bool | false | Call with `false` first to see a preview |

This uses a simple confirmed/preview flow rather than the token system because adding friction to an emergency stop is itself a safety hazard. Call with `confirmed=False` first to see current position and impact, then `confirmed=True` to cancel.

Warning: Cancelling mid-cut leaves a mark on your part. The spindle does not stop automatically - send `M5` afterward.

---

### Motion Tools

**All motion tools use the two-step token safety protocol described below.** Claude cannot move the machine without you providing a token.

---

#### `ugs_jog`
Jogs a single axis by a given distance.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `axis` | string | required | `X`, `Y`, or `Z` |
| `distance_mm` | float | required | Distance in mm (negative = reverse direction) |
| `feedrate` | float | required | Speed in mm/min |
| `confirmation_token` | string | `""` | Leave empty for preview; provide token to execute |

Example: Jog X by 10mm at 500mm/min.

---

#### `ugs_home`
Runs the GRBL homing cycle (`$H`). All axes move toward their limit switches at full speed.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `confirmation_token` | string | `""` | Leave empty for preview; provide token to execute |

Warning: Ensure nothing is in the machine's travel path before confirming.

---

#### `ugs_return_to_zero`
Rapids (G0) to the G54 work zero (X0 Y0 Z0).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `confirmation_token` | string | `""` | Leave empty for preview; provide token to execute |

---

#### `ugs_set_work_zero`
Sets the G54 work coordinate origin at the current machine position. This does **not** move the machine - it only updates the coordinate offset.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `axes` | list | `["X","Y","Z"]` | Which axes to zero |
| `confirmed` | bool | false | Call with `false` first to preview |

This uses simple confirmed/preview (not the token system) because it causes no physical movement.

---

### G-code Inspector Tools

These tools are read-only and analysis-only. They never move the machine.

---

#### `gcode_safety_check`
Scans G-code for safety problems before running. Checks for:
- Missing unit declaration (G20/G21)
- Spindle off (`M5`) during cut moves
- Zero feedrate on cut moves
- Other DANGER / WARNING / CAUTION conditions

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path_or_code` | string | File path or raw G-code string |

Run this on any G-code you did not write yourself.

---

#### `gcode_estimate_time`
Estimates cycle time from feedrates and distances. Returns time as `H:MM:SS`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path_or_code` | string | File path or raw G-code string |

---

#### `gcode_translate`
Translates G-code to plain English, line by line. Shows what each command does and the machine state at that point.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path_or_code` | string | required | File path or raw G-code string |
| `max_lines` | int | None | Limit output to N lines |

---

#### `gcode_list_tools`
Lists all tool changes (`T` words) in a G-code file, with first-use line number and usage count.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path_or_code` | string | File path or raw G-code string |

---

#### `gcode_save_macro`
Writes a named G-code macro to the macros directory after running a safety check.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | required | Macro name (used as filename) |
| `gcode_content` | string | required | Raw G-code to save |
| `description` | string | `""` | Optional description |

---

#### `gcode_list_macros`
Lists all saved macros with their names and descriptions. No parameters.

---

#### `gcode_run_macro`
Runs a saved macro by name. Uses the token safety protocol.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | required | Macro name |
| `confirmation_token` | string | `""` | Leave empty for preview; provide token to execute |

---

#### `ugs_run_file`
Streams a G-code file to the machine. Automatically runs `gcode_safety_check` during the preview step. Uses the token safety protocol.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string | required | Absolute path to the `.nc` or `.gcode` file |
| `confirmation_token` | string | `""` | Leave empty for preview; provide token to execute |

---

## Safety Workflow: The Token System

### The Problem It Solves

The original design used a `confirmed: bool` parameter. The fundamental flaw: Claude controls that boolean. Claude could call `ugs_jog(axis="X", distance_mm=100, confirmed=True)` without asking you anything. Nothing in the code prevented it.

### How Tokens Work

Every motion tool (jog, home, return to zero, run file, run macro) uses a two-step protocol enforced at the server level:

**Step 1 - Preview**

Claude calls the tool with no token. The server:
- Shows a preview of exactly what will happen (axis, distance, file, safety warnings, etc.)
- Generates a random 8-character token (e.g. `A3F8B2C1`) and stores it server-side
- Returns the token to Claude with instructions to show it to you

Claude will display something like:

```
PREVIEW - no movement yet:
  Axis:      X
  Distance:  10mm
  Feedrate:  500mm/min
  Current machine pos: X=0.000  Y=0.000  Z=0.000
  New X position (approx): 10.000mm

To confirm, provide this token to the user: [A3F8B2C1]
Ask them to confirm by reading the token back to you.
Token expires in 2 minutes and is single-use.
```

**Step 2 - Confirm**

You read the preview and, if you agree, tell Claude the token (e.g. "yes, A3F8B2C1"). Claude then calls the tool again with `confirmation_token="A3F8B2C1"`. The server:
- Looks up the token in its internal registry
- Verifies it has not expired (2-minute TTL)
- Deletes it immediately (single-use - it cannot be reused)
- Executes the motion

### Why Claude Cannot Bypass This

- Tokens are generated by `uuid4()` server-side. Claude cannot predict or fabricate a valid token.
- The token only exists in the server's memory. Claude has no access to the registry.
- The only way to get a valid token into Claude's context is through the preview call.
- The only way to get it into the execute call is if you type it back.

If Claude tries to call an execute with a guessed or repeated token, it gets:

```
INVALID OR EXPIRED TOKEN - movement blocked.
Call this tool without a token to generate a new preview and token.
```

### Token Properties

| Property | Value |
|----------|-------|
| Format | 8 uppercase hex characters |
| Expiry | 2 minutes from generation |
| Uses | Single-use (consumed on first valid execute) |
| Storage | Server memory only |

### What Is NOT Token-Protected

| Tool | Reason |
|------|--------|
| `ugs_pause_job` | Stops movement - no friction needed |
| `ugs_cancel_job` | Emergency stop - token friction would be dangerous |
| `ugs_set_work_zero` | No physical movement |
| All inspector tools | Read-only, no machine interaction |
| `ugs_get_status` | Read-only |
| `ugs_connect` / `ugs_disconnect` | No machine movement |

---

## Typical Workflows

### First Connection

1. Plug in the CNC via USB
2. Ask Claude: "What serial ports are available?" - Claude calls `ugs_troubleshoot_connection`
3. Identify your CNC port (e.g. `cu.usbserial-110`)
4. Ask Claude to connect - Claude calls `ugs_connect`
5. Verify with `ugs_get_status` - should show IDLE

### Before Running a File

1. `gcode_safety_check` - scan for problems
2. `gcode_estimate_time` - know how long it will take
3. `gcode_list_tools` - confirm which tools are needed
4. `ugs_run_file` - preview, get token, confirm with token

### Jogging

1. Call `ugs_jog` with no token to see preview and get token
2. Read the preview - check axis, distance, and resulting position
3. Confirm by providing the token
4. Machine moves

### Emergency Stop

- "Pause" - Claude calls `ugs_pause_job` immediately (no confirmation needed)
- "Cancel" - Claude calls `ugs_cancel_job(confirmed=False)` for a preview, then `confirmed=True` to cancel
- You can always hit the stop button in the UGS UI directly - the MCP has no control over that

---

## Limitations

- **Connect/disconnect** cannot be fully automated via pendant API on some UGS versions - use the UGS UI if the tool fails.
- **Job progress percentage** is not available via the pendant API - check the UGS UI directly.
- **The MCP cannot stop you from issuing commands through the UGS UI** - the token system only governs Claude's actions.
- **Tokens live in server memory** - restarting the MCP server clears all pending tokens.
