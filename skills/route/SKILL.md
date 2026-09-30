---
name: route
description: Use when turning a spec+plan (e.g. from superpowers) into code and deciding which model and reasoning effort to run each plan step at — Haiku/Sonnet/Opus, inline or subagent-driven, attended or walking away unattended. Also when the user twists model/effort mid-run ("delegate", "let me drive", "rush it") or arms an unattended run.
---

# Switchboard — per-step model & effort routing

## Overview

Route each plan step to the cheapest model + effort that will still do it right. A step's model = a **base** (from the step's objective shape) plus **live shifts** (your current state, twistable mid-run). Expensive resources are **gated** — suggested, never auto-run. When you walk away, an **unattended** mode auto-decides within a ceiling you set.

**Core principle:** the plan already absorbed the design reasoning, so execution defaults cheap (Sonnet). Only two things climb the ladder — work that is *gnarly* or *load-bearing*.

**Honesty about control:** inline, this skill cannot change its own session model — that is `/model`, the user's alone. So inline routing is **advisory**: the echo tag says what a step *deserves* and the user switches. The exception is **effort**, which is self-actuated via thinking budget. The one place a model is chosen **mechanically** is the `model` parameter on a subagent dispatch.

A **ceiling** inherits this limit: inline, it cannot bind the model axis (a below-session-rung cap can't lower a model that's already running), so an inline ceiling really only governs **effort-cap + gate-lock + parking load-bearing over-ceiling steps + the model picked for a subagent dispatch**. It is *not* a per-token model-cost cap while running inline — that only exists on the subagent-dispatch axis, where it's mechanically enforced (see Enforcement level below).

## When to use

- Executing a spec+plan into code, step by step (inline or subagent-driven).
- Holding cost down without hand-picking a model for every step.
- About to walk away and wanting bounded autonomy.
- The user twists a dial mid-run ("delegate this", "I'll drive", "rush it", "effort+").

**Not for:** a one-off chat model choice; or the *planning* model itself (specs/plans want Opus regardless of this skill).

## The ladder (roles — rebind as versions change)

| Rung | Role      | Currently                         |
|------|-----------|-----------------------------------|
| 1    | Floor     | Haiku 4.5                         |
| 2    | Default   | Sonnet                            |
| 3    | Opus-fast | Opus 4.8 (1M / fast-mode capable) |
| 4    | Opus-max  | Opus 5                            |

The protocol speaks in **roles**. When models change, rebind only the "Currently" column.

## Capability scale

Each rung × effort {lo, me, hi} laid on one line, positions 0–11:

```
Haiku      Sonnet     Opus-fast   Opus-max
lo me hi │ lo me hi │ lo me hi │ lo me hi
 0  1  2   3  4  5    6  7  8    9 10 11
```

Effort inline ≈ thinking budget: **lo** = none, **me** = `think`, **hi** = `think hard` / `think harder`. (`ultrathink` sits above `hi` and is **gated** — see Gated tier.)

## Base (objective, per step)

Infer **complexity** × **blast radius** from the step + spec, map to a base rung, effort defaults to `med`:

| complexity \ blast radius | throwaway | normal    | load-bearing (auth / money / data) |
|---------------------------|-----------|-----------|------------------------------------|
| **mechanical**            | Haiku     | Haiku     | Sonnet                             |
| **normal**                | Sonnet    | Sonnet    | Opus-fast                          |
| **gnarly**                | Sonnet    | Opus-fast | Opus-max                           |

The router infers both axes and **echoes its read**; the user overrides either like any dial. **Load-bearing** = auth / money / data — read "data" to include correctness- or integrity-critical paths (e.g. a concurrency race that can corrupt or drop data), not only data at rest. When a step sits between two cells, echo your read so the user can bump it.

## Live shifts (twist anytime, mid-run)

- **Drive ↔ Delegate** — signed notches on the 0–11 scale (they cross rungs). **Delegate +** (buy first-pass correctness, hand it off). **Drive −** (stay in the loop, cheaper/faster). Shifts **sum**; opposing shifts self-cancel; clamp to [0, 11].
- **Urgency** — trims **effort only**, staying inside the current rung (never drops capability, cost-neutral). For real wall-clock speed on a hard step, *suggest* fast mode (gated) — never auto-flip it.

