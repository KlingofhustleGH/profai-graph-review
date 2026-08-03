# Stopping: classes and residual estimate

A review that stops when the reviewer feels good has no stopping criterion. This
skill uses two gates, both required.

## Gate 1 — every class closed by a guard

A CLASS finding is closed only when an **enumerating guard** exists: a test that
walks the tree programmatically, finds every instance of the shape, and requires
each to be either correct or in an explicit allowlist with a written reason.

Why this gate is hard and not advisory: without it, a class is fixed one instance
at a time, and each pass finds the next one. A real sequence from production:

> Nine consecutive review passes each found one more function on the default
> database timeout. Each looked like the last. An AST guard enumerating every
> function that touches the table caught the tenth immediately, and the two passes
> after it found none.

A guard is written once and outlives the sweep. The next instance someone writes
turns it red without anyone reviewing anything.

**Guard checklist:**
- enumeration is programmatic (AST walk, import graph, grep with a defined pattern
  set), never a hand-written list of places
- allowlist entries carry a reason and an owner tag
- the guard is mutation-tested: break one instance deliberately, the guard must go
  red, restore, green
- the guard runs in the standard suite, not on request

## Gate 2 — residual estimate below one

Overlap between independent reviewers estimates how many defects remain unfound.
This is capture-recapture, borrowed from ecology and validated on software
inspections.

With two reviewers, Chapman's correction (stable even at zero overlap):

```
N̂ = ((n1 + 1) × (n2 + 1) / (m + 1)) − 1
residual = N̂ − |union|
```

`n1`, `n2` — findings per reviewer; `m` — findings both found.

With four or more independent reviewers, jackknife estimators (Mh-JK) are the
recommended family and considerably more stable. Below four reviewers the estimate
systematically **underestimates** — treat it as an order of magnitude.

**What it is good for:** telling "almost done" from "nowhere near". That question
has no other cheap answer, and a reviewer's score does not answer it at all.

**What it is not good for:** a precise defect count, or an argument that the code is
clean.

Stop when the residual stays below one across two consecutive sweeps.

## Anti-stagnation

If the residual does not fall across two sweeps while new findings keep arriving,
the diff territory is exhausted and the fan-out is re-sampling. Do not run a third
one. Switch to Engine 2 — the findings are elsewhere.

## What a stopped sweep does not mean

Stopping means the sweep found what this method finds. It does not mean the code is
correct. Three classes remain outside both engines by construction:

- defects in what the client actually experiences — found only by a human using the
  product
- defects requiring real providers, real latency, real money
- defects in prompts that only manifest with a specific model

The report says this explicitly. A clean sweep followed by "so we are done" is the
failure this skill was built to prevent.
