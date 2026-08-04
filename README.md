# PROF AI Graph Review

A two-engine defect hunt for agentic systems.

> ### ⚠️ A sweep costs 7–17 agents, not 8
>
> Up to eight reviewers, up to four more in a second echelon, and one adversarial
> agent per **heavy** finding — `breaks_money` and `breaks_order` only.
>
> Two rules keep that from being a flat fee. **A charter with no territory in the
> slice is not dispatched** — handed a job and no material, an agent invents rather
> than reporting nothing. And **lighter findings are not refuted during the sweep**;
> they reach the list marked `NOT REFUTED`, because nothing below `breaks_order`
> becomes a code change without a separate decision from the owner, so a false one
> costs nothing until then. If the owner does pull one into the work, it is refuted
> before the fix is planned — the check is deferred, not waived.
>
> Wide slice, all charters earning their place: `8 + 4 + 5 = 17`, the reviewers
> alone on the order of a million tokens, about an hour of wall time. Narrow slice:
> around `5 + 0 + 2 = 7`. Refuting every finding regardless of severity would have
> cost 27.
>
> Full arithmetic in
> [engine-1-fanout.md](skills/profai-graph-review/references/engine-1-fanout.md#budget).

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

> **Engine 2 runs out of the box, except for one file you write.** The skill ships
> the generator and the driver: combinations, execution, re-run of every stop to
> prove it reproduces, and classification into the four defect shapes. What it
> cannot ship is the adapter — the ~30 lines that drive *your* pipeline for one
> combination, with your entry points and your fake provider.
> [`adapter_template.py`](skills/profai-graph-review/scripts/adapter_template.py) is
> the contract;
> [`example_adapter.py`](skills/profai-graph-review/scripts/example_adapter.py) is a
> working one over a toy pipeline, so you can watch the machinery find the dead end
> from this README before writing yours. Until your adapter exists, Engine 2 gives
> you combinations, not findings — a combination nobody executed has no PROOF.

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
| findings | as reported | heavy ones survive an adversarial kill attempt first |

Written from production experience — and, until 1.1.0, never once installed: the
manifests were written from memory of the plugin schema instead of from the schema.
The skill's own rule caught its author. What ships is not what looks finished, it is
what someone ran.

## Install

> **1.4.0 — setup is documented and gated.** A sweep now stops if the project is
> not configured instead of improvising. `references/setup.md` was written by
> walking the setup end to end on a production codebase; its traps section is what
> actually went wrong.
>
> **1.3.0 — Engine 2 ships a working driver; empty charters are not dispatched.**
> A sweep now costs 7–17 agents depending on the slice. Config: `default_reviewers`
> is now `max_reviewers`, plus `min_reviewers` and `engine_2.adapter`.
>
> **1.2.0 — the adversarial check is gated by severity: a sweep costs ~17 agents,
> not 27.**
>
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

The skill is not usable out of the box, and it stops rather than guessing: a sweep
whose first check finds no config refuses to run. Setup is a one-time job, done
cold — not at the moment someone wants a review, because that is when it gets
skipped.

**The short version:** ask Claude Code to do it.

```
/profai-graph-review:profai-graph-review set this project up
```

It follows [references/setup.md](skills/profai-graph-review/references/setup.md),
which is written for exactly that: what to produce, how to choose sentinel paths,
how to find the right entry point for the Engine 2 adapter, and the four traps that
a real setup on a production codebase hit before it produced an honest number.

**By hand**, copy the config template to your repository root:

```bash
# installed as a plugin
cp "$(ls -d ~/.claude/plugins/cache/profai-graph-review/profai-graph-review/*/skills/profai-graph-review | tail -1)/graph-review.config.json" ./graph-review.config.json

# installed by symlink, from your clone
cp skills/profai-graph-review/graph-review.config.json ./graph-review.config.json
```

Then replace every `REPLACE_ME`. Two keys carry the weight:

`sentinel_paths` — the files where stages, artifact requirements, routes, and
required fields are declared. They drive one rule: **a diff touching a sentinel
path makes Engine 2 mandatory.** Left as `REPLACE_ME` the list matches nothing, the
trigger silently never fires, and the path sweep quietly stops running — the exact
failure the rule exists to prevent.

`state_file` — the committed registry of closed classes, discarded findings, and
two counters. Without it every sweep re-litigates decisions the owner already made.

Engine 2 needs two more files, both project-specific: a dimension model and a ~30
line adapter. [setup.md](skills/profai-graph-review/references/setup.md) covers
both; every key is documented in
[config.md](skills/profai-graph-review/references/config.md).

## The four non-negotiables

1. **Agents find, the owner decides, one worker fixes.** Parallel fixers overwrite
   each other, and a fix made under the pressure of a running loop is a common
   defect source.
2. **No fix is planned on a finding nobody tried to kill.** Heavy findings are
   refuted before they reach the list; lighter ones when the owner pulls them into
   the work. Agreement between agents is not evidence — a dozen agents will confirm
   a bug that does not exist.
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
│   ├── sweep.py                  Engine 2 driver — run, re-run, classify. Stdlib only
│   ├── covering_array.py         Engine 2 step 2 — covering arrays, constraints
│   ├── adapter_template.py       the one file you write per project
│   ├── example_adapter.py        a working adapter over a toy pipeline
│   └── example-model.json        worked dimension model
└── references/
    ├── setup.md                  configuring the skill for a project, and its traps
    ├── engine-1-fanout.md        charters, dispatch, echelons, budget, failure modes
    ├── engine-2-sweep.md         requirement map, combinations, dead-end classes
    ├── stopping.md               guards and the residual estimate
    ├── workflow.md               what happens around the sweep
    └── config.md                 every config key, and the state file's format
```

Try Engine 2 before wiring it to anything:

```bash
cd skills/profai-graph-review/scripts
python3 sweep.py --model example-model.json --adapter ./example_adapter.py
```

It finds the dead end and the retry-blind error from the top of this README, tells
them apart from the legitimate stop, and exits non-zero. Then write your adapter.

## Credits

Built by PROF AI from production experience running multi-agent content pipelines.
The fresh-reviewer principle is common to several review skills; the two-engine
structure, class-versus-instance rule, and residual-based stopping criterion are
this skill's own.

MIT.
