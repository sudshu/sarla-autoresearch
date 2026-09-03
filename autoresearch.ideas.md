# Idea bank

**Primary research direction (from 2026-09-02): the self-correcting atlas.**
The S-family below (atlas geometry and surgery, engine `sarla2.py`, see
ATLAS_SURGERY.md) has priority over kernel tuning. The v2 baseline fails by
never finding the posterior's basin (NL-Loo, DK-Sor, CZ-wet), which is an
atlas-coverage problem, not a kernel problem.

Status: open | running | kept | discarded | dev-only | blocked. Source: claude | codex | user.
Priority 1 = try first. Variant configs live in `variants/`.

| id | pri | status | source | category | hypothesis | variant |
|---|---|---|---|---|---|---|
| H1 | 1 | discarded | claude | walkers | Many more walkers at the same evaluation budget (512 x 4k, 256 x 8k): start diversity decided the v2/v3 posterior, and the GPU is launch-latency bound so this is nearly free | n_chains=512 n_steps=4000; n_chains=256 n_steps=8000 |
| H2 | 1 | running (512: discarded; 128 running) | claude | moves | Chart move mixed 50/50 with differential-evolution moves (CARDAMOM's STEP_DEMCMC), 512 walkers: affine-invariant steps learn valley lengths the Laplace charts cannot see | kernel=chart_de mix=0.5 n_chains=512 n_steps=4000 |
| H3 | 1 | running (512: discarded = baseline, faster; 128/256 running) | claude | moves | Chart move mixed with Goodman-Weare stretch moves (CARDAMOM mode 4 on the GPU), 512 walkers | kernel=chart_stretch mix=0.5 n_chains=512 n_steps=4000 |
| H4 | 2 | running | claude | moves | Adaptive pooled covariance (Haario) learned from the ensemble during burn-in, mixed 50/50 with chart moves | kernel=chart_adaptcov mix=0.5 |
| H5 | 1 | running | claude | charts | Inflate chart variance in flat (prior-capped) eigendirections x3 | flat_mult=3 |
| H6 | 3 | open | claude+codex | restarts | Restarts through the whole burn-in, tighter gap | restart_until=0.5 restart_gap=50 restart_every=250 |
| H7 | 3 | open | claude | budget | 64 L-BFGS seeds instead of 128, evaluations moved to sampling | n_seeds=64 n_steps=... |
| H8 | 3 | open | claude | speed | Cheaper atlas: 3 rounds, 2048 audit draws (speed path) | atlas_rounds=3 n_audit=2048 |
| H9 | 1 | discarded | claude+codex | starts | Chains start from all feasible seeds of the main region, not chart centres; motivated by the 82/18 mode inversion at NL-Loo (fast path never finds the dominant high-allocation mode) | start_policy=seeds |
| H10 | 3 | open | claude | burn-in | Burn-in 25% instead of 50% at fixed steps | burn_frac=0.25 |
| H11 | 2 | open | codex | moves | Tune the DE step (de_gamma around 2.38/sqrt(2D)) if H2 shows promise | de_gamma=0.12 / 0.25 |
| R1 | - | rule | codex | protocol | Confirm any apparent winner with three kernel seeds and on the dev-B truths before promotion; require improvement outside BE-Vie, which holds 54% of the baseline gap | - |
| S1 | 1 | running | external+claude | atlas_geometry | Does topology-aware surgery (extend/refine/split/branch/rank-change/merge) reduce importance discrepancies faster per evaluation than v1's add-a-chart, and does the final posterior improve? | atlas_engine=surgery |
| S2 | 1 | running | claude | atlas_geometry | Does normal projection place repair points better than repairing at the raw flagged draw? | atlas_engine=surgery sg_normal_projection=false (ablation) |
| S3 | 1 | running | claude | atlas_geometry | Do tangent-volume mixture weights (long ridges get more proposal mass) beat uniform weights? | sg_weight_rule=volume |
| S4 | 1 | confirming (0.92 one seed) | claude+codex | atlas_geometry | Surgery + DE kernel (do the gains combine?); more repair per round: 16 flags, 10 audit rounds | sg_flag_topk=16 atlas_rounds=10 |
| S5 | 2 | open | claude | atlas_geometry | Does true splitting help or hurt? (C2 box problem: repeated splits cost coverage) | sg_do_split=false |
| S6 | 2 | open | claude | atlas_geometry | Rank-detection criterion: gap_min 3 vs 10 vs 30; rank_tau 0.5 / 2 | sg_gap_min=3; sg_rank_tau=0.5 |
| S7 | 1 | running (btau 100) | claude | atlas_geometry | Branch criterion: branch_tau 5 vs 10 vs 20 (how easily a discrepancy becomes a new stratum) | sg_branch_tau=5 / 20 |
| S8 | 2 | open | claude | atlas_geometry | Audit sample size 16384 with ESS-based stop: can fewer downstream MCMC evaluations achieve the same G after a better atlas? | n_audit=16384 sg_stop_ess=0.3 n_steps=16000 |
| S9 | 3 | open | claude | atlas_geometry | Warm-up (H12) + surgery: does a better seed population change which operations fire? | warmup_steps=1000 atlas_engine=surgery |
| S10 | 3 | open | claude | atlas_geometry | Merge criterion: merge_tol 0.5 vs 2 (cost vs coverage) | sg_merge_tol=2.0 |
| P1 | - | rule | codex (iter 4) | strategy | Kernel-tuning family (H1-H4, H11) paused until a valid experiment shows the posterior basin is represented in the atlas; local mixing cannot repair a missing basin | - |
| T1 | 1 | open | osse-session/user | tempering | Likelihood-only tempering, EDC hard gate kept at every rung, 4-6 geometric temperatures, DE moves within rungs, adjacent swaps; walkers initialised stratified by mode (share on the high-allocation charts) so gamma=1 DE jumps span both modes | new code |
| B1 | 1 | open | osse-session/user | mode-weights | Two-cell bridge estimate of log Z_high - log Z_low (cells f_wood > / <= 0.5, moment-matched Gaussian per cell, sarla_evidence._bridge_logr) to reweight pooled DE draws; test on the iteration-13 DE fits and on real NL-Loo vs 0.815 | new code |
| M1 | - | rule | osse-session/user | protocol | Promotion requires across-seed sd of the high-mode fraction <= 0.10 at NL-Loo and DK-Sor; real-data NL-Loo mode fraction reported at every milestone | - |
