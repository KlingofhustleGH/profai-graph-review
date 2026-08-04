#!/usr/bin/env python3
"""Generate a covering array over the dimensions of a state model.

Engine 2 step 2. Stdlib only, no PICT or ACTS install needed.

    python3 covering_array.py model.json [--strength 2] [--format json|tsv]

Model file:

    {
      "strength": 2,
      "dimensions": {
        "mode":   ["full_auto", "semi_auto"],
        "photos": ["none", "some"],
        "type":   ["image", "video"]
      },
      "forbid": [
        {"mode": "semi_auto", "photos": "none"}
      ]
    }

`forbid` entries are partial assignments that cannot occur in reality. A row
matching every pair of a forbid entry is impossible input and is never emitted;
tuples that only live inside forbidden rows are dropped from the coverage goal.
Do not use `forbid` to hide combinations you believe are handled — those are
exactly the rows Engine 2 exists to walk.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys


def load_model(path):
    model = json.loads(open(path, encoding="utf-8").read())
    dims = model["dimensions"]
    if len(dims) < 2:
        sys.exit("model needs at least two dimensions")
    for name, values in dims.items():
        if not values:
            sys.exit(f"dimension {name} has no values")
    return dims, model.get("forbid", []), model.get("strength", 2)


def is_allowed(row, forbid):
    """A row (possibly partial) is allowed unless it matches a whole forbid entry."""
    for rule in forbid:
        if all(row.get(k) == v for k, v in rule.items()):
            return False
    return True


def required_tuples(dims, forbid, strength):
    """Every t-way value combination that at least one legal row can carry."""
    names = list(dims)
    goal = set()
    for combo in itertools.combinations(names, strength):
        for values in itertools.product(*(dims[n] for n in combo)):
            partial = dict(zip(combo, values))
            if extend(partial, dims, forbid) is not None:
                goal.add(tuple(sorted(partial.items())))
    return goal


def extend(partial, dims, forbid):
    """Complete a partial row into a legal full row, or return None if impossible."""
    if not is_allowed(partial, forbid):
        return None
    row = dict(partial)
    for name in dims:
        if name in row:
            continue
        for value in dims[name]:
            row[name] = value
            if is_allowed(row, forbid):
                break
            del row[name]
        else:
            return None
    return row


def covered_by(row, strength):
    names = sorted(row)
    return {
        tuple(sorted((n, row[n]) for n in combo))
        for combo in itertools.combinations(names, strength)
    }


def build(dims, forbid, strength):
    goal = required_tuples(dims, forbid, strength)
    rows = []
    while goal:
        seed = dict(min(goal))
        best = None
        # Greedily fill the seed one dimension at a time, always taking the value
        # that closes the most still-uncovered tuples.
        for name in dims:
            if name in seed:
                continue
            scored = []
            for value in dims[name]:
                trial = dict(seed, **{name: value})
                full = extend(trial, dims, forbid)
                if full is None:
                    continue
                scored.append((len(covered_by(full, strength) & goal), value))
            if not scored:
                break
            seed[name] = max(scored)[1]
        best = extend(seed, dims, forbid)
        if best is None:
            sys.exit(f"no legal row carries {seed} — check `forbid`")
        new = covered_by(best, strength) & goal
        if not new:
            sys.exit("greedy fill stalled — report this model as a bug")
        goal -= new
        rows.append(best)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--strength", type=int, default=None)
    ap.add_argument("--format", choices=("json", "tsv"), default="tsv")
    args = ap.parse_args()

    dims, forbid, strength = load_model(args.model)
    strength = args.strength or strength
    if not 1 < strength <= len(dims):
        sys.exit(f"strength must be between 2 and {len(dims)}")

    rows = build(dims, forbid, strength)
    names = list(dims)
    if args.format == "json":
        print(json.dumps(rows, indent=2))
    else:
        print("\t".join(names))
        for row in rows:
            print("\t".join(str(row[n]) for n in names))
    print(f"# {len(rows)} rows, strength {strength}", file=sys.stderr)


if __name__ == "__main__":
    main()
