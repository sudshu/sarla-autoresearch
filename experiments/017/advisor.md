# Codex advisor, iteration 017

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

Four-rung tempering reduced development G from 1.717 to 0.978 (−0.739, 43%); surgery+tempering reached 0.993, so surgery added no aggregate benefit. Both are effectively tied with recent DE/stretch results (0.96–1.05), not a new breakthrough.

Relative to baseline, plain tempering improved NL-Loo 1.416→1.076, BE-Vie 1.113→0.661, and especially DK-Sor 3.523→1.304, while DE-Gri worsened slightly, 0.817→0.872. Surgery made sites more consistent (range 0.924–1.107 versus 0.661–1.304), primarily by improving DK-Sor and NL-Loo, but degraded BE-Vie by 0.343.

The calibration gap remains dominated by joint-rank failure: mean rank penalties were 2.72 without surgery and 3.14 with it; ranks were 0.77–1.00, with every surgery fit ≥0.91. Surgery reduced the mean stuck penalty from 0.55 to 0.23, but worsened cover90 0.77→0.69, rank by 0.42, and rms-z by 0.06, leaving G unchanged. NL-Loo high-mode mass of 0.22 despite the truth occupying that mode confirms incorrect mode weighting.

There is no evidence yet of cross-truth or holdout generalization: both variants have one kernel seed, one development truth, and no mode-weight stability measurement. Wall times are acceptable: 1.09× and 0.91× baseline.

## 2. RISKS

The 0–2% adjacent-swap rate means this was not an effective tempering experiment; its cold rung behaved largely like a smaller DE ensemble, so the apparent improvement cannot be attributed to replica exchange. Moreover, likelihood-only tempering leaves the full EDC barrier intact, which may be the barrier separating modes.

G can look respectable because marginal coverage and projections compensate for nearly saturated joint-rank penalties; these fits still miss the correct joint typical set. Increasing to 16 rungs also leaves only 16 walkers per rung and 8,000 steps, potentially exchanging ladder resolution for poor within-rung mixing. Selecting designs repeatedly on the same truth risks development-truth specialization even without an obvious single-site improvement.

## 3. NEXT STEPS

1. Run the dense ladder once, requiring meaningful swaps and observed hot-to-cold round trips before confirmation; knobs: `kernel="pt_de"`, `pt_rungs=16`, `pt_beta_min=0.03`, `pt_swap_every=5`, `n_chains=256`, `n_steps=8000`.

2. Test whether ensemble diversity alone stabilizes mode weights using three seeds, since it preserves more walkers per target distribution than tempering; knobs: `kernel="chart_de"`, `mix=0.5`, `n_chains=256`, `n_steps=8000`.

3. Test surgery with within-mode adaptive covariance, separating atlas coverage from unstable cross-mode DE jumps; knobs: `atlas_engine="surgery"`, `kernel="chart_adaptcov"`, `sg_branch_on_infeasible=false`, `sg_weight_rule="volume"`, `n_chains=128`, `n_steps=16000`.

4. **[NEW CODE]** Replace invalid straight-segment topology tests with feasible paths before further surgery tuning; knobs: `sg_connectivity_rule="feasible_path"`, `atlas_engine="surgery"`, `sg_branch_on_infeasible=false`.

## 4. STOP/CONTINUE

Abandon four-rung T1 and the surgery+four-rung combination. Continue likelihood-only tempering only through the pre-planned 16-rung diagnostic; abandon the family if swaps remain below roughly 10% or no complete round trips occur.
