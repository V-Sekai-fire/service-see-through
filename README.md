# service-see-through

One see-through decomposer, as one deployable thing. A **service** packs sides into a release
and holds no code, only what runs together and why.

| member | side | why it is here |
| --- | --- | --- |
| `transport-runpod` | 1 | takes the job off the endpoint queue and puts it on the bus |
| `interactor-see-through-cpp` | 3 | one implementation, ggml, answering on that bus |
| `interactor-see-through-python` | 3 | the other, PyTorch, answering the same commands |
| `contract-bus` | 2 | the shared memory between them, and the envelope |

Two interactors make two images: iceoryx2 names one command service per machine, so two in one
container would race. The A/B is two endpoints on the same input, holding the transport constant.

## The release ladder

**`dev` → `beta` → `rc` → `release`, and no rung is skipped.** `ladder/ladder.py` decides
whether a tag is a legal step, and `proof/test_ladder.py` holds fifteen cases.

**It is not automated, and that is the design.** Nothing here cuts a tag. Each rung claims
evidence a machine cannot supply: `beta` says somebody installed it, `rc` says somebody ran the
production settings and looked at the layers, `release` says somebody decided. CI refuses an
illegal tag, never creates a legal one.

## Two budgets in seconds, and both only go down

Cost and latency are opposed — batching buys one with the other — so `seconds/seconds.json`
keeps two floors and `seconds/ratchet.py` never nets them: halving cost does not license a
slower job, which is the trade two budgets exist to refuse.

Each floor keeps a sample, not a number, because the gate judges against the spread: a
min-of-one ratchet fails on noise and gets switched off. Today's floors measure the path, not a
decomposition, since no engine has landed.

## What runs it today

Nothing. The endpoint, its template, the registry credential and the 100 GB weight volume were
deleted on 2026-08-17, and the deletion was verified rather than assumed. `endpoint.json` is the
recipe for standing it up again, not an inventory of what is there — the expensive thing about a
torn-down service is remembering its shape, not the machines.
