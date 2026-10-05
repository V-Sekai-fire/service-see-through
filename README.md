# service-see-through

A release package for a single-image layer decomposer, holding the gate that decides which release rung a tag may take.

## What it is for

A service packs repositories from different sides into one deployable release and holds no engine code of its own: here, a job transport, the decomposer implementations, and the shared bus between them. This repository keeps the release ladder (dev, beta, rc, release, with no rung skipped), which CI checks on every tag but never advances, and a ratchet that lets the cost and latency budgets only go down. `endpoint.json` records the hosted endpoint's shape so it can be stood up again.

## Building and running

```sh
python3 proof/test_ladder.py
python3 proof/test_ratchet.py
```

## Licence

MIT, per [LICENSE](LICENSE). The Python sources declare Apache-2.0 in their SPDX headers.
