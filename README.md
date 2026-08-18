# service-see-through

One see-through decomposer, as one deployable thing. A **service** is a packing of sides into a
release; it holds no code of its own, only what runs together and why.

## The membership

| member | side | why it is here |
| --- | --- | --- |
| `transport-runpod` | 1 | takes the job off the endpoint queue and puts it on the bus |
| `interactor-see-through-cpp` | 3 | one implementation, ggml, answering on that bus |
| `interactor-see-through-python` | 3 | the other, PyTorch, answering the same commands |
| `contract-bus` | 2 | the shared memory between them, and the envelope |

Two interactors and one transport layer make two images, not one. iceoryx2 names one command
service per machine, so two interactors in a container would both answer and race; the A/B is
two endpoints given the same input, which also holds the transport layer constant across it.

`transport-bus-cli` is not a member. It reaches the same interactors from a terminal, which is
how they are driven when no endpoint is running, and nothing ships it.

## The release ladder

**`dev` → `beta` → `rc` → `release`, and no rung is skipped.** `ladder/ladder.py` decides
whether a proposed tag is a legal step and `proof/test_ladder.py` holds the fifteen cases,
including every skip somebody would want to take in a hurry.

**It is not automated, and that is the design.** Nothing here cuts a tag. Each rung is a claim
about evidence a machine cannot supply: `beta` says somebody installed it somewhere real, `rc`
says somebody ran the production settings and looked at the layers, and `release` says somebody
decided. A workflow promoting on a green build would assert all three on nobody's authority, so
CI refuses an illegal tag and never creates a legal one.

## What runs it today

A RunPod Serverless queue endpoint, `workersMin` 0, in `EU-RO-1` because that is where the
weight cache is. Weights are never in an image: they live on the network volume RunPod mounts
at `/runpod-volume`, written once and read by every worker in the data center. `endpoint.json`
records the shape, and the ids it names are this account's rather than anything portable.
