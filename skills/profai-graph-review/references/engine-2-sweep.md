# Engine 2 — sweep over the system

Engine 2 answers a question no diff review can: **does a reachable state exist
where a stage runs and what it needs is absent?**

Two real dead ends that motivated this engine, both found by a human running the
product by hand after 1800 tests and sixteen review passes found neither:

> Full-auto mode asks no questions. The reference-card stage requires attached
> photos. The client attached none and was never asked. The order stopped forever.

> All photos on a task carried role `reference`. The crop tool numbers candidates
> from a different role set only. The valid range became `1..0` — satisfiable by no
> index. The model retried twelve times against a wall, because the error looked
> like "bad index, try another".

Neither is a bug in a line of code. Both are combinations nobody walked.

## Procedure

### Step 1 — build the requirement map

For every stage of the pipeline, record from the code (not from the spec — the spec
is what you meant, the code is what happens):

| field | meaning |
|-------|---------|
| `stage` | identifier |
| `requires_artifacts` | what must exist, by role/kind |
| `requires_fields` | what must be filled |
| `produces` | what appears after it |
| `entry_condition` | what makes this stage run |

The map is a table, kept in the repository next to the config, regenerated whenever
sentinel paths change. Building it is the agent's job; verifying it against the code
is the agent's job too — every row cites file:line.

### Step 2 — enumerate reachable states

Take the dimensions that determine what exists: mode (auto / semi-auto), content
type, presence or absence of each artifact kind, and the fields that gate branches.
Write them as a model file — `engine_2.state_model` in the config points at it:

```json
{
  "strength": 2,
  "dimensions": {
    "mode":            ["full_auto", "semi_auto"],
    "attached_photos": ["none", "some"],
    "photo_role":      ["absent", "reference", "hero", "mixed"]
  },
  "forbid": [
    { "attached_photos": "none", "photo_role": "reference" },
    { "attached_photos": "some", "photo_role": "absent" }
  ]
}
```

Generate the covering array:

```bash
python3 scripts/covering_array.py <state_model> --strength 2
```

The shipped generator is stdlib-only and needs nothing installed
(`engine_2.combinatorial_tool: "builtin"`). **PICT** and **ACTS** are supported
alternatives if you already have models in their formats; set
`combinatorial_tool` accordingly.

`forbid` entries matter more than the strength `t`: they exclude states that
cannot occur in reality, which shrinks the run count and keeps the sweep honest.
They are not a place to hide combinations you *believe* are handled — those are
the rows this engine exists to walk. The example above forbids a photo role
without photos, not full-auto without photos.

Why pairwise is enough to start: empirical studies across several domains found the
large majority of failures triggered by one or two parameter values, and nearly all
by three. Escalate to 3-way for the dimensions where pairwise found a dead end.

### Step 3 — execute, don't reason

Run each generated combination through the **real pipeline** with a fake provider,
and record what happened: did it reach a terminal state, or did it stop, and if it
stopped, at which stage and what was missing. Every stop is a candidate dead end.

The driver ships:

```bash
python3 scripts/sweep.py --model <state_model> --adapter <adapter> --out stops.json
```

It generates the rows, runs each one, re-runs every stop, classifies, prints, and
exits non-zero if any defect shape survives. What it cannot know is how to start
*your* pipeline — that is the adapter, and it is the only part you write:

```python
def run(row):
    """One combination in, where it got to out."""
    return {"outcome": "terminal"}
    # or {"outcome": "stopped", "stage": "reference_card",
    #     "missing": "...", "system_can_ask": False, "error_is_retryable": False}
```

Full contract with every field: `scripts/adapter_template.py`. A working example
over a toy pipeline: `scripts/example_adapter.py` — run it before writing yours,
it finds the two defects from the top of this file.

Three rules the adapter must obey, because they are what makes the output evidence:

- **Drive the real pipeline.** Same entry points production uses. A reimplementation
  of the logic inside the adapter tests the adapter.
- **No agent in the loop.** The adapter is code. The moment a model decides whether
  a combination "would work", step 3 has become step 0 with extra confidence.
- **No state between rows.** `scripts/sweep.py` re-runs every stop and marks it
  `not_reproducible` when the two runs disagree, so leaked state cannot be mistaken
  for a finding. Fix the leak; do not read past it.

Until your adapter exists, Engine 2 is a reading exercise: the requirement map from
step 1 still finds contradictions, but a dead end it reports has no PROOF field and
therefore is not a finding under this skill's own rule.

### Step 4 — classify the stops

`scripts/sweep.py` does this by rule, from what the adapter reported. It is not an agent's
judgement call:

| Bucket | Rule | Defect |
|---|---|---|
| **No exit** | `forced_tool_without_escape` | yes |
| **Retry-blind error** | `error_is_retryable` absent or `None` | yes |
| **Legitimate stop** | `system_can_ask` is true and neither of the above | no |
| **Dead end** | everything else that stopped | yes |
| **Not reproducible** | the re-run disagreed | fix the runner first |

Defect shapes are checked before legitimacy on purpose: a stage that asks the client
*and* reports an unretryable error as retryable is still burning the caller's budget.

What each one means:

- **Legitimate stop.** The system correctly asked the client for something.
- **Dead end.** The stage cannot proceed and the system cannot ask, or asking would
  not help. Severity `breaks_order` at minimum.
- **Retry-blind error.** The error shape does not distinguish "retry might help"
  from "impossible forever". The caller burns its budget against a wall. Fix shape:
  every validation error declares retryability explicitly.
- **No exit.** An agent is required to call a tool it cannot call, and forbidden
  from answering in text. Fix shape: wherever a tool call is forced, an escape hatch
  must exist ("cannot do this, here is why").

The last three are classes, not instances, almost always. Check the whole tree.

## Optional: formal reachability

If dead ends keep appearing after the executed sweep, the requirement model itself
may be contradictory. Two tools express this directly:

- **Alloy** — declare signatures (Order, Stage, Artifact, Mode) and facts
  (preconditions), then `run` a query for "stage active and required artifact
  absent". A found instance is your dead end with a concrete scenario. If the model
  is over-constrained, the unsat core points at the mutually exclusive constraints.
- **TLA+ / TLC** — same idea over dynamics: the pipeline as a state machine,
  checking that every reachable state is either terminal-successful or has a valid
  transition.

Both check the model, not the code. They find contradictions in what you specified;
keeping model and code in agreement remains discipline.

Worth the hours when: dead ends recur, or the stage graph is about to grow.
Not worth it for a first pass — the executed sweep is cheaper and finds the obvious
ones.

## Optional: stateful property testing

For sequences rather than combinations, a stateful model (Hypothesis
`RuleBasedStateMachine` in Python) explores orderings of user actions against
invariants such as:

- no active stage without its required artifacts
- shared-state version increases monotonically
- every order is terminal or has a valid transition

It searches for a sequence that breaks an invariant and shrinks it to a minimal
counterexample. This catches interleavings that combination coverage does not,
because the defect is in the order of actions rather than in the set of inputs.

## Output

Engine 2 findings use the same format as Engine 1, with two additions in the PROOF
field: the exact combination that produced the stop, and the stage where it
stopped. That combination becomes a permanent test.
