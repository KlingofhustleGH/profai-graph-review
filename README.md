# PROF AI Graph Review

A two-engine defect hunt for agentic systems.

Most defect-hunting skills loop one reviewer over a diff until it stops
complaining. That converges on style and misses whole categories of defect — most
importantly the ones that live in states nobody reached.

This skill runs two engines over different territory and hands the owner a decision
list. It never fixes anything on its own.

```
        ┌─ ENGINE 1: fan-out over the diff ──┐
code ───┤                                     ├── one list ── owner decides
        └─ ENGINE 2: sweep over the system ──┘
```

**Engine 1** dispatches eight independent reviewers with disjoint charters and
fresh contexts. Fresh context is the point: a reviewer who saw the author's
reasoning inherits the author's blind spots.

**Engine 2** ignores the diff. It maps what each stage requires and asks whether a
reachable state exists where the stage runs and the requirement is absent. This
catches dead ends, retry-blind errors, and forced tool calls with no escape hatch —
none of which a diff review can see.

## Why it exists

Two defects that a real system's 1800 tests and sixteen review passes both missed,
found in minutes by a human using the product:

> Full-auto mode asks no questions. The reference-card stage requires attached
> photos. The client attached none and was never asked. The order stopped forever.

> All photos on a task carried role `reference`. The crop tool numbered candidates
> from a different role set. The valid range became `1..0`. The model retried
> twelve times against a wall, because the error read like "bad index, try another".

Neither is a bug in a line of code. Both are combinations nobody walked. Engine 2
exists for them.

## What makes it different from a review loop

| | review loop | graph review |
|---|---|---|
| shape | one reviewer, N passes | N reviewers, one pass, second echelon on density |
| territory | the diff | the diff **and** reachable states |
| fixes | applied inside the loop | owner decides, one worker applies |
| repeated defects | fixed one at a time | class → enumerating guard, closed at once |
| stopping | reviewer's score | residual estimate from reviewer overlap |
| findings | as reported | survive an adversarial kill attempt first |

## Install

**Claude Code**

```
/plugin marketplace add KlingofhustleGH/profai-graph-review
/plugin install profai-graph-review@profai-graph-review
/reload-plugins
/profai-graph-review:profai-graph-review
```

**Direct**

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/profai-graph-review" ~/.claude/skills/profai-graph-review
```

**Codex**

```
codex plugin marketplace add KlingofhustleGH/profai-graph-review
```

or directly:

```bash
mkdir -p ~/.agents/skills
ln -s "$(pwd)/skills/profai-graph-review" ~/.agents/skills/profai-graph-review
```

## Setup

Copy `graph-review.config.json` to your repository root and fill in
`sentinel_paths` — the files where stages, artifact requirements, routes, and
required fields are declared.

That list drives one rule: **a diff touching a sentinel path makes Engine 2
mandatory.** Without it, the path sweep quietly stops running once nobody
remembers when it is needed.

See `references/config.md`.

## The four non-negotiables

1. **Agents find, the owner decides, one worker fixes.** Parallel fixers overwrite
   each other, and a fix made under the pressure of a running loop is a common
   defect source.
2. **A finding without reproduction is not a finding.** Agreement between agents is
   not evidence — a dozen agents will confirm a bug that does not exist.
3. **A class is never fixed one instance at a time.** More than one instance means
   the fix is an enumerating guard.
4. **Stop on residual estimate, not on a score.** A "9.5/10" measures the
   reviewer's mood; overlap between reviewers measures what is left.

## Contents

```
skills/profai-graph-review/
├── SKILL.md                      the protocol
├── graph-review.config.json      per-project settings
├── agents/openai.yaml            Codex manifest
└── references/
    ├── engine-1-fanout.md        charters, dispatch, echelons, failure modes
    ├── engine-2-sweep.md         requirement map, combinations, dead-end classes
    ├── stopping.md               guards and the residual estimate
    ├── workflow.md               what happens around the sweep
    └── config.md                 filling in sentinel paths
```

## Credits

Built by PROF AI from production experience running multi-agent content pipelines.
The fresh-reviewer principle is common to several review skills; the two-engine
structure, class-versus-instance rule, and residual-based stopping criterion are
this skill's own.

MIT.
