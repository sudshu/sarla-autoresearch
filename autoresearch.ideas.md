# Idea bank

Status: open | running | kept | discarded | dev-only | blocked. Source: claude | codex | user.
Priority 1 = try first. Variant configs live in `variants/`.

| id | pri | status | source | category | hypothesis | variant |
|---|---|---|---|---|---|---|
| H1 | 1 | running | claude | walkers | Many more walkers at the same evaluation budget (512 x 4k, 256 x 8k): start diversity decided the v2/v3 posterior, and the GPU is launch-latency bound so this is nearly free | n_chains=512 n_steps=4000; n_chains=256 n_steps=8000 |
| H2 | 1 | running | claude | moves | Chart move mixed 50/50 with differential-evolution moves (CARDAMOM's STEP_DEMCMC), 512 walkers: affine-invariant steps learn valley lengths the Laplace charts cannot see | kernel=chart_de mix=0.5 n_chains=512 n_steps=4000 |
| H3 | 1 | running | claude | moves | Chart move mixed with Goodman-Weare stretch moves (CARDAMOM mode 4 on the GPU), 512 walkers | kernel=chart_stretch mix=0.5 n_chains=512 n_steps=4000 |
| H4 | 2 | open | claude | moves | Adaptive pooled covariance (Haario) learned from the ensemble during burn-in, mixed 50/50 with chart moves | kernel=chart_adaptcov mix=0.5 |
| H5 | 2 | running | claude | charts | Inflate chart variance in flat (prior-capped) eigendirections x3 | flat_mult=3 |
| H6 | 3 | open | claude | restarts | Restarts through the whole burn-in, tighter gap | restart_until=0.5 restart_gap=50 restart_every=250 |
| H7 | 3 | open | claude | budget | 64 L-BFGS seeds instead of 128, evaluations moved to sampling | n_seeds=64 n_steps=... |
| H8 | 3 | open | claude | speed | Cheaper atlas: 3 rounds, 2048 audit draws (speed path) | atlas_rounds=3 n_audit=2048 |
| H9 | 2 | open | claude | starts | Chains start from all feasible seeds of the main region, not chart centres; motivated by the 82/18 mode inversion at NL-Loo (fast path never finds the dominant high-allocation mode) | start_policy=seeds |
| H10 | 3 | open | claude | burn-in | Burn-in 25% instead of 50% at fixed steps | burn_frac=0.25 |
