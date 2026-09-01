# claude-switchboard

Per-step model & effort routing for turning a spec+plan into code. **A decision protocol, not a proxy** — it helps *you* pick which model (Haiku / Sonnet / Opus) and how much reasoning effort each plan step deserves, and lets you twist that choice live as your needs change.

## What it does

When you execute a spec+plan (e.g. from [superpowers](https://github.com/obra/superpowers)) into code, each step gets a model from:

- a **base** — inferred from the step's *complexity* × *blast radius*, and
- **live shifts** — dials you twist mid-run (drive ↔ delegate, urgency).

Expensive resources (`ultrathink`, `ultracode`, fast mode, Fable) are **gated** — suggested, never run without your explicit OK. When you walk away, an **unattended** mode auto-decides within a spending ceiling you set.

### The ladder

| Rung | Role      | Currently |
|------|-----------|-----------|
| 1    | Floor     | Haiku 4.5 |
| 2    | Default   | Sonnet    |
| 3    | Opus-fast | Opus 4.8  |
| 4    | Opus-max  | Opus 5    |

Roles are stable; rebind the model bindings as versions change.

## Usage

The skill auto-triggers when you're routing a spec+plan into code, or invoke it explicitly:

```
/claude-switchboard:route
```

Then it announces a one-time kickoff line and, per step, echoes its pick:

```
Router armed · inline · dials neutral · attended
→ Sonnet·med [normal/normal]
```

Twist a dial anytime, in plain language or shorthand:

```
delegate            # hand it off, buy first-pass correctness
drive               # stay in the loop, cheaper/faster
rush                # trim effort for speed
effort+ / effort-   # nudge thinking budget
default               # back to neutral
route off / route on  # stand the router down / bring it back (on works from any state, any time)
```

### Walking away

```
unattended, cap Sonnet·high
```

Auto-escalates within the ceiling, parks over-ceiling load-bearing steps, logs every decision, and reverts to attended on your next message. `$`-budgets are **advisory** — nothing meters cumulative spend.

## Ceiling enforcement (unattended)

Unattended mode's spend ceiling is **hard-enforced** by a `PreToolUse` hook (`hooks/enforce_ceiling.py`): it denies any subagent dispatch whose model exceeds the ceiling, names a locked gated model, or leaves the model unspecified — so a sleeping user's cap holds even against the agent's own intent or a context compaction. It governs **subagent dispatch only** (the sole mechanically controllable surface); inline model is harness-pinned, and the skill's soft honoring covers the rest.

Tests: `python tests/test_enforce_ceiling.py` (runs the hook via `uv run`, the shipped invocation).

## Requirements

- **[`uv`](https://docs.astral.sh/uv/) — required.** The enforcement hook runs via `uv run`, which is the *same command* on Windows, macOS, and Linux and needs no pre-installed Python. Without `uv` the hook can't run: enforcement falls back to the skill's soft honoring, and arming unattended reports **soft** (see below) so you're never misled about the cap.

## Honest limits

- **Inline, the skill can't switch its own session model** (that's `/model`). Inline routing is advisory; only **effort** is self-actuated, and **subagent dispatch** picks a model mechanically.
- **Dollar budgets are advisory** — no hook can meter cumulative spend; the ceiling bounds the per-dispatch model, not total cost.
- **Hard enforcement covers subagent dispatch only** — inline is harness-pinned; without `uv` only soft (protocol) honoring applies, and arming says so.

## Install

**Prerequisite:** [`uv`](https://docs.astral.sh/uv/) — required for the ceiling-enforcement hook (see [Requirements](#requirements)).

Add the marketplace and install the plugin, from within Claude Code:

```
/plugin marketplace add zyeri/claude-switchboard
/plugin install claude-switchboard@claude-switchboard
```

Or from the terminal:

```
claude plugin marketplace add zyeri/claude-switchboard
claude plugin install claude-switchboard@claude-switchboard
```

The `route` skill then auto-triggers when you route a spec+plan into code, or invoke it explicitly with `/claude-switchboard:route`. To develop locally instead, clone the repo and `/plugin marketplace add ./claude-switchboard` from its parent directory.

## License

MIT — see [LICENSE](LICENSE).
