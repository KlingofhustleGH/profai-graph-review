# Engine 1 — fan-out over the diff

## Why fan-out instead of a loop

A single reviewer looping until it stops complaining converges on style. Worse, it
starts finding defects in its own earlier fixes: a fix made under the pressure of a
running loop is a well-documented defect source. Iterative review also has no
memory of which defect shapes it already covered, so it re-samples the same
territory with different luck each pass.

Fan-out replaces luck with coverage. Eight reviewers with disjoint charters look at
disjoint things by construction, and the overlap between them is what lets you
estimate what is left.

## Preparation

Before dispatching, prepare three things:

1. **Scope.** The diff range for this slice — commit range or file list. Reviewers
   read the whole repository but judge only the slice.
2. **Context files.** Spec, design doc, or plan for the slice. Reviewers read these
   from disk. Never pass the author's conversation.
3. **Prior classes.** The list of defect classes already closed by guards, from the
   `Closed` section of the state file (`state_file` in `graph-review.config.json`).
   Reviewers skip these — a guard already enumerates them.

## Dispatch

Each reviewer gets:

- its charter (one line, from the table in SKILL.md)
- the scope
- the finding format
- the non-negotiables: read only, no edits, no files except the report
- prior closed classes

Each reviewer must NOT get:

- the author's reasoning or conversation
- other reviewers' findings
- the plan the code was written from, unless it is a released spec document

## Charter design

The default eight cover the shapes that recur across agentic systems. When adapting:

- **One charter, one shape.** "Quality" is not a charter. "Concurrent writers to
  shared state" is.
- **Charters should not overlap.** Overlap wastes budget and inflates the residual
  estimate by making findings correlate.
- **Include a boring one.** Error handling and swallowed exceptions look unglamorous
  and produce some of the most expensive findings — a silently swallowed exception
  is invisible until it is expensive.

## Second echelon

Trigger: three or more findings from different reviewers pointing at the same
subsystem. That is evidence of density, not coincidence.

Send three or four reviewers into that subsystem with narrower charters derived
from what the first echelon found. Example: if the first echelon found two races
around card display, the second echelon hunts "every path that can display or
modify a card", "every path that can close an interaction", "restart behaviour of
the card lifecycle".

Do not send a second echelon everywhere. Width costs budget and, past a point,
returns invention rather than signal.

## Budget

**A sweep is not eight agents.** The reviewers are the smaller half of the bill.

```
agents per sweep = default_reviewers
                 + second_echelon_size   (when the trigger fires)
                 + one adversarial agent per finding
```

On the calibration slice that produced the defaults — eight reviewers, fifteen
findings, one second echelon — that is `8 + 4 + 15 = 27` agents, over three times
the reviewer count. The adversarial check is the largest single line item, and it
grows with how *productive* the sweep is: a good fan-out costs more, not less.

Tokens do not scale with agent count. Reviewers read broadly and are individually
expensive; on that slice the reviewers alone ran on the order of a million tokens.
Adversarial agents each read one claim's neighbourhood and are individually cheap,
but there are roughly twice as many of them. Wall time was about an hour, most of
it in the fan-out, which runs in parallel; the adversarial pass adds to it.

Treat every number here as this project's measurement, not yours. **Measure your
first run and calibrate** — the figure that matters is findings per unit cost, and
it drops fast once charters start to overlap.

If budget is tight, cut charters, not proof requirements. Six reviewers producing
reproduced findings beat twelve producing speculation. Do not cut the adversarial
check to save money: a fan-out without it scales confident invention, and the
findings it lets through cost more than it did.

## Common failure modes

**Reviewers report style.** Tighten charters and enforce the SEVERITY field — a
finding that cannot be assigned a severity above `cosmetic` usually is not one.

**Reviewers report the same thing eight times.** Charters overlap. Redesign them.

**Reviewers claim CLASS without listing instances.** Reject and return. A claimed
class without an enumeration is a guess, and guesses become the wrong kind of work:
a guard built on a guessed class either over-blocks or misses.

**Findings are all in the newest file.** Reviewers gravitate to what changed most.
Add a charter aimed explicitly at the interaction between new code and untouched
code — that seam is where the expensive defects live.
