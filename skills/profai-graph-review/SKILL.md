---
name: profai-graph-review
description: Two-engine defect hunt for agentic systems. Engine 1 fans out independent reviewers across the diff; Engine 2 enumerates reachable states and finds dead ends no diff review can see. Findings are classified as class or instance, deduplicated, and handed to the owner as a decision list — the skill never fixes anything on its own. Use when a work slice is code-complete, before deploy, or after a dead end escapes to production.
license: MIT
---

# PROF AI Graph Review

A defect hunt built on one observation: **a reviewer reading a diff cannot see a
state nobody reached.** Most defect-hunting skills loop a single reviewer until it
runs out of things to say. That converges on style and misses whole categories.

This skill runs two engines over different territory, then stops and hands you a
decision list.

```
        ┌─ ENGINE 1: fan-out over the diff ──┐
code ───┤                                     ├── one list ── owner decides ── fixes
        └─ ENGINE 2: sweep over the system ──┘
```

Engine 1 finds bugs in what was written. Engine 2 finds bugs in what was never
written — combinations that lead nowhere, stages demanding artifacts that cannot
exist, instructions an agent cannot obey.

## Non-negotiables

1. **Agents find. The owner decides. One worker fixes.** No agent edits code during
   a sweep. Parallel fixers overwrite each other, and a fix made under the pressure
   of a running loop is itself a common defect source.
2. **A finding without reproduction is not a finding.** Every finding passes an
   adversarial check that tries to kill it. Agreement between agents is not
   evidence — a dozen agents will happily confirm a bug that does not exist.
3. **A class is never fixed one instance at a time.** If the same defect shape
   exists in more than one place, the fix is an enumerating guard, not N patches.
4. **Stop on residual estimate, not on a score.** A reviewer's "9.5/10" measures
   the reviewer's mood. Overlap between independent reviewers measures what is left.

## Engine 1 — fan-out over the diff

Eight independent reviewers, each with a fresh context and a narrow charter. Fresh
context is the point: a reviewer who saw the author's reasoning inherits the
author's blind spots.

**Default charters.** Adapt names to the project, keep the shapes:

| # | Charter | Hunts |
|---|---------|-------|
| 1 | shared state | concurrent writers, lost updates, missing version checks |
| 2 | transport & UI | platform API limits, encoding, message lifecycle |
| 3 | lifecycle | create / cancel / close / restart paths of the main entity |
| 4 | money & external calls | double charge, retries, idempotency, refunds |
| 5 | recovery | restart, orphaned work, resumption |
| 6 | gates & permissions | ordering assumptions, bypasses, auth on callbacks |
| 7 | error handling | swallowed exceptions, silent failures, missing logs |
| 8 | contracts | function promises vs actual behaviour, stale comments |

Each reviewer returns findings in the format below. Nothing else — no fixes, no
files, no refactors.

**Second echelon.** If findings cluster in one area (three or more from different
reviewers pointing at the same subsystem), send three or four more reviewers into
that area specifically. Width where it earns itself, not everywhere.

Details: `references/engine-1-fanout.md`

## Engine 2 — sweep over the system

Engine 2 does not read the diff. It builds a map of what each stage of the system
requires, then asks whether a reachable state exists where the stage runs and the
requirement is absent.

Three defect shapes it catches, all invisible to diff review:

- **Dead end.** A stage demands an artifact that cannot exist in this state.
  (Real example: full-auto mode never asks questions; the reference-card stage
  requires attached photos; the client attached none — the order stops forever.)
- **Retry-blind error.** One error shape covers "you passed a bad argument"
  (retry helps) and "this is structurally impossible" (retry never helps). The
  caller burns its retry budget against a wall.
- **No exit.** A prompt forbids a plain-text answer and mandates a tool call the
  agent cannot make in this state.

Details and procedure: `references/engine-2-sweep.md`

### When Engine 2 runs — decided by fact, not by memory

The project declares **sentinel paths** in `graph-review.config.json`: the files
where stages, artifact requirements, routes, and required fields live.