Mood is one dial, not many: engaged / up-for-thinking / playful → **Drive (−)**; checked-out / grinding / don't-want-to-babysit → **Delegate (+)**.

## Gated tier — suggest-only, NEVER auto

| Gate                                | Cost      | Buys                                 |
|-------------------------------------|-----------|--------------------------------------|
| `ultrathink`                        | very high | effort above `hi`                    |
| `ultracode` / multi-agent workflows | very high | exec above subagent-driven           |
| fast mode                           | 1.5×      | faster Opus output (Opus rungs only) |
| Fable                               | —         | off-ladder creative / prose          |

**Soft-gate:** if summed shifts would push past position 11, pin to 11 and *offer* a gate. Recommend it, state the cost, wait for an explicit OK. Never enter this tier on your own.

## Interaction contract

- **Kickoff (once, not a gate):** emit `Router armed · <exec> · <dials> · <mode>` reflecting the state file — a fresh start reads `Router armed · inline · dials neutral · attended`; after a re-arm it shows the restored dials/mode. This is the moment to arm unattended / set a ceiling / pre-twist a dial. Ignore it and it proceeds. If `armed: false`, emit the disarmed breadcrumb instead (see Arming & disarming) and route nothing.
- **Per step:** echo `→ Sonnet·med [normal/normal]` and proceed. Auto-zone picks are **announce-only** — do not ask.
- **Pause for exactly three things:** (1) entering the gated tier, (2) dispatching a subagent — recommend a model per agent, then ask (that ask is the permission), (3) an unattended over-ceiling **load-bearing** step (park it).
- **Exec mode** (inline vs subagent-driven) is **inherited** from the plan-execution skill, not chosen here. Suggest a swap when the work changes shape; force one on request.

## Overrides — hybrid + echo-back

Free natural language **or** a canonical shorthand; always echo the resolved state so a misread is visible and correctable:

`delegate` · `drive` · `rush` · `effort+` · `effort-` · `default` · `subagents` · `inline` · `route off` · `route on`

```
you: "ease off, I'll drive this bit"
→ Sonnet·lo  [drive −2]        ← reply "too far" / "one more down" / "good"
```

## Arming & disarming

The router can be stood down and brought back at any point — **the on-switch always works**.

- **`route off`** (also "switchboard off", "stand down") — set `armed: false`, **immediately emit** `Router: off · say "route on" to re-arm`, then **stop routing entirely**: no per-step tags, no base/shift, no gates, no unattended auto. Execute on whatever model is already active, as if the skill were absent. Disarming does **not** wipe your dials / ceiling — they persist for when you re-arm.
- **`route on`** (also "switchboard on", "route back on") — set `armed: true`, restore the persisted dial/mode state, and re-emit the kickoff line reflecting it. **Honored at any time, from any state** — disarming is never sticky beyond the user's control.
- **Stay visible while disarmed:** emit `Router: off · say "route on" to re-arm` on the `route off` turn **and** at the start of any later session that opens with `armed: false`, then route nothing. The off-state advertises its own reversal, so it can never become a silent stuck state.
- Any explicit routing instruction (a dial twist, arming unattended) implies `route on`.

## Escalation (attended)

2 failed review cycles on the same unit → **suggest** a bump (crank effort first, then climb a rung). Never auto — the user says go.

## Unattended mode ("you're on your own")

Flips suggest → auto, bounded by a ceiling the user sets before leaving.

