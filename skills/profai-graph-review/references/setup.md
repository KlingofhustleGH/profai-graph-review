# Setting the skill up for a project

Read this when the config is missing, incomplete, or still has `REPLACE_ME` in it.
Setup is a one-time job, done cold, **not** at the moment someone wants a review —
that is exactly when it gets skipped.

Everything below was walked end to end on a real production codebase before being
written down. The traps section is what actually went wrong, in order.

## What setup produces

| Artifact | Where | Needed for |
|---|---|---|
| `graph-review.config.json` | repository root | both engines |
| state file | wherever `state_file` points | memory between sweeps |
| dimension model | wherever `engine_2.state_model` points | Engine 2 |
| adapter | wherever `engine_2.adapter` points | Engine 2 |

Engine 1 works after the first two. Engine 2 needs all four. Doing only the first
two is a legitimate stopping point — say so out loud rather than leaving the
Engine 2 keys pointing at files that do not exist.

## Step 1 — the config

```bash
cp "$(ls -d ~/.claude/plugins/cache/profai-graph-review/profai-graph-review/*/skills/profai-graph-review | tail -1)/graph-review.config.json" ./graph-review.config.json
```

If the skill was installed by symlink instead, copy from the repository you cloned.

### sentinel_paths — the one that matters

The question for each candidate: **if I changed this file, could a stage start
requiring something new, or stop requiring something?**

What qualifies is declarative — registries, stage definitions with preconditions,
field registries, capability catalogues. What does not qualify is a large file that
happens to contain a couple of requirement checks buried in operational code.
Guarding it means Engine 2 fires on almost every commit, which is the same as
having no rule.

Two failure modes, both silent:

- **Left as `REPLACE_ME`** — matches no diff, so the trigger never fires and Engine 2
  quietly never runs. Stop and ask the owner rather than inventing paths.
- **Forty paths** — fires every time, so the rule carries no information.

Write down the candidates you **rejected** and why, next to the list. Six weeks
later someone will propose the same file again, and the reason it was rejected is
worth more than the list itself.

Verify every path exists before moving on. A typo here fails open, not closed.

### state_file, test_command

`state_file` — the committed registry of closed classes, discarded findings, and
the two counters. Format and required sections: `config.md`. If the project already
keeps a defect registry, point at that one instead of creating a second.

`test_command` — used at the short verification step **after** fixes. The sweep
never edits code, so it never runs tests.

## Step 2 — the state file

Three sections and a counters block. `config.md` has the shape. If the project
already has a defect list, the job is adding the counters block, not migrating
anything.

## Step 3 — the dimension model

Dimensions are **what determines what exists when a stage runs** — not what the
user typed. Mode, content type, presence or absence of each artifact kind, the
fields that gate branches.

Read them out of the declarations, not out of the spec and not out of your memory
of the system. In practice this means opening the registry files you just listed as
sentinel paths and taking the actual enumerations: the pipeline keys, the route
choices, the mode aliases. Cite where each dimension came from in a comment — the
next person needs to know whether a value list is still current.

`forbid` entries exclude states the code cannot produce. Two rules:

- Forbid what is **structurally impossible**: a photo role when there are no
  photos, a branch value when no branch is selected.
- Never forbid what you believe is *handled*. Those are the rows this engine exists
  to walk. If you find yourself forbidding a combination because "that case is fine",
  stop — you are hiding the finding.

Run the generator alone first, before there is any adapter:

```bash
python3 <skill>/scripts/covering_array.py <model> --strength 2
```

Read the rows. If a row describes a state that cannot exist, the model is wrong,
not the generator.

## Step 4 — the adapter

Thirty lines, and the only part nobody can ship for you. Full contract:
`scripts/adapter_template.py`. Working example: `scripts/example_adapter.py`.

**The whole difficulty is choosing the entry point.** Get this wrong and the sweep
measures the adapter.

