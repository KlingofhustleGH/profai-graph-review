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

Generate a covering array over these dimensions with a combinatorial tool
(**PICT** and **ACTS** are free and support constraints; constraints matter more
than the strength `t`, because they let you exclude impossible inputs and target
suspicious ones).

Why pairwise is enough to start: empirical studies across several domains found the
large majority of failures triggered by one or two parameter values, and nearly all
by three. Escalate to 3-way for the dimensions where pairwise found a dead end.

### Step 3 — execute, don't reason

Run each generated combination through the **real pipeline** with a fake provider.
Do not ask an agent whether a combination works — agents are fluent and will tell
you a plausible story. Machines do not invent.

For each combination record: did it reach a terminal state, or did it stop? If it
stopped: at which stage, and what was missing.

Every stop is a candidate dead end.

### Step 4 — classify the stops

- **Legitimate stop.** The system correctly asked the client for something. Not a
  defect.
- **Dead end.** The stage cannot proceed and the system cannot ask, or asking would
  not help. Defect, severity `breaks_order` at minimum.
- **Retry-blind error.** The stop reports an error whose shape does not distinguish
  "retry might help" from "impossible forever". Defect — the caller will burn its
  budget. Fix shape: every validation error declares retryability explicitly.
- **No exit.** An agent is required to call a tool it cannot call, and forbidden
  from answering in text. Defect. Fix shape: wherever a tool call is forced, an
  escape hatch must exist ("cannot do this, here is why").

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