- **Ceiling** = a point on the scale (rung·effort), e.g. `cap Opus-fast·med`. Default **Sonnet·high**. Base + stall-climb + shifts all clamp to it. The gated tier stays **locked** unless explicitly opened (`fast-mode OK`, `budget $20`).
- **Over-ceiling step → SPLIT:** *park* it if load-bearing (skip, queue for the user's return, note it); otherwise *clamp-and-attempt* at the ceiling and flag it loud.
- **Dependents of a parked/blocked step → BLOCKED:** a step that needs a parked step's output is logged `BLOCKED [depends on <step>]` and queued — even if it would otherwise sit under the ceiling. Attempt only steps whose dependencies are satisfied.
- **Route log:** append every decision (format below). **Auto-reverts** to attended on the user's next message; re-arm each session.
- **`$`-budget is advisory only** — nothing in the harness meters cumulative spend. Say so plainly; never imply a hard dollar cap.
- **Enforcement level:** on arming unattended, state whether the ceiling is **hard-enforced** on the subagent-dispatch axis only — it denies over-ceiling / gated / unspecified-model `Task`/`Agent` calls; inline model/effort stays advisory regardless (see Honesty about control). Hard requires **both** `uv` present **and** the `enforce_ceiling` PreToolUse hook actually **loaded this session** — `uv` alone is not enough to call it hard. Confirm the hook is loaded with `/hooks` (look for the `claude-switchboard` row); if `/hooks` reports unavailable (**Remote Control sessions block it**), the load state is **unverified** — say so plainly rather than assuming either way, and fall back to disk/config evidence (plugin enabled, `hooks/hooks.json` present) as a weaker signal. Never let the user assume a hard cap they don't have.

## Router state file — `.claude/router-state.md`

Maintain this per run (project-local). Rewrite on every change; re-read each step. Losing it mid-overnight-run silently resets dials / ceiling / stall counts — the exact failure unattended mode exists to prevent, and a context compaction can cause it. If the file is missing, `armed` defaults to **true** (fail toward armed — you can never be stranded off), and the armed kickoff line shows, so the reset is visible, not silent.

```
---
armed: true             # false = stood down (route off); route on re-arms at any time
exec: inline            # inline | subagent
mode: attended          # attended | unattended
ceiling: null           # unattended only, e.g. Opus-fast·med
gates_open: []          # e.g. [fast-mode]
dials:
  shift: 0              # summed drive/delegate notches (urgency is per-step, not stored)
---
stalls:
  "<unit label>": <count>
```

## Route-log line format (pin exactly)

```
[HH:MM] "<step label>" -> <role>·<effort> [<complexity>/<blast>] <note> {<mode>[ cap=<x>]}
```

```
[02:14] "wire CLI flags" -> Sonnet·me [normal/normal] base {unattended cap=Sonnet·hi}
[02:31] "token refresh"  -> PARKED     [gnarly/load-bearing] over-ceiling {unattended cap=Sonnet·hi}
[02:32] "sign release"   -> BLOCKED    [depends on "token refresh"] not attempted {unattended cap=Sonnet·hi}
[02:33] "format output"  -> Haiku·me   [mechanical/throwaway] base {unattended cap=Sonnet·hi}
```

Use `PARKED` or `BLOCKED [depends on <step>]` in place of `<role>·<effort>` when a step is not attempted.

## Quick reference

| Situation                             | Move                                                 |
|---------------------------------------|------------------------------------------------------|
| Boilerplate, throwaway                | Haiku                                                |
| Normal step, plan is solid            | Sonnet (default)                                     |
| Gnarly **or** load-bearing            | climb to Opus-fast                                   |
| Gnarly **and** load-bearing           | Opus-max                                             |
| "I don't want to babysit this"        | delegate (+notches)                                  |
| "Let me drive / I want to learn this" | drive (−notches)                                     |
| Rushed                                | urgency (−effort); fast mode only if the user OKs it |
| Sonnet stalled 2× on a unit           | suggest a bump, effort first                         |
| Walking away                          | arm unattended + set a ceiling                       |

## Red flags — STOP

- About to run `ultrathink` / `ultracode` / fast mode / Fable without an explicit OK → it is **gated**; recommend and ask first.
- Unattended and a **load-bearing** step exceeds the ceiling → **park** it, do not clamp-and-attempt.
- Treating a `$` budget as enforced → it is **advisory**; nothing meters spend.
- Claiming you switched the inline session model → you cannot; that is `/model`. You can only self-actuate **effort** inline and recommend a switch.
- Calling a ceiling "hard" on `uv` presence alone → hard requires the `enforce_ceiling` hook to be **loaded this session**, checked via `/hooks`. If `/hooks` is unavailable (Remote Control), say the load state is unverified rather than guessing.
- `armed: false` (route off) → do **not** route; emit the disarmed breadcrumb and execute normally. `route on` re-arms at any time, from any state.
- A step depends on a parked step → log it `BLOCKED`, do not attempt it just because it fits under the ceiling.
