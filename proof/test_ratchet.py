"""What the ratchet lets through, and what it stops.

The cases that matter are the ones where a person would want to argue: a run that is a bit
slower because the machine was busy, and a run that is genuinely worse. A gate that cannot tell
them apart is one that gets switched off.

SPDX-License-Identifier: Apache-2.0
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from seconds.ratchet import MIN_SAMPLES, Regressed, check, compare  # noqa: E402

FAILURES = []


def report(ok, what):
    print(f"{'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        FAILURES.append(what)


BASE = [1.195, 1.198, 1.193, 1.201, 1.190]
BUDGETS = {
    "latency_seconds": {"samples": list(BASE)},
    "cost_seconds": {"samples": [0.218, 0.188, 0.173, 0.176, 0.163]},
}


def main():
    # Noise. The same distribution measured again must neither fail nor move the floor: a gate
    # that ratchets on noise walks its own floor down until everything fails.
    verdict, _ = compare(BASE, [1.196, 1.192, 1.203, 1.188, 1.199])
    report(verdict == "same", "a re-measurement of the same thing is neither better nor worse")

    # A real improvement, well outside the spread.
    verdict, _ = compare(BASE, [0.81, 0.79, 0.83, 0.80, 0.82])
    report(verdict == "better", "a real improvement is recognised")

    # A real regression.
    verdict, _ = compare(BASE, [1.61, 1.58, 1.63, 1.60, 1.62])
    report(verdict == "worse", "a real regression is recognised")

    # The floor moves only when it is beaten, and never on an equivocal run.
    v, _, updated = check("latency_seconds", [0.81, 0.79, 0.83, 0.80, 0.82], BUDGETS)
    report(v == "better" and updated["latency_seconds"]["samples"][0] == 0.81,
           "beating the floor lowers it")
    v, _, updated = check("latency_seconds", [1.196, 1.192, 1.203, 1.188, 1.199], BUDGETS)
    report(v == "same" and updated["latency_seconds"]["samples"] == BASE,
           "an equivocal run leaves the floor exactly where it was")

    try:
        check("latency_seconds", [1.61, 1.58, 1.63, 1.60, 1.62], BUDGETS)
        report(False, "a regression fails the gate")
    except Regressed as why:
        report("worse beyond the spread" in str(why), "a regression fails the gate, with the z")

    # The two budgets are independent. A cost improvement must not license a latency
    # regression: that trade is the whole reason there are two of them.
    cheap_and_slow = dict(BUDGETS)
    try:
        check("cost_seconds", [0.09, 0.088, 0.091, 0.089, 0.09], cheap_and_slow)
        check("latency_seconds", [1.61, 1.58, 1.63, 1.60, 1.62], cheap_and_slow)
        report(False, "halving cost does not buy a latency regression")
    except Regressed:
        report(True, "halving cost does not buy a latency regression")

    # An empty floor is set by the first measurement, not compared against nothing. This is
    # the case that was got wrong: floors were recorded for a path that produced no output.
    empty = {"latency_seconds": {"samples": []}}
    v, _, updated = check("latency_seconds", [171.3, 170.8, 172.1, 171.0, 171.6], empty)
    report(v == "first" and len(updated["latency_seconds"]["samples"]) == 5,
           "the first measurement of a working system sets the floor")

    # And it still may not be set from too little evidence.
    try:
        check("latency_seconds", [171.3], {"latency_seconds": {"samples": []}})
        report(False, "an empty floor still needs enough samples")
    except ValueError:
        report(True, "an empty floor is not set from a single run either")

    # Too small a sample says nothing, so it may neither fail the gate nor move it.
    try:
        check("latency_seconds", [0.4] * (MIN_SAMPLES - 1), BUDGETS)
        report(False, "a sample below the minimum is refused")
    except ValueError as why:
        report("says nothing about a distribution" in str(why),
               "a sample too small to mean anything is refused, even a flattering one")

    # A budget nobody keeps is a typo, not a pass.
    try:
        check("throughput", BASE, BUDGETS)
        report(False, "an unknown budget is refused")
    except KeyError:
        report(True, "an unknown budget is refused rather than silently skipped")

    # The file on disk must be the shape the gate reads, or every check above is theatre.
    disk = json.loads((ROOT / "seconds/seconds.json").read_text())["budgets"]
    report(set(disk) == {"latency_seconds", "cost_seconds"},
           "seconds.json keeps exactly the two opposed budgets")
    # A floor is either absent -- no working system measured through it yet -- or rests on
    # enough runs to have a spread. What is forbidden is a thin floor, because that is the one
    # that looks like evidence and behaves like noise.
    report(all(len(b["samples"]) == 0 or len(b["samples"]) >= MIN_SAMPLES for b in disk.values()),
           "a recorded floor is either absent or rests on enough samples")

    # And the working system it will be measured against is named, with a real artefact.
    working = json.loads((ROOT / "seconds/seconds.json").read_text())["working"]
    report(working["run"]["seconds"] > 0 and working["run"]["layers"],
           "the working system is recorded with its own timing and what it produced")

    print("ratchet: FAILED" if FAILURES else "ratchet: all checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
