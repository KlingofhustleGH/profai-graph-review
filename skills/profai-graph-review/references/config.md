# Configuration

`graph-review.config.json` lives in the repository root. Two entries decide how the
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

## state_file

`graph-review-state.json` carries what the skill must remember between sweeps —
the individual reviewers deliberately have no memory, so the state lives here:

```json
{
  "closed_classes": [
    {
      "shape": "writers to shared spec state without version check",
      "guard": "tests/guards/test_shared_state_writers.py",
      "closed_at": "2026-08-03",
      "instances_at_closure": 8
    }
  ],
  "slices_since_engine_2": 2,
  "last_residual": 0.4,
  "discarded_findings": [
    { "what": "...", "reason": "...", "decided_at": "2026-08-01" }
  ]
}
```

`closed_classes` stops reviewers re-reporting shapes a guard already enumerates.
`discarded_findings` stops the sweep re-surfacing what the owner already declined —
without it, every sweep re-litigates the same decisions.

## fanout

`default_reviewers: 8` is calibrated, not arbitrary: eight charters on a medium
slice returned fifteen findings in about an hour. Raise it only if charters stop
overlapping — more reviewers on the same territory return invention, not signal.

## engine_2

`force_after_n_slices` guards against drift: systems change what needs what without
anyone editing a requirement file. Five slices is a starting value.

`default_strength: 2` is pairwise. Empirically the majority of interaction failures
involve one or two parameters, most of the rest three. Escalate selectively rather
than globally — 3-way over every dimension explodes the run count for little gain.
