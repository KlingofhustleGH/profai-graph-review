"""A worked adapter over a toy pipeline, so sweep.py runs out of the box.

The toy reproduces the dead end from the README: full-auto never asks, the
reference-card stage requires photos, the client attached none, the order stops
forever. It also carries the retry-blind error from the same story.

Your adapter drives the real pipeline instead of a toy. This one exists so you can
see the machinery work before you write yours:

    python3 sweep.py --model example-model.json --adapter ./example_adapter.py
"""

STAGES = ("intake", "brief", "reference_card", "generate", "deliver")

# What the reference-card stage accepts. Anything else is a stop.
USABLE_ROLES = ("reference", "mixed")


def run(row):
    mode = row["mode"]
    photos = row["attached_photos"]
    role = row["photo_role"]

    # Full auto asks the client nothing, by design. Semi-auto can always ask.
    can_ask = mode == "semi_auto"

    if photos == "none":
        return {
            "outcome": "stopped",
            "stage": "reference_card",
            "missing": "photos with role=reference; none were attached and "
                       "full-auto never asked for them",
            "system_can_ask": can_ask,
            "error_is_retryable": False,
        }

    if role not in USABLE_ROLES:
        # Every photo carries a role the crop tool does not number, so the valid
        # index range collapses to 1..0. The error reads like a bad argument, so
        # the caller retries against a wall.
        return {
            "outcome": "stopped",
            "stage": "reference_card",
            "missing": f"a photo with role in {USABLE_ROLES}; all carry role={role}",
            "error": "index 1 out of range 1..0",
            "system_can_ask": can_ask,
            # Deliberately omitted: the error shape does not distinguish
            # "try another index" from "no index can ever work".
        }

    return {"outcome": "terminal"}
