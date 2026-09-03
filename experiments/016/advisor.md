# Codex advisor, iteration 016

model default (config.toml), reasoning effort high, rc 0

## 1. ASSESSMENT

S8 scores 1.197, improving 0.520 (30%) over the 1.717 baseline, but it is 0.234 worse than the three-seed S4 surgery+DE result and 34% slower than S4 (3,870 versus 2,880 seconds). The apparent baseline gain is concentrated almost entirely at DK-Sor (3.523→1.789; 83% of the total improvement) and BE-Vie (1.113→0.753); NL-Loo is essentially unchanged (1.416→1.392), while DE-Gri slightly worsens (0.817→0.854).

The mean term contributions are rank 2.78, cover90 1.39, projection 1.11, cover50 1.07, rms-z 0.84, and stuck 0. Rank remains near its worst value at NL-Loo and DK-Sor (r≈1; term 3.33) and is also poor at DE-Gri (r=0.917; term 2.78), so disabling the spectral-gap rule and increasing hysteresis did not restore typical-set calibration. DK-Sor remains broadly under-dispersed—67%/34% coverage versus 90%/50% targets—and its projection term is 1.76, including only 51% coverage for one stream.

All four sites completed and none violates the +0.25 site guard, but this is only one kernel seed, with no mode-weight, dev-B, or holdout result. Consequently there is no evidence that the improvement generalizes across seeds or truths; its concentration at DK-Sor is specifically a single-site/single-truth warning.

## 2. RISKS

The comparison mixes one S8 seed with a three-seed baseline whose DK-Sor variability was extreme, so the 0.520 gain is not an acceptance-quality estimate. The capped aggregate is not distorting S8 itself because all raw scores are below 5, but it hides how unstable the baseline comparator was. More fundamentally, 39 branch and 45 rank-change operations still fired: the intervention changed rank thresholds without fixing the hard-gate-crossing straight-line test, so operation counts can masquerade as topology discovery. Equal weighting of six terms also lets good stuck-chain behavior obscure near-saturated density-rank failure.

## 3. NEXT STEPS

1. **[NEW CODE]** Test likelihood-only parallel tempering because the repeated cross-seed mode-weight inversions are now stronger evidence for an inter-mode transport failure than a local proposal-scale failure: `kernel=tempered_de`, `start_policy=balanced`, `n_chains=256`, `n_steps=8000`, `de_gamma=0.12/0.25`.

2. Complete H13 with at least three `kernel_seed` values and judge NL-Loo/DK-Sor mode-fraction SD before G, testing `kernel=chart_de`, `mix=0.5`, `n_chains=256`, `n_steps=8000`, and `de_gamma=0.12/0.25`.

3. Test whether surgery benefits from globally learned within-mode geometry without DE’s unstable cross-mode weighting: `atlas_engine=surgery`, `sg_flag_topk=16`, `atlas_rounds=10`, `kernel=chart_adaptcov`, `mix=0.5`, `adapt_start=0.25`, `adapt_every=200`.

4. **[NEW CODE]** Replace straight-segment hard-gate connectivity with a feasible-path test and expose it as `sg_connectivity_rule=feasible_path`, holding `sg_branch_tau=100`, `sg_gap_min=10`, and `sg_rank_tau=2` fixed for a clean ablation.

## 4. STOP/CONTINUE

Abandon further tuning of the S8 absolute-rank/hysteresis/branch-threshold family: it left pathological operation counts and rank calibration intact. Continue surgery only in combinations addressing transport or connectivity, and pause additional single-seed screens of purely local kernels.