Find the function that **production** calls. Not the pure function underneath it,
however tempting purity is — the layer above usually adds gates, overlays, and
defaults, and skipping it manufactures dead ends that do not exist.

Three ways to find the real one, cheapest first:

1. **Look for a guard test.** A codebase that already had this bug often has a test
   forbidding direct calls to the inner function. It names the authoritative entry
   point for you, with the reasoning.
2. **Grep the callers.** The entry point is what the router, gateway, or command
   layer calls. If the pure function has one production caller and that caller wraps
   it, the wrapper is your entry point.
3. **Diff the two.** Call both on the same state. If they ever disagree, the outer
   one is authoritative and the inner one is a trap.

Then feed state through the channel **the code actually reads**. Check, do not
assume: a function taking a dict may still read attachments from the database by
id, ignoring the dict entirely. Follow the read, not the signature.

Isolate: temp home directory, temp database, set before the first import of project
code so nothing opens the production database. Fresh state per row — `scripts/sweep.py`
re-runs every stop and marks disagreement as `not_reproducible`, so leaked state
surfaces, but fix the cause.

## Step 5 — the first run

```bash
<project interpreter> <skill>/scripts/sweep.py --model <model> --adapter <adapter>
```

Use the **project's** interpreter — its virtualenv, its version. The system
`python3` is frequently years older than the code.

Then read the output against three checks before believing any of it:

- **`reached terminal: 0`** — no combination ever completes. Almost always the
  adapter, not the system: something it cannot fill, or a stage it never reaches.
- **A dead end that looks like a famous example** — that is a reason for *more*
  suspicion, not less. Verify it against the code before it goes anywhere near a
  finding.
- **Every row stopping at the same stage** — the model has a dimension the adapter
  ignores, or the adapter stops before the dimensions matter.

For each dead end, run the disconfirming test: **does anything ask the client for
the missing thing?** Grep the consumers of the requirement. If some layer surfaces
it as a question, it is a legitimate stop and your adapter is driving too low.

Mutation-check the adapter itself: supply the missing thing for real and confirm
the stop disappears. If it does not, the adapter is not feeding state where the
code reads it.

## Traps, in the order they were hit

A real setup on a production codebase, for calibration. Four problems before the
first honest number.

1. **System Python was 3.9, project code needs 3.12.** `int | None` in a module
   deep in the import chain. Cost: one confusing traceback that looked like a code
   bug. Use the project's interpreter.
2. **Attachments fed through a dict the code never reads.** The gate takes a
   deliverable dict, but reads customer videos from the `artifacts` table by
   `project_id`. The dict field was invented by the adapter. Three dead ends, all
   the adapter's.
3. **Drove the pure engine instead of the authority.** The production entry point
   wraps the pure decision with an overlay that lifts launch-gate requirements back
   into the questionnaire. Calling the inner function produced a dead end that
   reproduced the skill's own headline example almost exactly — and was false. The
   codebase already had a guard test forbidding exactly that call.
4. **The field filler could not fill artifact slots.** "Brief fully answered" was a
   lie for any slot needing an uploaded file. Visible as `reached terminal: 0`. Fill
   from the field declarations' own `example`/`enum`, and accept that artifact slots
   stay missing — that is true about the state, not a gap in the filler.

Final result of that setup: 22 combinations, 2 terminal, 20 legitimate stops, **zero
dead ends**. Which is a real result, not a failure: the questionnaire asks for
everything the launch gate requires, in that territory, at that depth. Trap 3 is
what stood between that and a confidently-reported bug.

## Definition of done

- every sentinel path exists on disk, `REPLACE_ME` gone from the config
- state file exists, is committed, has all three sections and the counters
- the generator runs and its rows describe states that can actually exist
- the adapter drives the same entry point production drives, verified by grep or
  by a guard test — not by assumption
- the sweep runs and its result survived the three checks above
- a dead end, if any, survived the disconfirming test

Anything short of this is setup in progress. Say which step you stopped at.