- Diff touches any sentinel path → **Engine 2 is mandatory.** It cannot be skipped.
- Diff touches none → Engine 2 is skipped, and the report says so explicitly.
- A dead end reached production → **Engine 2 is mandatory** regardless of the diff.
  A dead end escaping means the map is incomplete; rebuild all of it.
- Five slices since the last run → **Engine 2 is mandatory.** Systems drift without
  anyone editing a requirement.

Engine 2 is never limited to the diff. A dead end is born in the meeting of old
code and new state — the function that fails may not have changed in months.

## Finding format

Every finding, from either engine, in exactly this shape. A finding missing any
field is dropped by the agent that produced it, not passed on.

```
WHERE        file:line
WHAT BREAKS  the concrete scenario, not "may cause issues"
PROOF        code quote or reproduction. No proof, no finding.
SHAPE        CLASS (N instances, listed) | INSTANCE
SEVERITY     breaks_money | breaks_order | degrades_experience | cosmetic
```

**SHAPE is the field that decides the fix.** An agent claiming CLASS must list the
other instances — found by enumeration, not by memory. "There are probably others"
is an INSTANCE with a note, not a CLASS.

Severity ladder, in the owner's terms:
- `breaks_money` — a client is charged twice, or paid work is lost
- `breaks_order` — the job stops or produces the wrong thing
- `degrades_experience` — it works, but the client suffers
- `cosmetic` — the rest

## Adversarial check

Before a finding reaches the list, a separate agent tries to **kill** it: reproduce
the claim, and if it cannot, argue why the finding is wrong. Survivors are
promoted. This exists because agents are optimised for plausibility, and a fan-out
without this step scales confident invention.

## Consolidation

After the fan-out, one pass merges everything:

1. Drop findings that failed the adversarial check.
2. Merge duplicates — different reviewers describe the same defect differently.
3. Group CLASS findings, sum their instances.
4. Sort: classes first, then by severity.
5. Compute the residual estimate (below).

Output: **one list for the owner.** Not diffs, not fixes, not a plan.

## Stopping

Two gates, both required.

**Gate 1 — classes closed.** No CLASS finding may remain without an enumerating
guard. A guard is a test that walks the whole tree programmatically and requires
every instance of the shape to be either correct or in an explicit allowlist with
a written reason. Guards outlive the sweep: the next instance someone writes turns
the test red on its own.

**Gate 2 — residual estimate.** Estimated from the overlap between independent
reviewers (capture-recapture). With two reviewers, use Chapman's correction:

```
N̂ = ((n1 + 1) × (n2 + 1) / (m + 1)) − 1
residual = N̂ − |union of findings|
```

where `n1`, `n2` are each reviewer's finding counts and `m` their overlap.

Stop when the estimated residual stays below one for two consecutive sweeps. With
few reviewers this is an order-of-magnitude signal, not a precise number — it
systematically underestimates. Treat it as "close" versus "nowhere near", which is
exactly the question a reviewer's score cannot answer.

**Anti-stagnation.** If the residual does not fall across two sweeps while new
findings keep arriving, the diff territory is exhausted. Switch to Engine 2 instead
of running a third fan-out.

Details: `references/stopping.md`

## Where this skill ends

It ends at the list. It does not plan the fixes and does not apply them.

The recommended flow around it:

```
build slice → PROF AI Graph Review → owner triages the list
  → strong model writes a fix plan → owner approves
  → worker model applies → short verification → live acceptance
```

Short verification after fixes, not another full sweep: tests green, class guards
green, neighbouring behaviour intact. A full sweep is for new code, not for fixes.

Rationale in `references/workflow.md`.

## Report

The consolidated list is titled:

```
PROF AI Graph Review — <slice name>
Engine 1: N reviewers, F findings (C classes / I instances)
Engine 2: run | skipped (reason)
Residual estimate: X
```

Findings follow in the consolidation order. Nothing else in the report — no
narrative of the hunt, no self-assessment.
