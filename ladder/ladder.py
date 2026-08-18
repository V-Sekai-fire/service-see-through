"""The release ladder: dev, beta, rc, release, and no rung skipped.

A service is where the parts are packaged together into a release, so this is the rule that
decides whether a tag may be cut. It is a program rather than a paragraph because a convention
about version numbers that nothing enforces is one that holds until the first hurry.

    python3 ladder/ladder.py v0.1.0-rc.1 --tags v0.1.0-dev.3 v0.1.0-beta.2

Exits 0 if the tag is a legal next step and non-zero with the reason if it is not.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import re
import sys

RUNGS = ("dev", "beta", "rc", "release")

# v1.2.3, or v1.2.3-<rung>.<n>. The rung is named rather than numbered so a tag says which
# rung it is on without anybody having to remember an order.
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-(dev|beta|rc)\.(\d+))?$")


class NotOnTheLadder(Exception):
    """The tag is malformed, or the step it takes is not one the ladder allows."""


def parse(tag: str):
    m = TAG.match(tag)
    if not m:
        raise NotOnTheLadder(
            f"{tag} is not a ladder tag: expected vX.Y.Z or vX.Y.Z-<dev|beta|rc>.N"
        )
    major, minor, patch, rung, n = m.groups()
    version = (int(major), int(minor), int(patch))
    return version, (rung or "release"), (int(n) if n else 0)


def check(proposed: str, existing: list[str]) -> None:
    """Raises `NotOnTheLadder` with the reason, or returns having found none."""
    version, rung, n = parse(proposed)

    if rung != "release" and n < 1:
        raise NotOnTheLadder(f"{proposed} numbers its rung 0; a prerelease starts at 1")

    same_version = []
    for tag in existing:
        try:
            v, r, k = parse(tag)
        except NotOnTheLadder:
            continue  # a tag that is not on the ladder says nothing about one that is
        if v == version:
            same_version.append((r, k))

    if (rung, n) in same_version:
        raise NotOnTheLadder(f"{proposed} already exists")

    reached = {r for r, _ in same_version}
    step = RUNGS.index(rung)

    # Every rung below this one must have been stood on for this version. Skipping is the
    # failure this exists to stop: an rc that no beta preceded has never been installed by
    # anybody, and calling it a release candidate is a claim nothing backs.
    missing = [r for r in RUNGS[:step] if r not in reached]
    if missing:
        raise NotOnTheLadder(
            f"{proposed} skips {', '.join(missing)}: {version[0]}.{version[1]}.{version[2]} "
            f"has only reached {', '.join(sorted(reached)) or 'nothing'}"
        )

    # Within a rung, the number goes up by one. A gap means a tag was cut and deleted, and a
    # ladder with a hole in it is one nobody can read backwards.
    same_rung = sorted(k for r, k in same_version if r == rung)
    if rung != "release" and same_rung and n != same_rung[-1] + 1:
        raise NotOnTheLadder(
            f"{proposed} jumps to {n} where {rung} is at {same_rung[-1]}; the next is "
            f"{same_rung[-1] + 1}"
        )


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    proposed, existing = argv[0], []
    if "--tags" in argv:
        existing = argv[argv.index("--tags") + 1 :]
    try:
        check(proposed, existing)
    except NotOnTheLadder as why:
        print(f"ladder: {why}", file=sys.stderr)
        return 1
    print(f"ladder: {proposed} is a legal step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
