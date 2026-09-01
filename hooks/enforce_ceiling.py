# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""claude-switchboard — unattended ceiling enforcement (PreToolUse).

Hard-enforces the unattended-mode spend ceiling on subagent dispatches, so a
sleeping user's cap can't be crossed by the main agent's intent alone. Reads
the router state file; if the run is unattended with a ceiling set, it DENIES
any Task/Agent dispatch whose model exceeds that ceiling, names a locked gated
model, or leaves the model unspecified/inherited (unverifiable).

Scope of the guarantee (be honest about it):
  - Governs subagent dispatch only — the one mechanically controllable surface.
    Inline model is harness-pinned; effort and $-budget are NOT enforceable here.
  - Attended mode: the hook stays out entirely (the user is present).
  - No state file / no ceiling / disarmed: nothing to enforce -> allow.

stdlib only; run via `uv run`. Fails OPEN before a ceiling is confirmed (nothing
to guard), fails CLOSED once an active ceiling is known but evaluation breaks
(better to block than to overspend unattended).
"""
import sys
import os
import json
import datetime
from typing import NoReturn

# Capability scale: rung base positions (0-11); effort lo/me/hi add 0/1/2.
RUNG_BASE = {"floor": 0, "haiku": 0, "default": 3, "sonnet": 3,
             "opus-fast": 6, "opusfast": 6, "opus-max": 9, "opusmax": 9}
EFFORT_OFFSET = {"lo": 0, "low": 0, "me": 1, "med": 1, "medium": 1, "hi": 2, "high": 2}


def log(cwd, msg):
    """Append an audit line; never fatal."""
    try:
        path = os.path.join(cwd, ".claude", "router-hook.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write("[{}] {}\n".format(ts, msg))
    except Exception:
        pass


def allow() -> NoReturn:
    sys.exit(0)


def deny(cwd, reason) -> NoReturn:
    log(cwd, "DENY: " + reason)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "switchboard ceiling: " + reason,
        }
    }))
    sys.exit(0)


def parse_state(cwd):
    """Return dict of top-level frontmatter keys, or None if no state file."""
    path = os.path.join(cwd, ".claude", "router-state.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    parts = text.split("---")
    body = parts[1] if len(parts) >= 3 else text
    state = {}
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s or line[:1] in (" ", "\t"):
            continue  # skip blanks, comments, and nested (indented) keys
        key, _, val = s.partition(":")
        state[key.strip()] = val.strip()
    return state


def scale_position(rung_token, effort_token, default_effort):
    base = RUNG_BASE.get(rung_token)
    if base is None:
        return None
    off = EFFORT_OFFSET.get(effort_token, EFFORT_OFFSET[default_effort])
    return base + off


def parse_ceiling(raw):
    """'Opus-fast·med' / 'Sonnet high' / 'sonnet' -> position 0-11 (ceiling top).

    A ceiling with no effort means the whole rung is allowed -> use 'hi'.
    """
    norm = raw.strip().strip("'\"").lower().replace("·", " ").replace(".", " ")
    norm = norm.replace("opus fast", "opus-fast").replace("opus max", "opus-max")
    rung = effort = None
    for t in norm.split():
        if t in RUNG_BASE:
            rung = t
        elif t in EFFORT_OFFSET:
            effort = t
    if rung is None:
        return None
    return scale_position(rung, effort or "hi", "hi")


def model_floor(model):
    """Requested model -> ('ok'|'gated'|'unknown', cheapest scale position).

    Coarse 'opus' can't distinguish fast (4.8) from max (5) -> treat as max
    (conservative). Explicit ids ('opus-4', 'opus-5') map precisely.
    """
    m = model.strip().strip("'\"").lower()
    if "fable" in m:
        return ("gated", 12)
    if "haiku" in m:
        return ("ok", RUNG_BASE["haiku"])
    if "sonnet" in m:
        return ("ok", RUNG_BASE["sonnet"])
    if "opus" in m:
        if any(x in m for x in ("4-8", "4.8", "opus-4", "opus4", "fast")):
            return ("ok", RUNG_BASE["opus-fast"])
        return ("ok", RUNG_BASE["opus-max"])  # opus-5 / bare 'opus' -> max
    return ("unknown", 9)  # unknown model: conservative (near top)


def main():
    cwd = os.getcwd()
    data = {}
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()  # no parseable input -> nothing to enforce

    if data.get("hook_event_name") != "PreToolUse":
        allow()
    if data.get("tool_name") not in ("Task", "Agent"):
        allow()  # only govern subagent dispatch

    cwd = data.get("cwd") or cwd

    # --- fail-open zone: no confirmed active ceiling yet ---
    state = None
    try:
        state = parse_state(cwd)
    except Exception:
        allow()
    if state is None:
        allow()
    if str(state.get("armed", "true")).lower() != "true":
        allow()
    if state.get("mode", "attended").lower() != "unattended":
        allow()  # attended: the user is present
    raw_ceiling = state.get("ceiling", "null")
    if raw_ceiling.lower() in ("null", "none", ""):
        allow()  # no ceiling set
    ceiling_pos = parse_ceiling(raw_ceiling)
    if ceiling_pos is None:
        allow()  # unparseable ceiling -> can't define the bound, don't block blindly

    # --- fail-closed zone: an active ceiling exists; errors now deny ---
    try:
        gates_raw = state.get("gates_open", "[]").strip("[]").replace(" ", "")
        gates = [g.lower() for g in gates_raw.split(",") if g]
        tool_input = data.get("tool_input") or {}
        model = tool_input.get("model")

        if not model or str(model).strip().lower() == "inherit":
            deny(cwd, "unattended ceiling '{}' is active but this dispatch "
                      "specifies no explicit model (or 'inherit'); the router "
                      "must name a model at or below the ceiling."
                      .format(raw_ceiling))

        kind, pos = model_floor(model)
        if kind == "gated":
            if model.strip().lower() not in gates:
                deny(cwd, "'{}' is a gated model and the gated tier is locked; "
                          "open it explicitly before use.".format(model))
            allow()
        if pos > ceiling_pos:
            deny(cwd, "model '{}' (floor position {}) exceeds the unattended "
                      "ceiling '{}' (position {}). Choose a model at or below "
                      "the ceiling.".format(model, pos, raw_ceiling, ceiling_pos))
        allow()
    except SystemExit:
        raise
    except Exception as e:
        deny(cwd, "enforcement error ({}); blocking to stay under the "
                  "unattended ceiling.".format(type(e).__name__))


if __name__ == "__main__":
    main()
