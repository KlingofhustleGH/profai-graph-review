# PROF AI Graph Review

A two-engine defect hunt for agentic systems.

> ### ⚠️ A sweep costs about 27 agents, not 8
>
> Eight reviewers, up to four more in a second echelon, and **one adversarial agent
> per finding** — the check that keeps invented findings out is the largest single
> line item, and it grows with how productive the sweep is. On the calibration
> slice: `8 + 4 + 15 = 27` agents, the reviewers alone on the order of a million
> tokens, about an hour of wall time.
>
> Do not start one casually, and do not cut the adversarial check to save money.
> Full arithmetic in [engine-1-fanout.md](skills/profai-graph-review/references/engine-1-fanout.md#budget).

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

Written from production experience — and, until 1.1.0, never once installed: the
manifests were written from memory of the plugin schema instead of from the schema.
The skill's own rule caught its author. What ships is not what looks finished, it is
what someone ran.

## Install

> **1.1.0 — installation manifests fixed, Engine 2 ships its generator.** If you
> tried 1.0.0 and `marketplace add` failed on the first command, that was not your
> mistake: both manifests were invalid and the skill could not install for anyone.
> Worth trying again.

**Claude Code — plugin** (invokes as `/profai-graph-review:profai-graph-review`)

```bash
claude plugin marketplace add KlingofhustleGH/profai-graph-review
claude plugin install profai-graph-review@profai-graph-review
```

Both commands also work as `/plugin marketplace add ...` and `/plugin install ...`
inside a session; there, follow with `/reload-plugins`. Verify with
`claude plugin details profai-graph-review` — the component inventory must show
`Skills (1) profai-graph-review`.

**Claude Code — symlink** (invokes as `/profai-graph-review`)

```bash
git clone https://github.com/KlingofhustleGH/profai-graph-review
cd profai-graph-review
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/profai-graph-review" ~/.claude/skills/profai-graph-review
```

Picked up without a restart. The two paths coexist: the plugin skill is
namespaced, so installing both gives you two entries and no conflict.

**Codex — skill**

```bash
git clone https://github.com/KlingofhustleGH/profai-graph-review
cd profai-graph-review
mkdir -p ~/.agents/skills
ln -s "$(pwd)/skills/profai-graph-review" ~/.agents/skills/profai-graph-review
```

`~/.agents/skills/` is where Codex reads skills from. Invoke with
`$profai-graph-review`.

There is no `codex plugin marketplace add` step for this repository. Codex
marketplaces are catalogues you keep in your own `~/.agents/plugins/marketplace.json`
and point at plugin sources; this repo ships a valid `.codex-plugin/plugin.json` so
you can add it to yours, but that route is **untested by the author** — the skill
symlink above is the supported Codex path.

## Setup

Copy the config template to your repository root:

```bash
cp skills/profai-graph-review/graph-review.config.json ./graph-review.config.json
```

Then replace every `REPLACE_ME`. The one that matters is `sentinel_paths` — the
files where stages, artifact requirements, routes, and required fields are
declared.

That list drives one rule: **a diff touching a sentinel path makes Engine 2
mandatory.** Left as `REPLACE_ME` it matches nothing, the trigger silently never
fires, and the path sweep quietly stops running — which is the exact failure the
rule exists to prevent.

Also set `state_file`: the committed registry of closed classes, discarded
findings, and two counters. Without it every sweep re-litigates decisions the owner
already made.

See [references/config.md](skills/profai-graph-review/references/config.md).

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
.claude-plugin/
├── plugin.json                   Claude Code plugin manifest
└── marketplace.json              Claude Code marketplace catalogue (this repo)
.codex-plugin/plugin.json         Codex plugin manifest
skills/profai-graph-review/
├── SKILL.md                      the protocol
├── graph-review.config.json      per-project settings — template, copy to repo root
├── agents/openai.yaml            Codex presentation metadata (name, icon; no logic)
├── scripts/
│   ├── covering_array.py         Engine 2 step 2 — covering arrays, stdlib only
│   └── example-model.json        worked dimension model
└── references/
    ├── engine-1-fanout.md        charters, dispatch, echelons, budget, failure modes
    ├── engine-2-sweep.md         requirement map, combinations, dead-end classes
    ├── stopping.md               guards and the residual estimate
    ├── workflow.md               what happens around the sweep
    └── config.md                 every config key, and the state file's format
```

Engine 2 ships its generator, not its runner: driving your pipeline from a row of
dimension values is your entry points and your fixtures, and that part is work you
do once per project. `engine-2-sweep.md` states the contract it must satisfy.

## Credits

Built by PROF AI from production experience running multi-agent content pipelines.
The fresh-reviewer principle is common to several review skills; the two-engine
structure, class-versus-instance rule, and residual-based stopping criterion are
this skill's own.

MIT.
