#!/usr/bin/env python3
"""Behavior tests for hooks/enforce_ceiling.py.

Runs the hook exactly as the plugin ships it — `uv run <script>` — against a
temp router-state.md, and classifies each dispatch as:
  DENY  : stdout carries hookSpecificOutput.permissionDecision == "deny"
  ALLOW : clean pass (exit 0, no deny JSON, no stderr)
  ERROR : anything else (crash, missing script, stderr) — never a valid outcome

ALLOW asserts exit 0 AND empty stderr, so a missing/broken implementation
classifies as ERROR (not ALLOW) — every case has teeth, including the
allow-cases. Uses Python's tempfile for native paths (Git Bash `/tmp/...`
MSYS paths are unreadable by native Windows Python).
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "hooks", "enforce_ceiling.py")


def write_state(dir_, armed="true", mode="unattended", ceiling="Sonnet·high", gates="[]"):
    d = os.path.join(dir_, ".claude")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "router-state.md"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent("""\
            ---
            armed: {armed}
            exec: subagent
            mode: {mode}
            ceiling: {ceiling}
            gates_open: {gates}
            dials:
              shift: 0
            ---
            stalls:
            """).format(armed=armed, mode=mode, ceiling=ceiling, gates=gates))


def run(cwd, tool_name="Agent", model="__omit__", event="PreToolUse"):
    tool_input = {"subagent_type": "general-purpose", "prompt": "x"}
    if model != "__omit__":
        tool_input["model"] = model
    payload = {"hook_event_name": event, "tool_name": tool_name,
               "cwd": cwd, "tool_input": tool_input}
    p = subprocess.run(["uv", "run", HOOK], input=json.dumps(payload),
                       capture_output=True, text=True)
    if p.stdout.strip():
        try:
            dec = json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"]
            if dec == "deny":
                return "DENY"
        except Exception:
            return "ERROR"
    if p.returncode == 0 and not p.stderr.strip():
        return "ALLOW"
    return "ERROR"


CASES = [
    # (label, kwargs-for-state, kwargs-for-run, expected)
    ("opus over Sonnet·high ceiling",        dict(ceiling="Sonnet·high"),        dict(model="opus"),            "DENY"),
    ("sonnet under ceiling",                 dict(ceiling="Sonnet·high"),        dict(model="sonnet"),          "ALLOW"),
    ("haiku under ceiling",                  dict(ceiling="Sonnet·high"),        dict(model="haiku"),           "ALLOW"),
    ("fable gated + locked",                 dict(ceiling="Sonnet·high"),        dict(model="fable"),           "DENY"),
    ("no model specified",                   dict(ceiling="Sonnet·high"),        dict(),                        "DENY"),
    ("model=inherit (unverifiable)",         dict(ceiling="Sonnet·high"),        dict(model="inherit"),         "DENY"),
    ("non-subagent tool (Bash) ignored",     dict(ceiling="Sonnet·high"),        dict(tool_name="Bash", model="opus"), "ALLOW"),
    ("wrong event (PostToolUse) ignored",    dict(ceiling="Sonnet·high"),        dict(model="opus", event="PostToolUse"), "ALLOW"),
    ("explicit opus-4-8 under Opus-fast·med", dict(ceiling="Opus-fast·med"),     dict(model="claude-opus-4-8"), "ALLOW"),
    ("bare opus under Opus-fast·med (conservative)", dict(ceiling="Opus-fast·med"), dict(model="opus"),        "DENY"),
    ("fable allowed when gate open",         dict(ceiling="Opus-max·high", gates="[fable]"), dict(model="fable"), "ALLOW"),
    ("attended mode ignored",                dict(mode="attended", ceiling="Sonnet·high"), dict(model="opus"),  "ALLOW"),
    ("disarmed ignored",                     dict(armed="false", ceiling="Sonnet·high"), dict(model="opus"),    "ALLOW"),
    ("no ceiling set",                       dict(ceiling="null"),               dict(model="opus"),            "ALLOW"),
]


def main():
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for label, state_kw, run_kw, want in CASES:
            write_state(tmp, **state_kw)
            got = run(tmp, **run_kw)
            results.append((label, got, want))
    with tempfile.TemporaryDirectory() as empty:
        results.append(("no state file", run(empty, model="opus"), "ALLOW"))

    passed = True
    for label, got, want in results:
        ok = got == want
        passed &= ok
        print("  [{}] {}: got {}, want {}".format("PASS" if ok else "FAIL", label, got, want))
    print("\nRESULT:", "ALL PASS" if passed else "FAILURES ABOVE")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
