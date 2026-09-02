# Topology-aware atlas surgery (SARLA v2 engine)

Written 2026-09-02 after an external review redirected the loop's primary
target from tuning the downstream MCMC kernel to the self-correcting,
rank-adaptive Laplace atlas itself. Code: `scripts/sarla2.py` (research repo,
snapshot in `code/`), selected by `atlas_engine: "surgery"` in a variant.
The v1 engine (`scripts/sarla.py`) is untouched and remains the baseline.

## What the v1 engine already did

- Whitened-Hessian rank detection with a spectral-gap rule (`rank_split`).
- Importance audit from a frozen defensive mixture (charts + Student-t).
- Normal-space re-optimisation of each flagged draw (tangent frozen).
- Diagnostic labels extend / split / rank-change / refine.
- A duplicate filter ("merge") and a final exact independence-MH stage.

## What was only a label

Every diagnosis in v1 ended in `atlas.charts.append(make_chart(w_star))`.
The atlas was an unordered uniform mixture with no rank transitions,
neighbours, extents or strata. Merge was a duplicate filter by proximity.

## What v2 implements (2026-09-02)

Chart state: id, rank, tangent/normal bases, per-tangent extent (through the
proposal variance: extent = extend_sigma * sqrt(var_t)), neighbour set (metric
overlap under either chart's Mahalanobis metric, `overlap_tol`), branch id
(connected component of neighbour graph plus rank/split/refine links), typed
links, origin operation and round.

Operations, chosen per flagged draw after normal projection to x*:

| op | trigger | what changes |
|---|---|---|
| branch | x* not density-connected to the nearest chart k (segment dips > `branch_tau` below its endpoints) | new chart, new stratum, no link |
| rank-change | rank(x*) != rank(k), robust to `rank_tau` x/÷ `rank_hysteresis` | new chart of the new rank, `rank` edge to k, k's extent capped at the boundary |
| extend | x* outside k's tangent extent, k's quadratic model accurate at x* (< `model_tol`), ridge straight (normal displacement < `bend_tol` sigmas) | k's variance along that tangent direction grows to cover x*; **no new chart** |
| refine | x* outside the extent and the ridge bends or the model fails | k's extent capped at the bend, new chart tiled at x*, `refine` link |
| split | x* inside k's extent yet k's model is wrong there | k **replaced** by two charts at k +/- `split_offset` s_z along the offending tangent direction (fresh Hessians, quartered tangent variance), `split` link |
| merge | neighbours of equal rank and branch that explain each other's centres (mutual Mahalanobis < `merge_tol`, mutual model error < `model_tol`) | fused into the higher-density chart with extents unioned |
| patch | a round with flags but no structural op (all flags "duplicate": q too low despite a nearby accurate chart) | v1 behaviour, one chart at the worst flag; counted separately |

Mixture weights are exact and known (uniform or tangent-volume), so the
independence-MH and the fast path's chart-shaped random walk remain exact
MH against the true target. The atlas is frozen before sampling.

Per audit round the engine logs: K, rank histogram, number of branches,
IS-ESS, number of uncovered draws (importance log-weight > median +
`flag_thresh`), the max / 95th / 99th percentile log-weight excess, model
error of the flagged points, counts of every operation, cumulative target
evaluations, wall-clock, and whether the 95th-percentile discrepancy fell.
The fitter prints a trace like

    audit 0: 7 uncovered (q95 1.1), K=1 ranks=[0, 1] ESS=0.016 -> 1 refine, 1 split, 1 rank-change
    audit 1: 0 uncovered (q95 0.0), K=2 ESS=0.954 -> nothing

and stores the full history in the fit file (`atlas_history`); the scorer
carries it into `experiments/NNN/scores/*.json` under `meta.atlas_summary`.

## Box problems (`scripts/sarla2_toys.py`, results in `figures/sarla/sarla2_toys.json`)

| case | v1 | v2 | note |
|---|---|---|---|
| A curved ridge, 1 seed | KL 0.39, 9 charts | KL 0.43, 10 charts | on par after rank hysteresis + bend test |
| B hidden mode, 1 seed | KL 0.03, labelled "split" | KL 0.03, labelled **branch**, 2 strata, mass 0.50 exact | correct classification |
| C ridge -> bump, seed on ridge | KL 0.58, 2 charts, IMH acc 0.43 | KL 0.23, **1 chart**, acc 0.68 | true extend beats adding charts |
| C2 same, seed on bump | KL 0.31 | KL 0.61 | rank-change fires; repeated splits cost coverage: a knob for the loop |
| D 8-D Gaussian, 20 seeds | 6 charts | 6 charts (dedup at build) | merge not exercised yet |

Exactness: posterior means within 0.2 sd and sds within 4-45% of grid
truth for both engines at 3,000 x 32 IMH steps (the banana's 45% is the
independence sampler's low acceptance, identical for both engines).

## Knobs exposed in `Variant` (prefix `sg_`)

rank_tau, gap_min, gap_cap, var_cap, flag_topk, flag_thresh, eta,
weight_rule, normal_projection, extend_sigma, model_tol, merge_tol,
overlap_tol, branch_tau, split_offset, refine_shrink, rank_hysteresis,
bend_tol, fallback_patch, do_{extend,refine,split,rank,branch,merge},
clean_stop, stop_ess; plus the shared atlas_rounds and n_audit.

## Not implemented yet (ideas, not claims)

- Tangent-domain proposals (uniform over the extent box with a normal
  Gaussian) instead of Gaussian charts; would make extent a true domain.
- Curvature-aware refine that retiles along the principal curvature
  direction rather than at the single corrected point.
- Merge across rank transitions; explicit chart overlap weights; a stopping
  rule on discrepancy trajectory rather than clean audits.
- An atlas-only evaluation budget in the protocol (today the atlas shares
  the fixed 2.4M-evaluation budget with the sampling stage).

## Note on the calibration metric (flagged, not changed)

The density-rank term |r - 0.5| treats one simulation's rank as if it had to
be 0.5. Rigorous simulation-based calibration needs the rank distribution
over repeated truth and noise realisations; a single rank far from 0.5 is
evidence but not proof. The metric is unchanged so protocol-v2 results stay
comparable; the B truths and repeated seeds are the beginning of the
repeated-realisation view.
