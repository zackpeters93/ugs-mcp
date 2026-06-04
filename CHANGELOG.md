# Changelog

All notable changes to ugs-mcp are documented here.

## [0.1.0] — 2026-06-04

Initial public release.

### Added

- **19 MCP tools** across four categories: connection, status/job, motion, and G-code inspection
- **Two-step token safety protocol** — server generates a UUID4 token with a 2-minute TTL; Claude cannot predict, fabricate, or reuse tokens, preventing autonomous machine motion
- **Motion tools**: `ugs_jog`, `ugs_home`, `ugs_return_to_zero`, `ugs_set_work_zero` (all token-protected)
- **Job tools**: `ugs_run_file` (token-protected), `ugs_pause_job`, `ugs_cancel_job`, `ugs_get_job_status`
- **Connection tools**: `ugs_connect`, `ugs_disconnect`, `ugs_troubleshoot_connection`
- **Status tool**: `ugs_get_status` — machine state, position, feed rate, spindle speed
- **G-code inspector tools**: `gcode_translate`, `gcode_safety_check`, `gcode_estimate_time`, `gcode_list_tools`
- **Macro system**: `gcode_save_macro`, `gcode_list_macros`, `gcode_run_macro` (run is token-protected)
- **Automatic safety check** on `ugs_run_file` and `gcode_save_macro` — flags missing units, zero feedrate, spindle off during cuts
- **G-code translator** with full G/M-code glossary and modal state machine for plain-English output
- **Cycle time estimator** — returns HH:MM:SS estimate from feedrate and distance analysis
- **Tool inventory analyzer** — lists all tool changes with line numbers and usage counts
- UGS Pendant REST client (`httpx`-based) with structured error handling
- Environment variable configuration: `UGS_HOST`, `UGS_PORT`, `MACROS_DIR`, `RAPID_SPEED_MM_MIN`
- `pyproject.toml` packaging with `ugs-mcp` entry point and `hatchling` build backend
- Full documentation: `README.md`, `SAFETY.md`, `USER_GUIDE.md`
- MIT License
