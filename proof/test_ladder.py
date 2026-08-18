"""What the ladder allows, and what it refuses.

Every case here is a step somebody would want to take in a hurry, which is the only time the
rule matters.

SPDX-License-Identifier: Apache-2.0
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ladder.ladder import NotOnTheLadder, check  # noqa: E402

FAILURES = []


def ok(proposed, tags, what):
    try:
        check(proposed, tags)
        print(f"ok   {what}")
    except NotOnTheLadder as why:
        print(f"FAIL {what}: refused with {why}")
        FAILURES.append(what)


def refused(proposed, tags, what, needle=None):
    try:
        check(proposed, tags)
        print(f"FAIL {what}: allowed")
        FAILURES.append(what)
    except NotOnTheLadder as why:
        if needle and needle not in str(why):
            print(f"FAIL {what}: refused for the wrong reason -- {why}")
            FAILURES.append(what)
        else:
            print(f"ok   {what}")


def main():
    ok("v0.1.0-dev.1", [], "the first rung of a new version needs nothing below it")
    ok("v0.1.0-dev.2", ["v0.1.0-dev.1"], "a rung may be climbed again")
    ok("v0.1.0-beta.1", ["v0.1.0-dev.1"], "beta follows dev")
    ok("v0.1.0-rc.1", ["v0.1.0-dev.1", "v0.1.0-beta.1"], "rc follows beta")
    ok("v0.1.0", ["v0.1.0-dev.1", "v0.1.0-beta.1", "v0.1.0-rc.1"], "release follows rc")
    ok("v0.2.0-dev.1", ["v0.1.0"], "a new version starts at dev again")

    refused("v0.1.0", ["v0.1.0-dev.1"], "release may not skip beta and rc", "skips beta, rc")
    refused("v0.1.0-rc.1", ["v0.1.0-dev.1"], "rc may not skip beta", "skips beta")
    refused("v0.1.0-beta.1", [], "beta may not skip dev", "skips dev")
    refused("v0.1.0-dev.3", ["v0.1.0-dev.1"], "a rung may not leave a hole", "jumps to 3")
    refused("v0.1.0-dev.1", ["v0.1.0-dev.1"], "a tag is not cut twice", "already exists")
    refused("v0.1.0-dev.0", [], "a prerelease starts at 1", "numbers its rung 0")
    refused("0.1.0-dev.1", [], "a tag without the v is not a ladder tag", "not a ladder tag")
    refused("v0.1.0-alpha.1", [], "there is no alpha rung", "not a ladder tag")
    refused("v0.1.0-rc.1", ["v0.2.0-beta.1"], "another version's rungs do not count", "skips")

    print("ladder: FAILED" if FAILURES else f"ladder: all {15 - len(FAILURES)} checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
