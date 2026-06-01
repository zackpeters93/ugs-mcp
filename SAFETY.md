# SAFETY — Read This Before You Touch Anything

## This software can hurt you. Seriously.

A CNC machine is a robot that holds a spinning blade and moves it with enough force to
cut through wood, aluminum, and your fingers. When you give an AI assistant control of
that robot, you are responsible for what happens next.

This MCP server lets Claude issue motion commands to your CNC via Universal GCode Sender.
Claude is a language model. It does not know what your hands are doing. It does not know
your dog is chewing on the power cable. It does not know the workpiece is loose. It does
not feel bad if it breaks your bit, crashes your machine, or injures you.

**You are the last line of defense. Act like it.**

---

## What can go wrong

- **Unexpected motion** — If you or your AI assistant issues a jog command at the wrong
  moment, the machine moves. If your hand is in the way, the machine does not care.

- **Wrong work zero** — Set the wrong zero and your G-code runs somewhere other than where
  you think it does. Best case: ruined part. Worst case: the spindle drives into the
  fixture or the table.

- **Homing cycle surprises** — Homing drives every axis toward its limit switch at full
  speed. If a switch is broken, missing, or mis-wired, the machine drives into the frame.
  Hard.

- **Uncommanded movements from bugs** — Software has bugs. This software has bugs. If a
  bug causes an unexpected tool call, the machine moves. This is why we built the token
  system. It is not a guarantee.

- **Runaway jobs** — If a G-code file has an error (wrong units, zero feedrate, spindle
  off during a cut), `gcode_safety_check` catches most of it. Not all of it. Check your
  G-code yourself before running it.

---

## The token system: what it does and what it doesn't

Every motion command in this server requires a two-step confirmation. Claude generates a
token, shows it to you, and you must read it back before the machine moves. Claude cannot
fabricate or reuse tokens — they are generated server-side and are single-use.

**What this prevents:** Claude autonomously moving your machine without your knowledge.

**What this does NOT prevent:**
- You confirming a token without looking at the preview.
- You confirming a token while your hand is in the machine.
- A bug in this software issuing a command outside the token system.
- You ignoring this warning and doing something dumb.

Read every preview. Every single one. They are not formalities.

---

## Ground rules

1. **Never confirm a token without reading the preview.** If you're not sure what the
   preview is telling you, don't confirm it.

2. **Keep your hands out of the machine during any operation.** This sounds obvious.
   It isn't, when you're focused on a screen.

3. **Know where your E-stop is.** Before you run anything, know how to kill power to the
   machine instantly. A keyboard shortcut in UGS is not the same as a physical E-stop.

4. **Never leave a running job unattended.** Claude cannot smell smoke. You can.

5. **Run `gcode_safety_check` before every file you didn't generate yourself.** Even then,
   review it. The safety check catches common issues, not all issues.

6. **Treat every `$H` (home) command like it might be the last thing your machine does
   without a repair bill.** Make sure the travel path is clear.

---

## Liability

This software is provided under the MIT License: no warranty, no liability, no guarantees.
If your machine crashes, your bit breaks, your part is ruined, or you get hurt, that is
between you and your choices. The authors are not responsible.

If you are not comfortable accepting that risk, do not use this software.

---

## TL;DR

CNC machines are dangerous. AI assistants don't know they're dangerous. You do.
**Don't be a dumbass. Read the preview. Keep your hands clear. Know your E-stop.**
