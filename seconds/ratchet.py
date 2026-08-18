"""Two budgets in SI seconds, each of which may only ever go down.

Cost and latency are opposed: batching buys cost with latency, and every latency win is paid
for in cost somewhere. So there are two ratchets and they are never netted against each other
-- a cost improvement cannot license a latency regression, because that trade is exactly what
keeping the goals apart exists to prevent.

Seconds because the ledger's unit is the SI second and a git timestamp is in seconds; nothing
here is a conversion anybody has to trust.

**Judged against variance, not against a point.** One number fluctuates, so a min-of-one
ratchet fails on noise and then gets ignored, which is worse than having no gate. Each record
keeps a sample, and the floor moves only when the difference is real beyond the spread.

    python3 seconds/ratchet.py check latency 1.03 0.98 1.11 1.05 0.97

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

BUDGETS = Path(__file__).with_name("seconds.json")

# Below this a sample says nothing about a distribution, so it may neither fail the gate nor
# move the floor. Five is the smallest n at which the log-space standard deviation is worth
# computing at all.
MIN_SAMPLES = 5

# How many standard errors count as real. Two is about 95% one-sided, and it is the same
# threshold in both directions on purpose: the evidence to lower the floor is the evidence to
# fail against it, so the gate cannot be easier to please than to trip.
Z = 2.0


class Regressed(Exception):
    """The measurement is worse than the floor by more than the noise."""


def _log_stats(samples: list[float]) -> tuple[float, float, int]:
    """Mean and standard deviation in log space.

    Durations are positive and right-skewed -- a run can be arbitrarily slow and cannot be
    faster than zero -- so the arithmetic mean of raw seconds is pulled around by the tail. The
    same reason `CLAUDE.md` fits session length lognormally rather than normally.
    """
    if any(s <= 0 for s in samples):
        raise ValueError("a duration of zero or less is not a measurement")
    logs = [math.log(s) for s in samples]
    sd = statistics.stdev(logs) if len(logs) > 1 else 0.0
    return statistics.fmean(logs), sd, len(logs)


def compare(baseline: list[float], candidate: list[float]) -> tuple[str, float]:
    """`("better"|"same"|"worse", z)`. Positive z means the candidate takes longer."""
    m0, s0, n0 = _log_stats(baseline)
    m1, s1, n1 = _log_stats(candidate)

    se = math.sqrt(s0 * s0 / n0 + s1 * s1 / n1)
    if se == 0:
        # No spread anywhere. Fall back to the raw comparison rather than dividing by zero;
        # this is the synthetic case, not one a real endpoint produces.
        if m1 > m0:
            return "worse", math.inf
        return ("better", -math.inf) if m1 < m0 else ("same", 0.0)

    z = (m1 - m0) / se
    if z > Z:
        return "worse", z
    if z < -Z:
        return "better", z
    return "same", z


def check(name: str, candidate: list[float], budgets: dict) -> tuple[str, float, dict]:
    """Raises `Regressed` if the candidate is worse than the floor beyond the noise.

    Returns the verdict and the budgets as they should be written back: a candidate that is
    better replaces the floor, and one that is inside the noise leaves it exactly where it is.
    A floor that drifted up on every equivocal run would ratchet the wrong way.
    """
    if name not in budgets:
        raise KeyError(f"{name} is not a budget; this service keeps {sorted(budgets)}")
    if len(candidate) < MIN_SAMPLES:
        raise ValueError(
            f"{len(candidate)} samples says nothing about a distribution; {MIN_SAMPLES} is the "
            "fewest that may move or fail this gate"
        )

    record = budgets[name]

    # No floor yet. The first measurement of a working system sets one rather than being
    # compared against nothing -- which is the order Gall's law asks for and the order this
    # file got wrong once: it recorded floors for a path that produced no output, so the gate
    # was green, precise, and measuring the absence of the work.
    if not record["samples"]:
        updated = json.loads(json.dumps(budgets))
        updated[name]["samples"] = candidate
        return "first", 0.0, updated

    verdict, z = compare(record["samples"], candidate)

    if verdict == "worse":
        raise Regressed(
            f"{name}: {statistics.fmean(candidate):.3f}s against a floor of "
            f"{statistics.fmean(record['samples']):.3f}s, z={z:.2f} -- worse beyond the spread"
        )

    updated = json.loads(json.dumps(budgets))
    if verdict == "better":
        updated[name]["samples"] = candidate
    return verdict, z, updated


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[0] != "check":
        print("usage: ratchet.py check <budget> <seconds> [<seconds> ...]", file=sys.stderr)
        return 2

    budgets = json.loads(BUDGETS.read_text())
    name, samples = argv[1], [float(x) for x in argv[2:]]
    try:
        verdict, z, updated = check(name, samples, budgets["budgets"])
    except (Regressed, KeyError, ValueError) as why:
        print(f"ratchet: {why}", file=sys.stderr)
        return 1

    if verdict == "first":
        budgets["budgets"] = updated
        BUDGETS.write_text(json.dumps(budgets, indent=2) + "\n")
        print(f"ratchet: {name} had no floor; this run is now the one to beat")
        return 0

    print(f"ratchet: {name} is {verdict} (z={z:.2f})")
    if verdict == "better":
        budgets["budgets"] = updated
        BUDGETS.write_text(json.dumps(budgets, indent=2) + "\n")
        print(f"ratchet: the {name} floor moved down; commit seconds/seconds.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
