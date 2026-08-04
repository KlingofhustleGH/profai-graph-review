"""Engine 2 adapter — the one file per project you have to write.

Copy this next to your tests, fill in `run`, point sweep.py at it:

    python3 sweep.py --model model.json --adapter ./engine2_adapter.py

Everything else in Engine 2 is generic and ships with the skill. This file is
where your entry points, fixtures, and fake provider live.

Three rules the adapter must obey. Break one and the output stops being evidence:

1. **Drive the real pipeline.** Same entry points production uses. A reimplementation
   of the pipeline's logic here tests this file, not the system.
2. **No model in the loop.** Do not ask an agent whether the combination works.
   Agents are fluent and will tell you a plausible story. Machines do not invent.
3. **No state between rows.** Fresh fixtures each call. sweep.py re-runs every stop
   and fails it if the two runs disagree, so leaked state surfaces as
   `not_reproducible` rather than as a finding — but fix the cause, not the symptom.
"""


def run(row):
    """Drive one combination through the pipeline and report where it got to.

    `row` is one line of the covering array: {"mode": "full_auto",
    "attached_photos": "none", ...} — the keys are your model's dimensions.

    Return a dict. Reached the end:

        {"outcome": "terminal"}

    Stopped somewhere:

        {
          "outcome": "stopped",
          "stage": "reference_card",          # required — where it stopped

          "missing": "photos with role=reference",   # what the stage wanted
          "error": "index 1 out of range 1..0",      # what it actually reported

          # Does the system have a way to obtain what is missing from this state —
          # ask the client, fall back, skip the stage? False here with no defect
          # flags below is a DEAD END.
          "system_can_ask": False,

          # Does the error itself distinguish "retry might help" from "impossible
          # forever"? True or False if it does. Leave it out, or None, if it does
          # not — that is a RETRY-BLIND error, and the caller will burn its budget
          # against a wall. Guessing here defeats the check.
          "error_is_retryable": False,

          # Is an agent required to call a tool it cannot call here, with no
          # plain-text escape hatch? That is a NO EXIT.
          "forced_tool_without_escape": False,
        }

    `stage` is required for a stop. The rest is optional, but an omitted
    `error_is_retryable` is read as "the error does not say", which is itself one
    of the defect shapes — that default is deliberate, not an oversight.
    """
    raise NotImplementedError("write the adapter for your pipeline")
