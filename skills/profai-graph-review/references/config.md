# Configuration

`graph-review.config.json` lives in the repository root. Copy the template from
this skill's directory and replace every `REPLACE_ME`. Two entries decide how the
skill behaves; the rest are defaults you can leave alone.

## sentinel_paths — the important one

These are the files where **what needs what** is declared: stage definitions,
artifact requirements, route tables, required-field registries.

The rule they drive: if a slice's diff touches any sentinel path, Engine 2 is
mandatory and cannot be skipped. If it touches none, Engine 2 is skipped and the
report says so.

This is why the decision is made by fact rather than by memory. Six weeks in,
nobody remembers when the path sweep is needed, and it quietly stops running.

**How to fill it in.** Ask: if I changed this file, could a stage start requiring
something new, or stop requiring something? If yes, it is a sentinel path. Typical
inhabitants:

- pipeline / route registries
- stage or step definitions with their preconditions
- field registries with required flags and conditions
- artifact role definitions
- capability catalogues (what a model or provider can do)

Do not list the whole repository. A sentinel list of forty paths means Engine 2
runs every time, which is the same as having no rule.

The shipped values are `REPLACE_ME/...` on purpose. A sweep that finds `REPLACE_ME`
still there stops and asks the owner: an unfilled list matches no diff, so the
Engine 2 trigger is silently off, which is the exact failure the sentinel rule
exists to prevent.

## state_file

The state file carries what the skill must remember between sweeps. The individual
reviewers deliberately have no memory, so it lives here and it is **committed** —
losing it means the next sweep re-litigates every decision the owner already made.

**Format: markdown.** Nothing in this skill parses the state file; the only reader
is an agent, and the state's most valuable content is the owner's reasoning — why a
finding was discarded, what a guard actually covers. That reasoning survives in
prose and dies in JSON string fields. Default: `docs/DEFECTS.md`.

Three sections are required, in this order: **open**, **closed**, **discarded**.
Head them in whatever language the project is written in — the roles are required,
the English words below are not. An agent that cannot find all three stops and says
so rather than guessing.

```markdown
# Defect registry

<!-- graph-review counters -->
slices_since_engine_2: 2
last_residual: 0.4

## Open
- **[breaks_order] <one-line shape>** · class, 3 instances · found: <date>, <how>
  Where: file:line, file:line
  What breaks: <concrete scenario>
  Owner decision: <fix now | backlog | not triaged>
  Status: open

## Closed
- **[breaks_money] <shape>** · class, 8 instances at closure · closed: <date>
  Guard: tests/guards/test_shared_state_writers.py
  Status: closed

## Discarded
- **<what>** · discarded: <date> · reason: <why the owner declined it>
```

`Closed` stops reviewers re-reporting shapes a guard already enumerates — a closed
class entry without a `Guard:` line is not closed, it is unfinished. `Discarded`
stops the sweep re-surfacing what the owner already declined.

The counters block is the one machine-read part, because two rules count:
`slices_since_engine_2` against `engine_2.force_after_n_slices`, and
`last_residual` against `stopping.residual_threshold`. Keep both on their own line
in that exact `key: value` shape. A missing counters block means the
`force_after_n_slices` rule has nothing to count from and quietly never fires.

## fanout

`max_reviewers: 8` is a **ceiling**, not a quota. Eight charters on a medium slice
returned fifteen findings, which is where the number comes from — but a charter with
no territory in the slice is not dispatched at all, so the actual count is whatever
the slice earns. Raise the ceiling only if charters stop overlapping; more reviewers
on the same territory return invention, not signal.

`min_reviewers: 3` is the floor. Below three or four the residual estimate has
almost no overlap to work from and stops carrying information — you would be saving
two agents by giving up the stopping criterion.

`second_echelon_trigger: 3` — findings from that many *distinct* reviewers pointing
at one subsystem before a second echelon is sent in. `second_echelon_size: 4` — how
many go.

Both feed the cost of a run directly: reviewers are the largest line item, and the
adversarial check adds one more agent per *heavy* finding on top. See the budget
section in `engine-1-fanout.md` before raising either.

## engine_2

`force_after_n_slices` guards against drift: systems change what needs what without
anyone editing a requirement file. Five slices is a starting value, counted from
the `slices_since_engine_2` counter in the state file.

`combinatorial_tool` selects the step-2 generator:

- `builtin` (default) — `scripts/covering_array.py`, shipped with this skill,
  stdlib only, nothing to install. Supports constraints and any strength.
- `pict` / `acts` — external tools, must be on `PATH`. Use them when you already
  have models written for one of them.

`state_model` points at the dimension model the generator reads. See
`engine-2-sweep.md` for its shape and `scripts/example-model.json` for a worked
example.

`adapter` points at the one file you write: the ~30 lines that drive your pipeline
for one combination. `scripts/adapter_template.py` is the contract,
`scripts/example_adapter.py` a working one. Both keys must be real before Engine 2
produces findings rather than a list of combinations.

`default_strength: 2` is pairwise. Empirically the majority of interaction failures
involve one or two parameters, most of the rest three. Escalate selectively rather
than globally — 3-way over every dimension explodes the run count for little gain.

## stopping

`residual_threshold` and `consecutive_sweeps_below` are Gate 2: stop when the
residual estimate stays below the threshold for that many sweeps in a row. Gate 1 —
every CLASS finding closed by an enumerating guard — has no config on purpose.

## test_command

Run at the **short verification** step after fixes, not during the sweep. The sweep
never edits code, so it never needs to run tests. If your project has no single
command, put the one that covers the changed area; the point is that the owner and
the fixing worker run the same thing.
