# Workflow around the skill

The skill produces a list. Everything before and after is the owner's process; this
is the arrangement it was designed for.

```
build slice
   ↓
PROF AI Graph Review          ← full sweep, once per slice
   ↓
owner triages the list        ← fix now / backlog / discard
   ↓
strong model writes fix plan  ← classes become guards, not N patches
   ↓
owner approves the plan
   ↓
worker model applies fixes    ← one worker, never parallel
   ↓
short verification            ← NOT another full sweep
   ↓
live acceptance               ← owner uses the product by hand
   ↓
next slice
```

## Why the owner triages before planning

Fifteen findings are fifteen opinions about what matters. Handed straight to a
planner, they become a plan for all fifteen and the slice doubles. Half are usually
"would be nicer", not "will break".

The severity ladder makes triage fast: `breaks_money` and `breaks_order` are
decisions about whether to fix now or accept knowingly; `degrades_experience` and
`cosmetic` are candidates for the backlog.

Discarding a finding is a legitimate outcome and should be recorded with a reason —
otherwise the next sweep finds it again and you re-decide from scratch.

## Why one worker applies fixes

Parallel fixers touching the same files overwrite each other. Beyond that, a fix
written under the pressure of a running review cycle is itself a common defect
source — in one recorded sequence, pass 15 found a defect inside the fix from
pass 14.

## Why verification after fixes is short

A full sweep after every fix batch never terminates: it finds new things every time,
because there are always more things. After fixes, verify three specific claims:

1. the standard suite is green
2. the guards for the classes just closed are green
3. neighbouring behaviour is intact — the paths adjacent to what changed

A full sweep is for new code. Fixes get verification, not a hunt.

## Model assignment

- **Sweep (Engine 1 reviewers):** cheap and fast. Reviewers read and report; the
  work is breadth, not depth.
- **Adversarial check:** stronger. Killing a finding requires reasoning about why
  something cannot happen — the harder direction.
- **Fix planning:** strongest available. This is where architecture decisions hide.
- **Applying fixes:** cheap. The plan carries the thinking.

## Live acceptance is not optional

Every recorded dead end in this skill's origin was found by a human using the
product, not by any automated pass. Tests prove state is correct; a live run proves
the client received the result. These are different claims and the second does not
follow from the first.
