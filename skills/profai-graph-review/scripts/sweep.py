#!/usr/bin/env python3
"""Engine 2 steps 2-4: generate combinations, execute them, classify the stops.

    python3 sweep.py --model model.json --adapter ./my_adapter.py [--out stops.json]

This is the generic half. The project half is one file — an adapter exposing
`run(row) -> dict` that drives the real pipeline for one combination. See
`adapter_template.py` for the contract and `example_adapter.py` for a working one.

What this driver does that a hand-rolled loop does not:

- runs every row and records the outcome verbatim, so a stop is reproducible
- **re-runs every stop once** and fails it if the second run disagrees, because a
  stop that does not reproduce means the runner carries hidden state and its
  output is not evidence
- classifies stops into the four shapes Engine 2 hunts, by rule rather than by
  an agent's opinion
- exits non-zero when a defect shape is found, so it can sit in a test suite

It deliberately does not write findings. Agents write findings; this produces the
PROOF field they are required to carry.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import covering_array  # noqa: E402

TERMINAL = "terminal"
STOPPED = "stopped"

# Stop shapes, in classification order. The first three are defects; a legitimate
# stop is what is left once none of them applies.
DEAD_END = "dead_end"
RETRY_BLIND = "retry_blind"
NO_EXIT = "no_exit"
LEGITIMATE = "legitimate_stop"
UNSTABLE = "not_reproducible"

DEFECTS = (DEAD_END, RETRY_BLIND, NO_EXIT, UNSTABLE)


def load_adapter(spec):
    """Import an adapter from a file path or a dotted module path."""
    if spec.endswith(".py") or "/" in spec:
        path = Path(spec).resolve()
        if not path.is_file():
            sys.exit(f"adapter not found: {path}")
        mod_spec = importlib.util.spec_from_file_location("gr_adapter", path)
        module = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(module)
    else:
        module = importlib.import_module(spec)
    if not hasattr(module, "run"):
        sys.exit(f"adapter {spec} has no `run(row)` function — see adapter_template.py")
    return module


def normalise(result, row, where):
    """Reject an adapter return that cannot carry proof, loudly and early."""
    if not isinstance(result, dict):
        sys.exit(f"{where}: adapter returned {type(result).__name__}, expected dict")
    outcome = result.get("outcome")
    if outcome not in (TERMINAL, STOPPED):
        sys.exit(f"{where}: outcome must be '{TERMINAL}' or '{STOPPED}', got {outcome!r}")
    if outcome == STOPPED and not result.get("stage"):
        sys.exit(f"{where}: a stop must name the stage it stopped at")
    return {
        "row": dict(row),
        "outcome": outcome,
        "stage": result.get("stage"),
        "missing": result.get("missing"),
        "error": result.get("error"),
        "error_is_retryable": result.get("error_is_retryable", "unset"),
        "system_can_ask": bool(result.get("system_can_ask", False)),
        "forced_tool_without_escape": bool(result.get("forced_tool_without_escape", False)),
    }


def classify(rec):
    """Which of Engine 2's shapes this stop is. Defect shapes win over legitimacy:
    a stage that asks the client and *also* reports an unretryable error as
    retryable is still burning the caller's budget."""
    if rec["outcome"] == TERMINAL:
        return None
    if rec["forced_tool_without_escape"]:
        return NO_EXIT
    if rec["error_is_retryable"] == "unset" or rec["error_is_retryable"] is None:
        return RETRY_BLIND
    if rec["system_can_ask"]:
        return LEGITIMATE
    return DEAD_END


def comparable(rec):
    """The part of a record that a re-run must reproduce exactly."""
    return {k: rec[k] for k in ("outcome", "stage", "missing", "error_is_retryable",
                                "system_can_ask", "forced_tool_without_escape")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="dimension model JSON")
    ap.add_argument("--adapter", required=True, help="path to adapter .py or dotted module")
    ap.add_argument("--strength", type=int, default=None)
    ap.add_argument("--out", help="write the full record set here as JSON")
    args = ap.parse_args()

    dims, forbid, strength = covering_array.load_model(args.model)
    strength = args.strength or strength
    rows = covering_array.build(dims, forbid, strength)
    adapter = load_adapter(args.adapter)

    records = []
    for i, row in enumerate(rows):
        rec = normalise(adapter.run(dict(row)), row, f"row {i}")
        rec["shape"] = classify(rec)
        if rec["outcome"] == STOPPED:
            # A stop that does not reproduce is not evidence.
            again = normalise(adapter.run(dict(row)), row, f"row {i} (re-run)")
            if comparable(again) != comparable(rec):
                rec["shape"] = UNSTABLE
                rec["rerun"] = comparable(again)
        records.append(rec)

    if args.out:
        Path(args.out).write_text(json.dumps(records, indent=2, ensure_ascii=False))

    buckets = {}
    for rec in records:
        buckets.setdefault(rec["shape"], []).append(rec)

    print(f"rows: {len(rows)}   strength: {strength}   adapter: {args.adapter}")
    print(f"reached terminal: {len(buckets.get(None, []))}")
    for shape in (DEAD_END, RETRY_BLIND, NO_EXIT, UNSTABLE, LEGITIMATE):
        hits = buckets.get(shape, [])
        if not hits:
            continue
        print(f"\n{shape.upper()}  ({len(hits)})")
        for rec in hits:
            combo = " ".join(f"{k}={v}" for k, v in sorted(rec["row"].items()))
            detail = rec["missing"] or rec["error"] or ""
            print(f"  stage={rec['stage']:<20} {combo}")
            if detail:
                print(f"    {detail}")

    found = sum(len(buckets.get(s, [])) for s in DEFECTS)
    print(f"\n{found} rows carry a defect shape. Each one is a permanent test.")
    if UNSTABLE in buckets:
        print("not_reproducible means the runner carries hidden state — fix that first, "
              "the rest of this output is not evidence yet.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
